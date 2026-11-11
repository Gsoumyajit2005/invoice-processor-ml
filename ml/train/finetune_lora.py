"""BF16 PEFT LoRA fine-tuning script for Qwen3.5-0.8B on RTX 3050 6GB."""

from __future__ import annotations

import argparse
import json
import math
import random
import time
from pathlib import Path
from typing import Any

from app.core.paths import QWEN35_08B_DIR, QWEN35_LORA_DIR, REPO_ROOT, configure_local_caches

configure_local_caches(offline=True)

import torch  # noqa: E402
import torch.nn.functional as F  # noqa: E402
from app.extractors.base import build_v2_extraction_prompt  # noqa: E402
from peft import LoraConfig, get_peft_model  # noqa: E402
from PIL import Image  # noqa: E402
from transformers import AutoModelForImageTextToText, AutoProcessor  # noqa: E402

TRAIN_CACHE_DIR = REPO_ROOT / "ml" / "train" / "cache"
DEFAULT_LORA_TARGET_REGEX = (
    r".*language_model\.layers\.\d+\..*"
    r"(q_proj|k_proj|v_proj|o_proj|gate_proj|up_proj|down_proj|in_proj_qkv|out_proj)$"
)


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def _encode_sample(
    row: dict[str, Any],
    processor: Any,
    *,
    max_ocr_chars: int,
    max_seq_tokens: int,
) -> dict[str, Any] | None:
    """Encode prompt + pretty JSON target and locate exact assistant token boundary."""
    img_path = REPO_ROOT / row["image_path"]
    prompt = build_v2_extraction_prompt(row["ocr_text"], max_ocr_chars=max_ocr_chars)
    # Use pretty indent=2 JSON matching SCHEMA_TEMPLATE_V2 and base Qwen3.5 generation format.
    ans_text = json.dumps(json.loads(row["target_json"]), indent=2, ensure_ascii=False)

    with Image.open(img_path) as im:
        rgb_img = im.convert("RGB")
        user_msgs = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": rgb_img},
                    {"type": "text", "text": prompt},
                ],
            }
        ]
        full_msgs = user_msgs + [
            {
                "role": "assistant",
                "content": [{"type": "text", "text": ans_text}],
            }
        ]
        prompt_text = processor.apply_chat_template(
            user_msgs,
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=False,
        )
        full_text = processor.apply_chat_template(
            full_msgs,
            tokenize=False,
            add_generation_prompt=False,
            enable_thinking=False,
        )
        prompt_inputs = processor(
            text=[prompt_text],
            images=[rgb_img],
            padding=False,
            return_tensors="pt",
        )
        full_inputs = processor(
            text=[full_text],
            images=[rgb_img],
            padding=False,
            return_tensors="pt",
        )

    full_ids = full_inputs["input_ids"][0]
    if int(full_ids.shape[0]) > max_seq_tokens:
        return None

    prompt_ids = prompt_inputs["input_ids"][0]
    prompt_len = int(prompt_ids.shape[0])
    if prompt_len >= int(full_ids.shape[0]) or not full_ids[:prompt_len].equal(prompt_ids):
        # Fallback to longest common token prefix if BPE merged near boundary
        limit = min(prompt_len, int(full_ids.shape[0]) - 1)
        matched = 0
        while matched < limit and int(full_ids[matched]) == int(prompt_ids[matched]):
            matched += 1
        prompt_len = matched

    ans_len = int(full_ids.shape[0]) - prompt_len
    if ans_len < 4:
        return None

    return {
        "sample_id": row["sample_id"],
        "source": row["source"],
        "inputs": full_inputs,
        "prompt_len": prompt_len,
        "ans_len": ans_len,
        "total_tokens": int(full_ids.shape[0]),
    }


def _forward_loss(
    model: Any,
    encoded: dict[str, Any],
    *,
    device: torch.device,
) -> torch.Tensor:
    """Compute assistant-only cross-entropy using logits_to_keep to prevent full-vocab OOM."""
    inputs = {
        k: v.to(device) if isinstance(v, torch.Tensor) else v
        for k, v in encoded["inputs"].items()
    }
    ans_len: int = encoded["ans_len"]
    prompt_len: int = encoded["prompt_len"]

    out = model(**inputs, use_cache=False, logits_to_keep=ans_len + 1)
    shift_logits = out.logits[:, :-1, :].contiguous()
    target_ids = inputs["input_ids"][:, prompt_len:].contiguous()
    return F.cross_entropy(
        shift_logits.view(-1, shift_logits.size(-1)).float(),
        target_ids.view(-1),
    )


@torch.no_grad()
def _evaluate_val_loss(
    model: Any,
    val_encoded: list[dict[str, Any]],
    *,
    device: torch.device,
) -> float:
    was_training = model.training
    model.eval()
    total_loss = 0.0
    total_tokens = 0
    try:
        for item in val_encoded:
            loss = _forward_loss(model, item, device=device)
            ans_len = item["ans_len"]
            total_loss += float(loss.item()) * ans_len
            total_tokens += ans_len
    finally:
        if was_training:
            model.train()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    return total_loss / max(total_tokens, 1)


def _lr_for_step(step: int, total_steps: int, base_lr: float, warmup_ratio: float = 0.10) -> float:
    warmup_steps = max(1, int(total_steps * warmup_ratio))
    if step < warmup_steps:
        return base_lr * float(step + 1) / float(warmup_steps)
    progress = min(1.0, float(step - warmup_steps) / max(1, total_steps - warmup_steps))
    cosine = 0.5 * (1.0 + math.cos(math.pi * progress))
    return base_lr * (0.1 + 0.9 * cosine)


def train_lora(args: argparse.Namespace) -> dict[str, Any]:
    """Run LoRA SFT on pre-built JSONL splits and save best validation adapter."""
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA GPU required for Qwen3.5 LoRA training.")

    random.seed(args.seed)
    torch.manual_seed(args.seed)
    device = torch.device("cuda:0")

    train_rows = _load_jsonl(Path(args.train_jsonl))
    val_rows = _load_jsonl(Path(args.val_jsonl))

    processor = AutoProcessor.from_pretrained(str(args.base_model), trust_remote_code=True)
    processor.image_processor.size = {
        "shortest_edge": 65536,
        "longest_edge": 512 * 768,
    }

    print("[train] Encoding dataset splits...")
    train_encoded: list[dict[str, Any]] = []
    skipped_train = 0
    for row in train_rows:
        enc = _encode_sample(
            row,
            processor,
            max_ocr_chars=args.max_ocr_chars,
            max_seq_tokens=args.max_seq_tokens,
        )
        if enc is None:
            skipped_train += 1
        else:
            train_encoded.append(enc)

    val_encoded: list[dict[str, Any]] = []
    skipped_val = 0
    for row in val_rows:
        enc = _encode_sample(
            row,
            processor,
            max_ocr_chars=args.max_ocr_chars,
            max_seq_tokens=args.max_seq_tokens,
        )
        if enc is None:
            skipped_val += 1
        else:
            val_encoded.append(enc)

    max_tok = max(x["total_tokens"] for x in train_encoded + val_encoded)
    print(
        f"[train] Encoded train={len(train_encoded)} (skipped={skipped_train}), "
        f"val={len(val_encoded)} (skipped={skipped_val}), max_tokens={max_tok}"
    )

    base_model = AutoModelForImageTextToText.from_pretrained(
        str(args.base_model),
        dtype=torch.bfloat16,
        trust_remote_code=True,
        device_map={"": "cuda:0"},
    )
    base_model.config.use_cache = False
    base_model.enable_input_require_grads()
    base_model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})

    lora_cfg = LoraConfig(
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=args.lora_dropout,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=DEFAULT_LORA_TARGET_REGEX,
    )
    model = get_peft_model(base_model, lora_cfg)
    model.print_trainable_parameters()
    model.train()

    trainable_params = [p for p in model.parameters() if p.requires_grad]
    optimizer = torch.optim.AdamW(trainable_params, lr=args.lr, weight_decay=0.01)

    total_batches_per_epoch = math.ceil(len(train_encoded) / args.grad_accum)
    total_opt_steps = max(1, total_batches_per_epoch * args.epochs)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    torch.cuda.reset_peak_memory_stats(device)
    baseline_val_loss = _evaluate_val_loss(model, val_encoded, device=device)
    best_val_loss = baseline_val_loss
    best_opt_step = 0
    model.save_pretrained(str(output_dir))
    processor.save_pretrained(str(output_dir))
    print(f"[eval] opt_step=0 (baseline) | val_loss={baseline_val_loss:.4f}")

    opt_step = 0
    history: list[dict[str, Any]] = [{"opt_step": 0, "val_loss": round(baseline_val_loss, 5)}]
    train_start = time.perf_counter()
    step_times: list[float] = []

    optimizer.zero_grad(set_to_none=True)
    rng = random.Random(args.seed)

    for epoch in range(1, args.epochs + 1):
        epoch_items = list(train_encoded)
        rng.shuffle(epoch_items)
        batches = [
            epoch_items[i : i + args.grad_accum]
            for i in range(0, len(epoch_items), args.grad_accum)
        ]
        for batch in batches:
            batch_loss = 0.0
            batch_len = len(batch)
            for item in batch:
                t0 = time.perf_counter()
                raw_loss = _forward_loss(model, item, device=device)
                (raw_loss / float(batch_len)).backward()
                batch_loss += float(raw_loss.item())
                step_times.append(time.perf_counter() - t0)

            lr_now = _lr_for_step(opt_step, total_opt_steps, args.lr)
            for pg in optimizer.param_groups:
                pg["lr"] = lr_now
            torch.nn.utils.clip_grad_norm_(trainable_params, max_norm=1.0)
            optimizer.step()
            optimizer.zero_grad(set_to_none=True)
            opt_step += 1

            avg_train_loss = batch_loss / float(batch_len)
            if opt_step % args.log_every == 0 or opt_step == 1 or opt_step == total_opt_steps:
                peak_mb = torch.cuda.max_memory_allocated(device) / (1024 * 1024)
                avg_s = sum(step_times[-batch_len:]) / float(batch_len)
                print(
                    f"[train] epoch={epoch}/{args.epochs} opt_step={opt_step}/{total_opt_steps} "
                    f"loss={avg_train_loss:.4f} lr={lr_now:.2e} "
                    f"step_s={avg_s:.2f} peak_vram_mb={peak_mb:.1f}"
                )

            is_eval_step = (opt_step % args.eval_every == 0) or (opt_step == total_opt_steps)
            if is_eval_step:
                val_loss = _evaluate_val_loss(model, val_encoded, device=device)
                improved = val_loss < best_val_loss
                if improved:
                    best_val_loss = val_loss
                    best_opt_step = opt_step
                    model.save_pretrained(str(output_dir))
                    processor.save_pretrained(str(output_dir))
                history.append(
                    {
                        "opt_step": opt_step,
                        "epoch": epoch,
                        "train_loss": round(avg_train_loss, 5),
                        "val_loss": round(val_loss, 5),
                        "saved_best": improved,
                    }
                )
                print(
                    f"[eval] opt_step={opt_step} | val_loss={val_loss:.4f} "
                    f"({'BEST' if improved else f'best={best_val_loss:.4f}'})"
                )

    total_time = time.perf_counter() - train_start
    peak_vram_mb = torch.cuda.max_memory_allocated(device) / (1024 * 1024)
    metrics = {
        "base_model": str(args.base_model),
        "output_dir": str(output_dir),
        "epochs": args.epochs,
        "train_samples": len(train_encoded),
        "val_samples": len(val_encoded),
        "total_opt_steps": opt_step,
        "best_opt_step": best_opt_step,
        "baseline_val_loss": round(baseline_val_loss, 5),
        "best_val_loss": round(best_val_loss, 5),
        "peak_vram_mb": round(peak_vram_mb, 1),
        "wall_clock_s": round(total_time, 1),
        "history": history,
    }
    (TRAIN_CACHE_DIR / "train_metrics.json").write_text(
        json.dumps(metrics, indent=2), encoding="utf-8"
    )
    print(f"[done] Training complete in {total_time:.1f}s | best val_loss={best_val_loss:.4f}")
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fine-tune Qwen3.5-0.8B LoRA for invoice extraction"
    )
    parser.add_argument("--base-model", type=Path, default=QWEN35_08B_DIR)
    parser.add_argument("--output-dir", type=Path, default=QWEN35_LORA_DIR)
    parser.add_argument("--train-jsonl", type=Path, default=TRAIN_CACHE_DIR / "train.jsonl")
    parser.add_argument("--val-jsonl", type=Path, default=TRAIN_CACHE_DIR / "val.jsonl")
    parser.add_argument("--epochs", type=int, default=2)
    parser.add_argument("--grad-accum", type=int, default=8)
    parser.add_argument("--lr", type=float, default=1.5e-4)
    parser.add_argument("--lora-r", type=int, default=16)
    parser.add_argument("--lora-alpha", type=int, default=32)
    parser.add_argument("--lora-dropout", type=float, default=0.05)
    parser.add_argument("--max-ocr-chars", type=int, default=2800)
    parser.add_argument("--max-seq-tokens", type=int, default=1750)
    parser.add_argument("--eval-every", type=int, default=12)
    parser.add_argument("--log-every", type=int, default=3)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    train_lora(args)


if __name__ == "__main__":
    main()

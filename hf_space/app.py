"""Hugging Face ZeroGPU microservice for Qwen3.5-0.8B + Phase 3 Invoice LoRA."""

import spaces
import json
import os
import gradio as gr
import torch
from safetensors import safe_open
from PIL import Image
from transformers import AutoModelForImageTextToText, AutoProcessor

MODEL_ID = "Qwen/Qwen3.5-0.8B"
LORA_DIR = os.path.join(os.path.dirname(__file__), "lora_adapter")
ADAPTER_FILE = os.path.join(LORA_DIR, "adapter_model.safetensors")
CONFIG_FILE = os.path.join(LORA_DIR, "adapter_config.json")

print(f"[Startup] Loading processor for {MODEL_ID}...")
processor = AutoProcessor.from_pretrained(MODEL_ID)
if hasattr(processor, "image_processor") and hasattr(processor.image_processor, "size"):
    processor.image_processor.size = {
        "shortest_edge": 65536,
        "longest_edge": 1024 * 1280,
    }

print(f"[Startup] Loading base model {MODEL_ID} in FP16...")
model = AutoModelForImageTextToText.from_pretrained(
    MODEL_ID,
    dtype=torch.float16,
)

if os.path.exists(ADAPTER_FILE) and os.path.exists(CONFIG_FILE):
    print(f"[Startup] Merging LoRA adapter mathematically from {ADAPTER_FILE}...")
    with open(CONFIG_FILE) as f:
        cfg = json.load(f)
    scaling = float(cfg.get("lora_alpha", 32)) / float(cfg.get("r", 16))
    state_dict = dict(model.named_parameters())
    with safe_open(ADAPTER_FILE, framework="pt", device="cpu") as f:
        a_keys = [k for k in f.keys() if "lora_A" in k]
        for a_key in a_keys:
            b_key = a_key.replace("lora_A", "lora_B")
            target = a_key.replace("base_model.model.", "").replace(".lora_A.weight", ".weight")
            if target in state_dict:
                a_t = f.get_tensor(a_key).to(torch.float32)
                b_t = f.get_tensor(b_key).to(torch.float32)
                delta = (b_t @ a_t) * scaling
                state_dict[target].data.add_(delta.to(state_dict[target].dtype))
    print(f"[Startup] Successfully merged {len(a_keys)} LoRA layers into base weights.")
else:
    print(f"[Startup] Warning: {ADAPTER_FILE} not found. Running base model.")

print("[Startup] Transferring merged model to ZeroGPU CUDA device...")
model = model.to("cuda")
model.eval()
print("[Startup] Model initialization complete.")


@spaces.GPU(duration=30)
def extract_invoice(image: Image.Image, prompt: str) -> str:
    """Run multimodal inference on high-performance NVIDIA ZeroGPU."""
    if image is None:
        return json.dumps({"error": "No image provided"})

    image_rgb = image.convert("RGB")
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image", "image": image_rgb},
                {"type": "text", "text": prompt},
            ],
        }
    ]

    inputs = processor.apply_chat_template(
        messages,
        tokenize=True,
        add_generation_prompt=True,
        enable_thinking=False,
        return_dict=True,
        return_tensors="pt",
    ).to("cuda")

    with torch.inference_mode():
        output_ids = model.generate(
            **inputs,
            max_new_tokens=1536,
            do_sample=False,
        )

    gen_tokens = output_ids[:, inputs["input_ids"].shape[1] :]
    raw_text = processor.batch_decode(gen_tokens, skip_special_tokens=True)[0].strip()
    return raw_text


demo = gr.Interface(
    fn=extract_invoice,
    inputs=[
        gr.Image(type="pil", label="Invoice Page Image"),
        gr.Textbox(label="Extraction Prompt", lines=8),
    ],
    outputs=gr.Code(label="Extracted JSON", language="json"),
    title="Invoice Processor VLM (ZeroGPU)",
    description="Multimodal invoice extraction powered by Qwen3.5-0.8B + Phase 3 PEFT LoRA on Hugging Face ZeroGPU.",
)

if __name__ == "__main__":
    demo.launch()

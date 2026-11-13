"use client";

import { MapPin } from "lucide-react";
import type { FieldProvenance } from "@/lib/types";
import { GlassPopover } from "./GlassPopover";
import { GlassButton } from "./GlassButton";

export function OcrInspectorControl({ label, provenance, onLocate }: { label: string; provenance: FieldProvenance; onLocate: () => void }) {
  const box = provenance.bbox;
  return <GlassPopover label={`Inspect ${label} provenance`} trigger={<MapPin aria-hidden="true" size={13} />}>
    <dl className="lg-inspector-data">
      <dt>Source</dt><dd>{provenance.source === "ocr_matched" ? "OCR matched" : provenance.source === "vlm_inferred" ? "VLM inferred" : "User edited"}</dd>
      {box ? <><dt>Document page</dt><dd>{box.page}</dd><dt>Bounding box (0–1000)</dt><dd>[{box.x1}, {box.y1}, {box.x2}, {box.y2}]</dd>
        <dt>Confidence</dt><dd>{box.confidence == null ? "Not supplied" : String(box.confidence)}</dd></> : <><dt>Bounding box</dt><dd>No coordinates supplied</dd></>}
    </dl>
    {box ? <GlassButton onClick={onLocate}>Locate on document</GlassButton> : null}
  </GlassPopover>;
}

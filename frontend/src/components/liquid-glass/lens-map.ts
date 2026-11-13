/** A smooth, size-specific edge lens. Canvas bakes geometry, never document pixels.
 * Technique reference: nordify/css-liquid-glass HOW-IT-WORKS.md (MIT).
 * Grey X + alpha Y avoids colour-profile mixing before the final SVG unpack.
 */
export function bakeLensMap(width: number, height: number, radius: number) {
  if (!Number.isFinite(width + height + radius) || width <= 0 || height <= 0 || radius < 0) return null;
  const canvas = document.createElement("canvas");
  canvas.width = Math.min(1024, Math.ceil(width / 2));
  canvas.height = Math.min(384, Math.ceil(height));
  const context = canvas.getContext("2d");
  if (!context) return null;
  const pixels = context.createImageData(canvas.width, canvas.height);
  const scale = 96;
  const r = Math.max(.001, Math.min(radius, height / 2, width / 2));
  for (let j = 0; j < canvas.height; j++) {
    for (let i = 0; i < canvas.width; i++) {
      const x = (i + 0.5) * width / canvas.width;
      const y = (j + 0.5) * height / canvas.height;
      const nx = x - Math.max(r, Math.min(width - r, x));
      const ny = y - Math.max(r, Math.min(height - r, y));
      const distance = Math.hypot(nx, ny);
      // Neutral central plane, rounded shoulder, then a steep inward lip.
      const t = Math.max(0, Math.min(1, (distance / r - 0.56) / 0.44));
      const shoulder = 9 * t * t * (3 - 2 * t);
      const lip = 21 * Math.pow(t, 7);
      const pull = (shoulder + lip) * Math.min(1, r / 34);
      const dx = distance ? -nx / distance * pull + (0.5 - x / width) * pull * 0.18 : 0;
      const dy = distance ? -ny / distance * pull : 0;
      const grey = Math.round(255 * (0.5 + dx / scale));
      const at = (j * canvas.width + i) * 4;
      pixels.data[at] = pixels.data[at + 1] = pixels.data[at + 2] = grey;
      pixels.data[at + 3] = Math.round(255 * (0.75 + dy / scale / 2));
    }
  }
  context.putImageData(pixels, 0, 0);
  return { url: canvas.toDataURL(), scale };
}

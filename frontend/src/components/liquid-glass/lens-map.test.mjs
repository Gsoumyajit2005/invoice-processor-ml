import assert from 'node:assert/strict';
import test from 'node:test';
import { readFileSync } from 'node:fs';
import ts from 'typescript';
const source = readFileSync(new URL('./lens-map.ts', import.meta.url), 'utf8');
const compiled = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ESNext } }).outputText;
const { bakeLensMap } = await import('data:text/javascript;base64,' + Buffer.from(compiled).toString('base64'));

let raster;
globalThis.document = { createElement: () => ({
  width: 0, height: 0,
  getContext: () => ({
    createImageData: (width, height) => ({ width, height, data: new Uint8ClampedArray(width * height * 4) }),
    putImageData: image => { raster = image; },
  }),
  toDataURL: () => 'data:image/png;base64,test',
}) };
function field(w, h, r) {
  const result = bakeLensMap(w, h, r);
  const image = raster;
  return { result, sample: (x, y) => {
    const i = (Math.min(image.height - 1, Math.floor(y / h * image.height)) * image.width + Math.min(image.width - 1, Math.floor(x / w * image.width))) * 4;
    return { x: (image.data[i] / 255 - .5) * result.scale,
      y: ((image.data[i + 3] / 255) * 2 - 1.5) * result.scale };
  } };
}
test('center remains neutral within 8-bit map quantization', () => {
  const { sample } = field(440, 76, 34);
  for (const x of [70, 220, 370]) {
    const d = sample(x, 38);
    assert.ok(Math.abs(d.x) < .4 && Math.abs(d.y) < .4);
  }
});
test('opposite rims sample inward, not outside the captured backdrop', () => {
  const { sample } = field(440, 76, 34);
  assert.ok(sample(220, 0).y > 20);
  assert.ok(sample(220, 75).y < -20);
  assert.ok(sample(0, 38).x > 20);
  assert.ok(sample(438, 38).x < -20);
});
test('rounded cap has both displacement axes, with bounded reach', () => {
  const { sample } = field(440, 76, 34);
  const a = sample(10, 10);
  assert.ok(a.x > 0 && a.y > 0);
  assert.ok(Math.hypot(a.x, a.y) < 35);
});
test('mobile dimensions and radius clamping retain neutral center', () => {
  const { sample, result } = field(256, 72, 100);
  assert.ok(result.url.startsWith('data:image/png'));
  assert.ok(Math.abs(sample(128, 36).y) < .4);
});

test('small-radius controls keep displacement proportional and within capture bounds', () => {
  for (const radius of [8, 12, 20, 28, 34]) {
    const { sample } = field(320, 72, radius);
    const top = sample(160, 0);
    assert.ok(top.y > 0 && top.y <= radius, `radius ${radius}: inward reach ${top.y}`);
  }
});
test('large fields cap raster allocation without losing geometric center', () => {
  const { sample } = field(3000, 1000, 40);
  assert.ok(raster.width <= 1024 && raster.height <= 384);
  assert.ok(Math.abs(sample(1500, 500).x) < .4);
});
test('invalid sizes fail safely instead of allocating or emitting broken maps', () => {
  for (const [w, h, r] of [[0, 50, 20], [-1, 50, 20], [100, 0, 20], [100, 50, -1], [Infinity, 50, 20], [NaN, 50, 20]]) {
    assert.equal(bakeLensMap(w, h, r), null);
  }
});

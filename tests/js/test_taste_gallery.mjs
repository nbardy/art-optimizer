import assert from "node:assert/strict";
import {
  orderedGalleryCells,
  parseStrengths,
  tasteIdFromLabel,
} from "../../art_optimizer/static/taste_gallery.js";

assert.deepEqual(parseStrengths("0.25, 0.5,1,1.25"), [0.25, 0.5, 1, 1.25]);
assert.equal(tasteIdFromLabel("Taste A"), "taste-1");
assert.equal(tasteIdFromLabel("Taste C"), "taste-3");
assert.equal(tasteIdFromLabel("waiting"), null);

const ordered = orderedGalleryCells({
  cells: [
    { cell_id: "r2c2", row: 1, column: 1 },
    { cell_id: "r1c2", row: 0, column: 1 },
    { cell_id: "r1c1", row: 0, column: 0 },
  ],
});
assert.deepEqual(ordered.map((item) => item.cell_id), ["r1c1", "r1c2", "r2c2"]);

console.log("taste gallery UI checks passed");

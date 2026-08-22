import assert from "node:assert/strict";
import { ConceptLibrary } from "../../art_optimizer/static/experiment_core.js";

class MemoryStorage {
  constructor() {
    this.values = new Map();
  }
  getItem(key) {
    return this.values.get(key) ?? null;
  }
  setItem(key, value) {
    this.values.set(key, String(value));
  }
}

function snapshot(basis = "basis-a") {
  return {
    current_design: {
      action: Array(8).fill(0),
      control_basis_revision: basis,
    },
  };
}

const storage = new MemoryStorage();
const library = new ConceptLibrary(storage);
const base = snapshot();
assert.equal(
  library.observeCommit(base, {
    action: [0.4, 0, 0, 0, 0, 0, 0, 0],
    image_url: "/a.png",
    design_id: "a",
  }),
  true,
);
assert.equal(library.view(base).length, 1);
assert.equal(library.view(base)[0].effective, true);

library.observeCommit(base, {
  action: [0.5, 0.01, 0, 0, 0, 0, 0, 0],
  image_url: "/b.png",
  design_id: "b",
});
assert.equal(library.view(base).length, 1, "aligned accepted deltas should merge");
assert.equal(library.view(base)[0].support, 2);

const conceptId = library.view(base)[0].conceptId;
library.setActivation(base, conceptId, "off");
assert.equal(library.view(base)[0].effective, false);
library.setActivation(base, conceptId, "on");
const composed = library.composition(base);
assert.equal(composed.length, 8);
assert.ok(composed[0] > 0);

library.observeReroll(base, [
  { action: [0.6, 0, 0, 0, 0, 0, 0, 0] },
  { action: [0.7, 0.02, 0, 0, 0, 0, 0, 0] },
]);
assert.ok(library.view(base)[0].opposition > 0);

const other = snapshot("basis-b");
assert.equal(library.view(other).length, 0, "control bases must never share numeric lanes");
console.log("concept library checks passed");

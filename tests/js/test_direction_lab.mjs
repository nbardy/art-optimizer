import assert from "node:assert/strict";

import {
  appendCenterStep,
  formatRms,
  nextPointSeed,
  popCenterStep,
} from "../../art_optimizer/static/direction_lab.js";

const first = nextPointSeed(1001);
const second = nextPointSeed(1001);
assert.equal(first, second);
assert.notEqual(first, 1001);
assert.ok(Number.isSafeInteger(first));

const step = {
  codec_id: "orthogonal-shell",
  point_seed: 1001,
  candidate_index: 2,
  radius: 0.4,
};
const original = [];
const extended = appendCenterStep(original, step);
assert.deepEqual(original, []);
assert.deepEqual(extended, [step]);
assert.notEqual(extended[0], step, "the stored path step must be copied");
assert.deepEqual(popCenterStep(extended), []);
assert.equal(formatRms(0.4), "0.400×");

console.log("direction-lab browser helpers passed");

import assert from "node:assert/strict";
import {
  modelBarWidths,
  readyExposureIds,
  summarizeTasteModel,
} from "../../art_optimizer/static/emergent_tastes.js";

assert.deepEqual(summarizeTasteModel({ observation_count: 0 }), {
  heading: "Learning the first taste",
  copy: "Vote on a few fixed-root embedding variations. Extra tastes must improve future predictions before they appear.",
});

const summary = summarizeTasteModel({
  observation_count: 12,
  selected_component_count: 2,
  score_advantage_over_one_taste: 4.25,
});
assert.equal(summary.heading, "2 tastes are earning their keep");
assert.match(summary.copy, /4\.25 log-score advantage/);

assert.deepEqual(modelBarWidths([]), []);
const widths = modelBarWidths([
  { penalized_score: -12 },
  { penalized_score: -4 },
  { penalized_score: -9 },
]);
assert.equal(widths[1], 100);
assert.ok(widths[0] < widths[2]);

const ids = readyExposureIds(
  {
    active_round: {
      candidates: [
        { candidate_id: "ready", status: "ready" },
        { candidate_id: "loading", status: "rendering" },
      ],
    },
  },
  new Set(["stale", "ready", "loading"]),
);
assert.deepEqual(ids, ["ready"]);

console.log("emergent taste UI checks passed");

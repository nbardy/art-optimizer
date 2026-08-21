import { createStudioController } from "/static/experiment_core.js";
import {
  createCandidateCard,
  createExposureTracker,
  mountExperimentSwitcher,
  renderConceptCards,
  renderHistory,
  setImageSource,
  showToast,
  wireStartForm,
} from "/static/experiment_components.js";

const studio = createStudioController();
const tracker = createExposureTracker(studio);
const elements = Object.fromEntries(
  [
    "start-screen",
    "start-form",
    "prompt",
    "studio",
    "experiment-switcher",
    "world-label",
    "learning-label",
    "connection-label",
    "current-image",
    "preview-image",
    "candidate-container",
    "stage-caption",
    "concept-status",
    "concept-count",
    "concept-dots",
    "concept-drawer",
    "concept-close",
    "concept-list",
    "favorite-current",
    "reroll",
    "recast",
    "new-world",
    "history-toggle",
    "history-drawer",
    "history-close",
    "history-strip",
    "toast",
  ].map((id) => [id, document.getElementById(id)]),
);

function errorToast(error) {
  showToast(elements.toast, error.message || String(error));
}

function endPreview() {
  elements.previewImage.classList.add("hidden");
  elements.previewImage.removeAttribute("src");
  elements.stageCaption.textContent = "CURRENT DESIGN";
}

function preview(candidate) {
  setImageSource(elements.previewImage, candidate.image_url);
  elements.previewImage.classList.remove("hidden");
  elements.stageCaption.textContent = `PREVIEW ${candidate.slot}`;
}

function renderCandidates(state) {
  for (const old of elements.candidateContainer.querySelectorAll(".experiment-candidate")) {
    tracker.unobserve(old);
  }
  const candidates = state.snapshot?.active_round?.candidates || [];
  elements.candidateContainer.replaceChildren(
    ...candidates.map((candidate) =>
      createCandidateCard({
        candidate,
        studio,
        exposureTracker: tracker,
        favorites: state.snapshot.favorites,
        onPreview: preview,
        onPreviewEnd: endPreview,
        onCommitted: endPreview,
        onError: errorToast,
      }),
    ),
  );
}

studio.subscribe((state) => {
  const snapshot = state.snapshot;
  elements.connectionLabel.textContent = state.connection;
  elements.connectionLabel.className = `connection ${state.connection}`;
  if (!snapshot) return;

  elements.startScreen.classList.add("hidden");
  elements.studio.classList.remove("hidden");
  setImageSource(elements.currentImage, snapshot.current_design.image_url);
  elements.worldLabel.textContent = ` · world ${snapshot.world.world_id.slice(-6)}`;
  elements.learningLabel.textContent = `${snapshot.learner.observation_count} choices`;

  const currentFavorite = snapshot.favorites.includes(snapshot.current_design.design_id);
  elements.favoriteCurrent.textContent = currentFavorite ? "★ Favorited" : "☆ Favorite current";
  elements.favoriteCurrent.classList.toggle("active", currentFavorite);

  const activeConcepts = state.concepts.filter((concept) => concept.effective);
  elements.conceptCount.textContent = `${activeConcepts.length} active / ${state.concepts.length} learned lanes`;
  elements.conceptDots.replaceChildren(
    ...state.concepts.slice(0, 8).map((concept) => {
      const dot = document.createElement("span");
      dot.className = `concept-dot${concept.effective ? " active" : ""}`;
      dot.title = `${concept.label}: ${concept.activation}`;
      return dot;
    }),
  );
  elements.recast.disabled = state.busy || activeConcepts.length === 0;
  for (const button of [
    elements.favoriteCurrent,
    elements.reroll,
    elements.newWorld,
    elements.historyToggle,
  ]) {
    button.disabled = state.busy;
  }

  renderCandidates(state);
  renderConceptCards(elements.conceptList, state, studio);
  renderHistory(elements.historyStrip, snapshot.history || [], studio, errorToast);
});

wireStartForm({
  studio,
  form: elements.startForm,
  prompt: elements.prompt,
  startScreen: elements.startScreen,
  shell: elements.studio,
  onError: errorToast,
});
mountExperimentSwitcher(elements.experimentSwitcher, "implicit-lanes").catch(errorToast);

studio.resume().then((snapshot) => {
  if (snapshot) {
    elements.startScreen.classList.add("hidden");
    elements.studio.classList.remove("hidden");
  }
});

elements.favoriteCurrent.addEventListener("click", async () => {
  try {
    const result = await studio.favorite(studio.current().snapshot?.current_design.design_id);
    if (result) showToast(elements.toast, result.favorite ? "Added to persistent taste" : "Removed from favorites");
  } catch (error) {
    errorToast(error);
  }
});
elements.reroll.addEventListener("click", async () => {
  endPreview();
  try {
    const result = await studio.reroll();
    if (result) {
      showToast(
        elements.toast,
        result.exposureCount >= 2 ? "Kept the image; weak no to exposed moves" : "Skipped an underexposed round",
      );
    }
  } catch (error) {
    errorToast(error);
  }
});
elements.recast.addEventListener("click", async () => {
  endPreview();
  try {
    await studio.newWorld("composition");
    showToast(elements.toast, "Fresh seed, same active concept composition");
  } catch (error) {
    errorToast(error);
  }
});
elements.newWorld.addEventListener("click", async () => {
  endPreview();
  try {
    await studio.newWorld("taste_guided");
    showToast(elements.toast, "New taste-guided world");
  } catch (error) {
    errorToast(error);
  }
});
elements.conceptStatus.addEventListener("click", () => elements.conceptDrawer.classList.remove("hidden"));
elements.conceptClose.addEventListener("click", () => elements.conceptDrawer.classList.add("hidden"));
elements.historyToggle.addEventListener("click", () => elements.historyDrawer.classList.remove("hidden"));
elements.historyClose.addEventListener("click", () => elements.historyDrawer.classList.add("hidden"));
window.addEventListener("beforeunload", () => {
  tracker.clear();
  studio.close();
});

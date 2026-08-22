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
const byId = (id) => document.getElementById(id);
const elements = {
  startScreen: byId("start-screen"),
  startForm: byId("start-form"),
  prompt: byId("prompt"),
  studio: byId("studio"),
  switcher: byId("experiment-switcher"),
  world: byId("world-label"),
  learning: byId("learning-label"),
  connection: byId("connection-label"),
  current: byId("current-image"),
  preview: byId("preview-image"),
  caption: byId("stage-caption"),
  candidates: byId("candidate-container"),
  concepts: byId("concept-list"),
  summary: byId("composition-summary"),
  favorite: byId("favorite-current"),
  reroll: byId("reroll"),
  recast: byId("recast"),
  neutral: byId("neutral-world"),
  newWorld: byId("new-world"),
  clear: byId("clear-concepts"),
  historyToggle: byId("history-toggle"),
  historyDrawer: byId("history-drawer"),
  historyClose: byId("history-close"),
  history: byId("history-strip"),
  toast: byId("toast"),
};

function errorToast(error) {
  showToast(elements.toast, error.message || String(error));
}

function preview(candidate) {
  setImageSource(elements.preview, candidate.image_url);
  elements.preview.classList.remove("hidden");
  elements.caption.textContent = `PREVIEW ${candidate.slot}`;
}

function endPreview() {
  elements.preview.classList.add("hidden");
  elements.preview.removeAttribute("src");
  elements.caption.textContent = "CURRENT DESIGN";
}

function renderCandidates(state) {
  for (const old of elements.candidates.querySelectorAll(".experiment-candidate")) tracker.unobserve(old);
  elements.candidates.replaceChildren(
    ...(state.snapshot?.active_round?.candidates || []).map((candidate) =>
      createCandidateCard({
        candidate,
        studio,
        exposureTracker: tracker,
        favorites: state.snapshot.favorites,
        showRole: false,
        onPreview: preview,
        onPreviewEnd: endPreview,
        onCommitted: endPreview,
        onError: errorToast,
      }),
    ),
  );
}

studio.subscribe((state) => {
  elements.connection.textContent = state.connection;
  elements.connection.className = `connection ${state.connection}`;
  const snapshot = state.snapshot;
  if (!snapshot) return;
  elements.startScreen.classList.add("hidden");
  elements.studio.classList.remove("hidden");
  setImageSource(elements.current, snapshot.current_design.image_url);
  elements.world.textContent = ` · world ${snapshot.world.world_id.slice(-6)}`;
  elements.learning.textContent = `${snapshot.learner.observation_count} choices · radius ${snapshot.search.radius.toFixed(2)}`;

  const currentFavorite = snapshot.favorites.includes(snapshot.current_design.design_id);
  elements.favorite.textContent = currentFavorite ? "★ Favorited" : "☆ Favorite current";
  elements.favorite.classList.toggle("active", currentFavorite);
  const active = state.concepts.filter((concept) => concept.effective);
  elements.summary.textContent = `${active.length} active concepts · ${state.concepts.length} learned`;
  elements.recast.disabled = state.busy || active.length === 0;
  for (const button of [elements.favorite, elements.reroll, elements.neutral, elements.newWorld]) {
    button.disabled = state.busy;
  }

  renderCandidates(state);
  renderConceptCards(elements.concepts, state, studio);
  renderHistory(elements.history, snapshot.history || [], studio, errorToast);
});

wireStartForm({
  studio,
  form: elements.startForm,
  prompt: elements.prompt,
  startScreen: elements.startScreen,
  shell: elements.studio,
  onError: errorToast,
});
mountExperimentSwitcher(elements.switcher, "concept-shelf").catch(errorToast);
studio.resume();

elements.favorite.addEventListener("click", async () => {
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
    if (result) showToast(elements.toast, result.exposureCount >= 2 ? "Anchor kept" : "Round skipped");
  } catch (error) {
    errorToast(error);
  }
});
elements.recast.addEventListener("click", async () => {
  endPreview();
  try {
    await studio.newWorld("composition");
    showToast(elements.toast, "Recast active concepts on a new seed");
  } catch (error) {
    errorToast(error);
  }
});
elements.neutral.addEventListener("click", async () => {
  endPreview();
  try {
    await studio.newWorld("neutral");
    showToast(elements.toast, "Neutral control-space origin on a new seed");
  } catch (error) {
    errorToast(error);
  }
});
elements.newWorld.addEventListener("click", async () => {
  endPreview();
  try {
    await studio.newWorld("taste_guided");
    showToast(elements.toast, "New world guided by persistent taste");
  } catch (error) {
    errorToast(error);
  }
});
elements.clear.addEventListener("click", () => {
  if (studio.clearConcepts()) showToast(elements.toast, "Cleared concepts for this model basis");
});
elements.historyToggle.addEventListener("click", () => elements.historyDrawer.classList.remove("hidden"));
elements.historyClose.addEventListener("click", () => elements.historyDrawer.classList.add("hidden"));
window.addEventListener("beforeunload", () => {
  tracker.clear();
  studio.close();
});

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
  activeCandidates: byId("active-candidates"),
  alternateCandidates: byId("alternate-candidates"),
  discoveryCandidates: byId("discovery-candidates"),
  activeConcepts: byId("active-concept-strip"),
  alternateConcepts: byId("alternate-concept-strip"),
  favorite: byId("favorite-current"),
  reroll: byId("reroll"),
  recast: byId("recast"),
  newWorld: byId("new-world"),
  conceptToggle: byId("concept-toggle"),
  conceptDrawer: byId("concept-drawer"),
  conceptClose: byId("concept-close"),
  conceptList: byId("concept-list"),
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
  const lane = studio.classifyCandidate(candidate);
  elements.caption.textContent = `PREVIEW ${candidate.slot} · ${lane.toUpperCase()}`;
}

function endPreview() {
  elements.preview.classList.add("hidden");
  elements.preview.removeAttribute("src");
  elements.caption.textContent = "CURRENT DESIGN";
}

function emptyLane(label) {
  const message = document.createElement("p");
  message.className = "lane-empty";
  message.textContent = label;
  return message;
}

function renderCandidateLane(container, candidates, state, lane) {
  for (const old of container.querySelectorAll(".experiment-candidate")) {
    tracker.unobserve(old);
  }
  if (!candidates.length) {
    container.replaceChildren(
      emptyLane(
        lane === "active"
          ? "No candidate currently reinforces an active learned lane."
          : lane === "alternate"
            ? "No muted learned lane is represented in this round."
            : "Discovery candidates will appear here as the library becomes explanatory.",
      ),
    );
    return;
  }
  container.replaceChildren(
    ...candidates.map((candidate) =>
      createCandidateCard({
        candidate,
        studio,
        exposureTracker: tracker,
        favorites: state.snapshot.favorites,
        laneLabel: lane,
        onPreview: preview,
        onPreviewEnd: endPreview,
        onCommitted: endPreview,
        onError: errorToast,
      }),
    ),
  );
}

function renderCandidates(state) {
  const grouped = { active: [], alternate: [], discovery: [] };
  for (const candidate of state.snapshot?.active_round?.candidates || []) {
    grouped[studio.classifyCandidate(candidate)].push(candidate);
  }
  renderCandidateLane(elements.activeCandidates, grouped.active, state, "active");
  renderCandidateLane(
    elements.alternateCandidates,
    grouped.alternate,
    state,
    "alternate",
  );
  renderCandidateLane(
    elements.discoveryCandidates,
    grouped.discovery,
    state,
    "discovery",
  );
}

function makeConceptChip(concept) {
  const chip = document.createElement("button");
  chip.type = "button";
  chip.className = `lane-chip${concept.effective ? " active" : ""}`;
  chip.textContent = `${concept.label} · ${concept.activation}`;
  chip.title = `${concept.support.toFixed(1)} yes / ${concept.opposition.toFixed(1)} no; click to cycle auto/on/off`;
  chip.addEventListener("click", () => studio.cycleConceptActivation(concept.conceptId));
  return chip;
}

function renderConceptStrips(state) {
  const active = state.concepts.filter((concept) => concept.effective);
  const alternate = state.concepts.filter((concept) => !concept.effective);
  elements.activeConcepts.replaceChildren(
    ...(active.length
      ? active.map(makeConceptChip)
      : [emptyLane("No active learned lanes yet.")]),
  );
  elements.alternateConcepts.replaceChildren(
    ...(alternate.length
      ? alternate.map(makeConceptChip)
      : [emptyLane("No inactive learned lanes yet.")]),
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
  elements.learning.textContent = `${snapshot.learner.observation_count} choices · ${state.concepts.length} learned lanes`;

  const currentFavorite = snapshot.favorites.includes(snapshot.current_design.design_id);
  elements.favorite.textContent = currentFavorite ? "★ Favorited" : "☆ Favorite current";
  elements.favorite.classList.toggle("active", currentFavorite);
  const active = state.concepts.filter((concept) => concept.effective);
  elements.recast.disabled = state.busy || active.length === 0;
  for (const button of [
    elements.favorite,
    elements.reroll,
    elements.newWorld,
    elements.conceptToggle,
    elements.historyToggle,
  ]) {
    button.disabled = state.busy;
  }

  renderConceptStrips(state);
  renderCandidates(state);
  renderConceptCards(elements.conceptList, state, studio);
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
mountExperimentSwitcher(elements.switcher, "lane-board").catch(errorToast);
studio.resume();

elements.favorite.addEventListener("click", async () => {
  try {
    const result = await studio.favorite(studio.current().snapshot?.current_design.design_id);
    if (result) {
      showToast(
        elements.toast,
        result.favorite ? "Added to persistent taste" : "Removed from favorites",
      );
    }
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
        result.exposureCount >= 2
          ? "Kept the image; exposed lanes received weak no evidence"
          : "Skipped an underexposed round",
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
    showToast(elements.toast, "New seed rendered from the active concept composition");
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

elements.conceptToggle.addEventListener("click", () => {
  elements.conceptDrawer.classList.remove("hidden");
});
elements.conceptClose.addEventListener("click", () => {
  elements.conceptDrawer.classList.add("hidden");
});
elements.historyToggle.addEventListener("click", () => {
  elements.historyDrawer.classList.remove("hidden");
});
elements.historyClose.addEventListener("click", () => {
  elements.historyDrawer.classList.add("hidden");
});
window.addEventListener("beforeunload", () => {
  tracker.clear();
  studio.close();
});

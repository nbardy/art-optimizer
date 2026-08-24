import { currentExposure, formatRequestError } from "./experiment_core.js";

export function summarizeTasteModel(model) {
  const count = Number(model?.selected_component_count || 0);
  const votes = Number(model?.observation_count || 0);
  const advantage = Number(model?.score_advantage_over_one_taste || 0);
  if (votes === 0) {
    return {
      heading: "Learning the first taste",
      copy: "Vote on a few fixed-root embedding variations. Extra tastes must improve future predictions before they appear.",
    };
  }
  if (count <= 1) {
    return {
      heading: "One coherent taste so far",
      copy: `${votes} vote${votes === 1 ? "" : "s"} recorded. More complex explanations are still running as chronological tests.`,
    };
  }
  return {
    heading: `${count} tastes are earning their keep`,
    copy: `The ${count}-taste model has a ${advantage.toFixed(2)} log-score advantage over one taste after complexity cost.`,
  };
}

export function modelBarWidths(models = []) {
  if (!models.length) return [];
  const scores = models.map((item) => Number(item.penalized_score || 0));
  const minimum = Math.min(...scores);
  const maximum = Math.max(...scores);
  const span = Math.max(maximum - minimum, 1e-9);
  return scores.map((score) => 15 + 85 * ((score - minimum) / span));
}

export function readyExposureIds(snapshot, exposedCandidateIds) {
  return currentExposure(snapshot, exposedCandidateIds).ids;
}

const roleLabels = {
  best_local: "local",
  diverse_posterior: "different",
  informative_probe: "probe",
  controlled_surprise: "farther",
};

function boot() {
  const elements = {
    startScreen: document.querySelector("#start-screen"),
    startForm: document.querySelector("#start-form"),
    prompt: document.querySelector("#prompt"),
    studio: document.querySelector("#studio"),
    currentImage: document.querySelector("#current-image"),
    previewImage: document.querySelector("#preview-image"),
    previewLabel: document.querySelector("#preview-label"),
    canvasLoader: document.querySelector("#canvas-loader"),
    corners: document.querySelector("#candidate-corners"),
    noneFit: document.querySelector("#none-fit"),
    explore: document.querySelector("#explore"),
    historyToggle: document.querySelector("#history-toggle"),
    historyDrawer: document.querySelector("#history-drawer"),
    historyStrip: document.querySelector("#history-strip"),
    historyCount: document.querySelector("#history-count"),
    learningLabel: document.querySelector("#learning-label"),
    connectionLabel: document.querySelector("#connection-label"),
    worldLabel: document.querySelector("#world-label"),
    roundLabel: document.querySelector("#round-label"),
    tasteHeading: document.querySelector("#taste-heading"),
    tasteSummary: document.querySelector("#taste-summary"),
    tasteList: document.querySelector("#taste-list"),
    modelScoreboard: document.querySelector("#model-scoreboard"),
    toast: document.querySelector("#toast"),
  };

  const state = {
    snapshot: null,
    sessionId: null,
    eventSource: null,
    previewCandidateId: null,
    exposedCandidateIds: new Set(),
    exposureTimers: new Map(),
    activeRoundId: null,
    busy: false,
    historyOpen: false,
    reconnectTimer: null,
  };

  const exposureObserver = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        const candidateId = entry.target.dataset.candidateId;
        if (!candidateId) continue;
        if (entry.isIntersecting && entry.intersectionRatio >= 0.5) {
          scheduleExposure(candidateId, entry.target);
        } else {
          cancelExposureTimer(candidateId);
        }
      }
    },
    { threshold: [0, 0.5, 1] },
  );

  function makeRequestId() {
    if (globalThis.crypto?.randomUUID) {
      return `command_${globalThis.crypto.randomUUID()}`;
    }
    return `command_${Date.now().toString(36)}_${Math.random().toString(36).slice(2)}`;
  }

  function commandPayload(extra = {}) {
    return {
      request_id: makeRequestId(),
      expected_mutation_version: state.snapshot?.mutation_version ?? null,
      ...extra,
    };
  }

  async function api(path, options = {}) {
    const response = await fetch(path, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...(options.headers || {}),
      },
    });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) {
      const error = new Error(formatRequestError(body.detail, response.status));
      error.status = response.status;
      throw error;
    }
    return body;
  }

  function showToast(message) {
    elements.toast.textContent = message;
    elements.toast.classList.remove("hidden");
    window.clearTimeout(showToast.timer);
    showToast.timer = window.setTimeout(
      () => elements.toast.classList.add("hidden"),
      2800,
    );
  }

  function currentReadyExposure() {
    return currentExposure(state.snapshot, state.exposedCandidateIds);
  }

  function setBusy(value) {
    state.busy = value;
    const exposureCount = currentReadyExposure().ids.length;
    elements.noneFit.disabled = value || exposureCount < 2;
    elements.explore.disabled = value || !state.snapshot?.active_round;
    elements.corners.classList.toggle("command-pending", value);
    document.querySelectorAll(".taste-resume").forEach((button) => {
      button.disabled = value || !button.dataset.branchNodeId;
    });
  }

  function setConnection(status) {
    elements.connectionLabel.textContent = status;
    elements.connectionLabel.classList.toggle("online", status === "live");
    elements.connectionLabel.classList.toggle("offline", status === "offline");
  }

  async function recoverAfterConflict(error) {
    if (error.status !== 409 || !state.sessionId) return;
    try {
      applySnapshot(
        await api(`/api/emergent-tastes/sessions/${state.sessionId}`),
      );
    } catch {
      // Preserve the original command error.
    }
  }

  async function startSession(prompt) {
    if (state.busy) return;
    setBusy(true);
    const submit = elements.startForm.querySelector("button[type='submit']");
    submit.disabled = true;
    submit.textContent = "Building fixed-root world…";
    try {
      const snapshot = await api("/api/emergent-tastes/sessions", {
        method: "POST",
        body: JSON.stringify({ prompt }),
      });
      state.sessionId = snapshot.session_id;
      localStorage.setItem("artOptimizerEmergentSessionId", state.sessionId);
      elements.startScreen.classList.add("hidden");
      elements.studio.classList.remove("hidden");
      applySnapshot(snapshot);
      connectStream();
    } catch (error) {
      showToast(error.message);
    } finally {
      setBusy(false);
      submit.disabled = false;
      submit.textContent = "Begin fixed-root search";
    }
  }

  async function resumeSession(sessionId) {
    try {
      const snapshot = await api(`/api/emergent-tastes/sessions/${sessionId}`);
      state.sessionId = sessionId;
      elements.startScreen.classList.add("hidden");
      elements.studio.classList.remove("hidden");
      applySnapshot(snapshot);
      connectStream();
    } catch {
      localStorage.removeItem("artOptimizerEmergentSessionId");
    }
  }

  function connectStream() {
    if (!state.sessionId) return;
    state.eventSource?.close();
    window.clearTimeout(state.reconnectTimer);
    setConnection("connecting");
    const source = new EventSource(
      `/api/emergent-tastes/sessions/${state.sessionId}/events`,
    );
    state.eventSource = source;
    source.addEventListener("open", () => {
      if (state.eventSource === source) setConnection("live");
    });
    source.addEventListener("session.snapshot", (event) => {
      if (state.eventSource !== source) return;
      applySnapshot(JSON.parse(event.data));
    });
    source.addEventListener("error", () => {
      if (state.eventSource !== source) return;
      setConnection("offline");
      source.close();
      state.reconnectTimer = window.setTimeout(connectStream, 1400);
    });
  }

  function setImageSource(image, url) {
    if (!url) return;
    const absolute = new URL(url, location.href).href;
    if (image.src !== absolute) image.src = url;
  }

  function applySnapshot(snapshot) {
    state.snapshot = snapshot;
    if (snapshot.active_round?.round_id !== state.activeRoundId) {
      state.activeRoundId = snapshot.active_round?.round_id || null;
      state.exposedCandidateIds.clear();
      for (const timer of state.exposureTimers.values()) window.clearTimeout(timer);
      state.exposureTimers.clear();
      endPreview();
    }

    setImageSource(elements.currentImage, snapshot.current_design.image_url);
    elements.canvasLoader.classList.toggle(
      "hidden",
      snapshot.status !== "transitioning",
    );
    elements.worldLabel.textContent = `root ${String(snapshot.world.seed).slice(-7)}`;
    elements.roundLabel.textContent = snapshot.active_round
      ? `ROUND ${snapshot.search.planner_step + 1}`
      : "";
    elements.learningLabel.textContent = `${snapshot.emergent_tastes.observation_count} tested vote${snapshot.emergent_tastes.observation_count === 1 ? "" : "s"} · radius ${snapshot.search.radius.toFixed(2)}`;

    renderCandidates(snapshot.active_round?.candidates || []);
    renderTasteProjection(snapshot.emergent_tastes || {});
    renderHistory(snapshot.history || []);
    elements.historyCount.textContent = String(
      snapshot.history_total ?? snapshot.history?.length ?? 0,
    );
    setBusy(state.busy);
  }

  function renderCandidates(candidates) {
    const existing = new Map(
      Array.from(elements.corners.querySelectorAll(".candidate-card")).map((card) => [
        card.dataset.candidateId,
        card,
      ]),
    );
    const fragment = document.createDocumentFragment();
    for (const candidate of candidates) {
      let card = existing.get(candidate.candidate_id);
      if (!card) card = buildCandidateCard(candidate);
      updateCandidateCard(card, candidate);
      fragment.appendChild(card);
      existing.delete(candidate.candidate_id);
    }
    for (const stale of existing.values()) exposureObserver.unobserve(stale);
    elements.corners.replaceChildren(fragment);
  }

  function buildCandidateCard(candidate) {
    const card = document.createElement("div");
    card.className = "candidate-card loading";
    card.dataset.candidateId = candidate.candidate_id;
    card.dataset.slot = String(candidate.slot);
    card.tabIndex = 0;
    card.setAttribute("role", "button");
    card.innerHTML = `
      <div class="candidate-skeleton"></div>
      <img class="candidate-image hidden" alt="Embedding variation ${candidate.slot}" draggable="false" />
      <span class="candidate-number">${candidate.slot}</span>
      <span class="candidate-role">${roleLabels[candidate.role] || candidate.role}</span>
    `;
    card.addEventListener("mouseenter", () => previewCandidate(candidate.candidate_id));
    card.addEventListener("mouseleave", () => endPreview(candidate.candidate_id));
    card.addEventListener("click", () => commitCandidate(candidate.candidate_id));
    card.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        commitCandidate(candidate.candidate_id);
      } else if (event.key === " ") {
        event.preventDefault();
        previewCandidate(candidate.candidate_id);
      }
    });
    card.addEventListener("keyup", (event) => {
      if (event.key === " ") endPreview(candidate.candidate_id);
    });
    exposureObserver.observe(card);
    return card;
  }

  function updateCandidateCard(card, candidate) {
    card.dataset.candidateId = candidate.candidate_id;
    card.dataset.slot = String(candidate.slot);
    const image = card.querySelector(".candidate-image");
    const skeleton = card.querySelector(".candidate-skeleton");
    const ready = candidate.status === "ready" && candidate.image_url;
    card.classList.toggle("loading", !ready);
    card.classList.toggle(
      "previewing",
      state.previewCandidateId === candidate.candidate_id,
    );
    card.setAttribute("aria-disabled", ready ? "false" : "true");
    if (ready) {
      image.onload = () => scheduleExposure(candidate.candidate_id, card);
      setImageSource(image, candidate.image_url);
      image.classList.remove("hidden");
      skeleton.classList.add("hidden");
      if (image.complete && image.naturalWidth > 0) {
        scheduleExposure(candidate.candidate_id, card);
      }
    } else {
      cancelExposureTimer(candidate.candidate_id);
      image.classList.add("hidden");
      skeleton.classList.remove("hidden");
    }
  }

  function getCandidate(candidateId) {
    return (
      state.snapshot?.active_round?.candidates.find(
        (candidate) => candidate.candidate_id === candidateId,
      ) || null
    );
  }

  function previewCandidate(candidateId) {
    const candidate = getCandidate(candidateId);
    if (!candidate || candidate.status !== "ready" || !candidate.image_url) return;
    state.previewCandidateId = candidateId;
    setImageSource(elements.previewImage, candidate.image_url);
    elements.previewImage.classList.remove("hidden");
    elements.previewLabel.textContent = `PREVIEW ${candidate.slot} · ${roleLabels[candidate.role] || candidate.role}`;
    document.querySelectorAll(".candidate-card").forEach((card) => {
      card.classList.toggle("previewing", card.dataset.candidateId === candidateId);
    });
    markExposed(candidateId);
  }

  function endPreview(candidateId = null) {
    if (candidateId && state.previewCandidateId !== candidateId) return;
    state.previewCandidateId = null;
    elements.previewImage.classList.add("hidden");
    elements.previewImage.removeAttribute("src");
    elements.previewLabel.textContent = "CURRENT DESIGN";
    document
      .querySelectorAll(".candidate-card.previewing")
      .forEach((card) => card.classList.remove("previewing"));
  }

  function cancelExposureTimer(candidateId) {
    const timer = state.exposureTimers.get(candidateId);
    if (timer) window.clearTimeout(timer);
    state.exposureTimers.delete(candidateId);
  }

  function scheduleExposure(candidateId, card) {
    if (
      state.exposedCandidateIds.has(candidateId) ||
      state.exposureTimers.has(candidateId)
    ) {
      return;
    }
    const candidate = getCandidate(candidateId);
    if (!candidate || candidate.status !== "ready") return;
    const timer = window.setTimeout(() => {
      state.exposureTimers.delete(candidateId);
      const rect = card.getBoundingClientRect();
      const visibleWidth = Math.max(
        0,
        Math.min(rect.right, innerWidth) - Math.max(rect.left, 0),
      );
      const visibleHeight = Math.max(
        0,
        Math.min(rect.bottom, innerHeight) - Math.max(rect.top, 0),
      );
      const fraction =
        (visibleWidth * visibleHeight) / Math.max(rect.width * rect.height, 1);
      if (
        document.visibilityState === "visible" &&
        card.isConnected &&
        fraction >= 0.5
      ) {
        markExposed(candidateId);
      }
    }, 320);
    state.exposureTimers.set(candidateId, timer);
  }

  function markExposed(candidateId) {
    state.exposedCandidateIds.add(candidateId);
    setBusy(state.busy);
  }

  async function commitCandidate(candidateId) {
    const candidate = getCandidate(candidateId);
    if (!candidate || candidate.status !== "ready" || state.busy) return;
    markExposed(candidateId);
    const exposed = currentReadyExposure();
    setBusy(true);
    endPreview();
    try {
      const snapshot = await api(
        `/api/emergent-tastes/sessions/${state.sessionId}/candidates/${candidateId}/commit`,
        {
          method: "POST",
          body: JSON.stringify(
            commandPayload({ exposed_candidate_ids: exposed.ids }),
          ),
        },
      );
      applySnapshot(snapshot);
    } catch (error) {
      await recoverAfterConflict(error);
      showToast(error.message);
    } finally {
      setBusy(false);
    }
  }

  async function noneFit() {
    const exposed = currentReadyExposure();
    if (state.busy || exposed.ids.length < 2) return;
    setBusy(true);
    endPreview();
    try {
      const snapshot = await api(
        `/api/emergent-tastes/sessions/${state.sessionId}/none-of-these`,
        {
          method: "POST",
          body: JSON.stringify(
            commandPayload({ exposed_candidate_ids: exposed.ids }),
          ),
        },
      );
      applySnapshot(snapshot);
      showToast("Recorded: the current image beat this slate");
    } catch (error) {
      await recoverAfterConflict(error);
      showToast(error.message);
    } finally {
      setBusy(false);
    }
  }

  async function explore() {
    if (state.busy || !state.snapshot?.active_round) return;
    setBusy(true);
    endPreview();
    try {
      const snapshot = await api(
        `/api/emergent-tastes/sessions/${state.sessionId}/explore`,
        {
          method: "POST",
          body: JSON.stringify(
            commandPayload({
              exposed_candidate_ids: currentReadyExposure().ids,
            }),
          ),
        },
      );
      applySnapshot(snapshot);
      showToast("No vote recorded; searching wider with the same seed");
    } catch (error) {
      await recoverAfterConflict(error);
      showToast(error.message);
    } finally {
      setBusy(false);
    }
  }

  function renderTasteProjection(model) {
    const summary = summarizeTasteModel(model);
    elements.tasteHeading.textContent = summary.heading;
    elements.tasteSummary.textContent = summary.copy;
    const fragment = document.createDocumentFragment();
    const components = model.components || [];
    if (!components.length) {
      const empty = document.createElement("div");
      empty.className = "taste-card";
      empty.innerHTML = `
        <div class="taste-card-header">
          <h3 class="taste-card-title">Taste A</h3>
          <span class="taste-status">waiting for votes</span>
        </div>
        <p class="taste-metrics">The first model exists as a broad prior.</p>
        <div class="taste-exemplars">
          <div class="taste-exemplar taste-empty-exemplar">NO<br />EXEMPLAR</div>
        </div>
      `;
      fragment.appendChild(empty);
    }
    for (const component of components) {
      const card = document.createElement("article");
      card.className = `taste-card${model.latest_taste_id === component.taste_id ? " latest" : ""}`;
      const exemplars = (component.exemplars || [])
        .map(
          (item) => `
            <div class="taste-exemplar">
              <img src="${item.image_url}" alt="Representative image for ${component.label}" />
            </div>
          `,
        )
        .join("");
      const missing = Math.max(0, 3 - (component.exemplars || []).length);
      const emptySlots = Array.from(
        { length: missing },
        () => '<div class="taste-exemplar taste-empty-exemplar">MORE<br />EVIDENCE</div>',
      ).join("");
      card.innerHTML = `
        <div class="taste-card-header">
          <h3 class="taste-card-title">${component.label}</h3>
          <span class="taste-status ${component.status}">${component.status}</span>
        </div>
        <p class="taste-metrics">${component.vote_count} assigned vote${component.vote_count === 1 ? "" : "s"} · ${component.evidence_mass.toFixed(1)} evidence mass</p>
        <div class="taste-exemplars">${exemplars}${emptySlots}</div>
        <button class="taste-resume" type="button" data-branch-node-id="${component.latest_branch_node_id || ""}">Resume from exemplar</button>
      `;
      const resume = card.querySelector(".taste-resume");
      resume.disabled = state.busy || !component.latest_branch_node_id;
      resume.addEventListener("click", () => {
        if (component.latest_branch_node_id) {
          restoreBranch(component.latest_branch_node_id, component.label);
        }
      });
      fragment.appendChild(card);
    }
    elements.tasteList.replaceChildren(fragment);
    renderModelScoreboard(model.models || []);
  }

  function renderModelScoreboard(models) {
    if (!models.length) {
      elements.modelScoreboard.replaceChildren();
      return;
    }
    const widths = modelBarWidths(models);
    const fragment = document.createDocumentFragment();
    const title = document.createElement("div");
    title.className = "model-scoreboard-title";
    title.textContent = "Chronological prediction test";
    fragment.appendChild(title);
    models.forEach((model, index) => {
      const row = document.createElement("div");
      row.className = `model-row${model.selected ? " selected" : ""}`;
      row.innerHTML = `
        <span>${model.k} taste${model.k === 1 ? "" : "s"}</span>
        <span class="model-track"><span class="model-fill" style="display:block;width:${widths[index].toFixed(1)}%"></span></span>
        <span class="model-state">${model.selected ? "active" : model.eligible ? "testing" : "waiting"}</span>
      `;
      fragment.appendChild(row);
    });
    elements.modelScoreboard.replaceChildren(fragment);
  }

  function renderHistory(history) {
    const fragment = document.createDocumentFragment();
    for (const item of history) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = `history-item${item.current ? " current" : ""}`;
      const image = document.createElement("img");
      image.src = item.image_url;
      image.alt = "Branch checkpoint";
      button.appendChild(image);
      button.addEventListener("click", () => restoreBranch(item.branch_node_id));
      fragment.appendChild(button);
    }
    elements.historyStrip.replaceChildren(fragment);
  }

  async function restoreBranch(branchNodeId, label = "checkpoint") {
    if (!branchNodeId || state.busy) return;
    setBusy(true);
    endPreview();
    try {
      const snapshot = await api(
        `/api/emergent-tastes/sessions/${state.sessionId}/history/${branchNodeId}/restore`,
        {
          method: "POST",
          body: JSON.stringify(commandPayload()),
        },
      );
      applySnapshot(snapshot);
      showToast(`Resumed ${label}; existing votes were not duplicated`);
    } catch (error) {
      await recoverAfterConflict(error);
      showToast(error.message);
    } finally {
      setBusy(false);
    }
  }

  elements.startForm.addEventListener("submit", (event) => {
    event.preventDefault();
    const prompt = elements.prompt.value.trim() || "an evolving impossible garden";
    startSession(prompt);
  });
  elements.noneFit.addEventListener("click", noneFit);
  elements.explore.addEventListener("click", explore);
  elements.historyToggle.addEventListener("click", () => {
    state.historyOpen = !state.historyOpen;
    elements.historyDrawer.classList.toggle("open", state.historyOpen);
  });

  document.addEventListener("keydown", (event) => {
    const tag = event.target.tagName;
    if (tag === "INPUT" || tag === "TEXTAREA" || !state.snapshot) return;
    const number = Number(event.key);
    if (number >= 1 && number <= 4 && !event.repeat) {
      const candidate = state.snapshot.active_round?.candidates.find(
        (item) => item.slot === number,
      );
      if (candidate) {
        event.preventDefault();
        commitCandidate(candidate.candidate_id);
      }
      return;
    }
    const key = event.key.toLowerCase();
    if (["e", "x", "h"].includes(key)) event.preventDefault();
    if (key === "e") explore();
    if (key === "x") noneFit();
    if (key === "h") elements.historyToggle.click();
    if (event.key === "Escape") endPreview();
  });

  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState !== "visible") endPreview();
  });
  window.addEventListener("beforeunload", () => state.eventSource?.close());

  const remembered = localStorage.getItem("artOptimizerEmergentSessionId");
  if (remembered) resumeSession(remembered);
}

if (typeof document !== "undefined") boot();

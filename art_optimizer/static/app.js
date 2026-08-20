(() => {
  "use strict";

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
    favoriteCurrent: document.querySelector("#favorite-current"),
    reroll: document.querySelector("#reroll"),
    newWorld: document.querySelector("#new-world"),
    historyToggle: document.querySelector("#history-toggle"),
    historyDrawer: document.querySelector("#history-drawer"),
    historyStrip: document.querySelector("#history-strip"),
    historyCount: document.querySelector("#history-count"),
    atlasLabel: document.querySelector("#atlas-label"),
    learningLabel: document.querySelector("#learning-label"),
    connectionLabel: document.querySelector("#connection-label"),
    worldLabel: document.querySelector("#world-label"),
    roundLabel: document.querySelector("#round-label"),
    toast: document.querySelector("#toast"),
  };

  const ui = {
    snapshot: null,
    sessionId: null,
    eventSource: null,
    previewCandidateId: null,
    exposedCandidateIds: new Set(),
    exposureTimers: new Map(),
    activeRoundId: null,
    busy: false,
    historyOpen: false,
    longPressTimer: null,
    suppressNextClick: false,
    reconnectTimer: null,
  };

  const roleLabels = {
    best_local: "local",
    diverse_posterior: "diverse",
    informative_probe: "probe",
    controlled_surprise: "surprise",
  };

  function api(path, options = {}) {
    return fetch(path, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...(options.headers || {}),
      },
    }).then(async (response) => {
      const body = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(body.detail || `Request failed (${response.status})`);
      }
      return body;
    });
  }

  function showToast(message) {
    elements.toast.textContent = message;
    elements.toast.classList.remove("hidden");
    window.clearTimeout(showToast.timer);
    showToast.timer = window.setTimeout(() => elements.toast.classList.add("hidden"), 2400);
  }

  function setBusy(value) {
    ui.busy = value;
    elements.reroll.disabled = value;
    elements.newWorld.disabled = value;
    elements.favoriteCurrent.disabled = value || !ui.snapshot;
  }

  function setConnection(status) {
    elements.connectionLabel.textContent = status;
    elements.connectionLabel.classList.toggle("online", status === "live");
    elements.connectionLabel.classList.toggle("offline", status === "offline");
  }

  async function startSession(prompt) {
    setBusy(true);
    const submit = elements.startForm.querySelector("button[type='submit']");
    submit.disabled = true;
    submit.textContent = "Building world…";
    try {
      const snapshot = await api("/api/sessions", {
        method: "POST",
        body: JSON.stringify({ prompt }),
      });
      ui.sessionId = snapshot.session_id;
      localStorage.setItem("artOptimizerSessionId", ui.sessionId);
      elements.startScreen.classList.add("hidden");
      elements.studio.classList.remove("hidden");
      applySnapshot(snapshot);
      connectStream();
    } catch (error) {
      showToast(error.message);
    } finally {
      setBusy(false);
      submit.disabled = false;
      submit.textContent = "Create world";
    }
  }

  async function resumeSession(sessionId) {
    try {
      const snapshot = await api(`/api/sessions/${sessionId}`);
      ui.sessionId = sessionId;
      elements.startScreen.classList.add("hidden");
      elements.studio.classList.remove("hidden");
      applySnapshot(snapshot);
      connectStream();
    } catch {
      localStorage.removeItem("artOptimizerSessionId");
    }
  }

  function connectStream() {
    if (!ui.sessionId) return;
    if (ui.eventSource) ui.eventSource.close();
    window.clearTimeout(ui.reconnectTimer);
    setConnection("connecting");
    const source = new EventSource(`/api/sessions/${ui.sessionId}/events`);
    ui.eventSource = source;

    source.addEventListener("open", () => setConnection("live"));
    source.addEventListener("session.snapshot", (event) => {
      applySnapshot(JSON.parse(event.data));
    });
    source.addEventListener("error", () => {
      setConnection("offline");
      source.close();
      ui.reconnectTimer = window.setTimeout(connectStream, 1400);
    });
  }

  function applySnapshot(snapshot) {
    ui.snapshot = snapshot;
    if (snapshot.active_round?.round_id !== ui.activeRoundId) {
      ui.activeRoundId = snapshot.active_round?.round_id || null;
      ui.exposedCandidateIds.clear();
      for (const timer of ui.exposureTimers.values()) window.clearTimeout(timer);
      ui.exposureTimers.clear();
      endPreview();
    }

    elements.currentImage.src = withVersion(snapshot.current_design.image_url, snapshot.version);
    elements.currentImage.dataset.designId = snapshot.current_design.design_id;
    elements.canvasLoader.classList.toggle("hidden", snapshot.status !== "generating" || Boolean(snapshot.current_design));
    elements.worldLabel.textContent = `world ${snapshot.world.world_id.slice(-6)}`;
    elements.learningLabel.textContent = `${snapshot.learner.observation_count} choices · radius ${snapshot.search.radius.toFixed(2)}`;
    elements.roundLabel.textContent = snapshot.active_round ? `ROUND ${snapshot.search.planner_step + 1}` : "";

    const isFavorite = snapshot.favorites.includes(snapshot.current_design.design_id);
    elements.favoriteCurrent.classList.toggle("active", isFavorite);
    elements.favoriteCurrent.textContent = isFavorite ? "★ Favorited" : "☆ Favorite current";
    elements.reroll.textContent = snapshot.search.consecutive_rerolls > 1 ? "↻ Go wilder" : "↻ Reroll";

    renderCandidates(snapshot.active_round?.candidates || []);
    renderHistory(snapshot.history || []);
    elements.historyCount.textContent = String(snapshot.history?.length || 0);
    elements.atlasLabel.textContent = `${snapshot.atlas.component_count} taste mode${snapshot.atlas.component_count === 1 ? "" : "s"} · ${snapshot.atlas.provisional_count} provisional`;
    setBusy(false);
  }

  function withVersion(url, version) {
    return `${url}${url.includes("?") ? "&" : "?"}v=${version}`;
  }

  function renderCandidates(candidates) {
    const existing = new Map(
      Array.from(elements.corners.querySelectorAll(".candidate-card")).map((card) => [card.dataset.candidateId, card]),
    );
    const fragment = document.createDocumentFragment();

    for (const candidate of candidates) {
      let card = existing.get(candidate.candidate_id);
      if (!card) card = buildCandidateCard(candidate);
      updateCandidateCard(card, candidate);
      fragment.appendChild(card);
      existing.delete(candidate.candidate_id);
    }
    elements.corners.replaceChildren(fragment);
  }

  function buildCandidateCard(candidate) {
    const card = document.createElement("div");
    card.className = "candidate-card loading";
    card.dataset.candidateId = candidate.candidate_id;
    card.dataset.slot = String(candidate.slot);
    card.tabIndex = 0;
    card.setAttribute("role", "button");
    card.setAttribute("aria-label", `Candidate ${candidate.slot}, ${roleLabels[candidate.role] || candidate.role}`);
    card.innerHTML = `
      <div class="candidate-skeleton"></div>
      <img class="candidate-image hidden" alt="Candidate ${candidate.slot}" draggable="false" />
      <span class="candidate-number">${candidate.slot}</span>
      <span class="candidate-role">${roleLabels[candidate.role] || candidate.role}</span>
      <button class="candidate-favorite" type="button" aria-label="Favorite candidate">☆</button>
    `;

    card.addEventListener("mouseenter", () => previewCandidate(candidate.candidate_id));
    card.addEventListener("mouseleave", () => endPreview(candidate.candidate_id));
    card.addEventListener("click", (event) => {
      if (event.target.closest(".candidate-favorite")) return;
      if (ui.suppressNextClick) {
        ui.suppressNextClick = false;
        return;
      }
      commitCandidate(candidate.candidate_id);
    });
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
    card.addEventListener("pointerdown", (event) => {
      if (event.pointerType === "mouse") return;
      window.clearTimeout(ui.longPressTimer);
      ui.longPressTimer = window.setTimeout(() => {
        ui.suppressNextClick = true;
        previewCandidate(candidate.candidate_id);
      }, 360);
    });
    const releaseTouch = (event) => {
      if (event.pointerType === "mouse") return;
      window.clearTimeout(ui.longPressTimer);
      if (ui.previewCandidateId === candidate.candidate_id) endPreview(candidate.candidate_id);
    };
    card.addEventListener("pointerup", releaseTouch);
    card.addEventListener("pointercancel", releaseTouch);

    const star = card.querySelector(".candidate-favorite");
    star.addEventListener("click", (event) => {
      event.stopPropagation();
      const current = getCandidate(candidate.candidate_id);
      if (!current?.design_id) return;
      toggleFavorite(current.design_id);
    });
    return card;
  }

  function updateCandidateCard(card, candidate) {
    card.dataset.candidateId = candidate.candidate_id;
    card.dataset.slot = String(candidate.slot);
    const image = card.querySelector(".candidate-image");
    const skeleton = card.querySelector(".candidate-skeleton");
    const star = card.querySelector(".candidate-favorite");
    const ready = candidate.status === "ready" && candidate.image_url;
    card.classList.toggle("loading", !ready);
    card.classList.toggle("previewing", ui.previewCandidateId === candidate.candidate_id);
    card.setAttribute("aria-disabled", ready ? "false" : "true");

    if (ready) {
      const src = withVersion(candidate.image_url, ui.snapshot.version);
      if (image.src !== new URL(src, location.href).href) image.src = src;
      image.classList.remove("hidden");
      skeleton.classList.add("hidden");
      image.onload = () => scheduleExposure(candidate.candidate_id, card);
    } else {
      image.classList.add("hidden");
      skeleton.classList.remove("hidden");
    }

    const favorited = candidate.design_id && ui.snapshot.favorites.includes(candidate.design_id);
    star.disabled = !ready;
    star.classList.toggle("active", Boolean(favorited));
    star.textContent = favorited ? "★" : "☆";
  }

  function getCandidate(candidateId) {
    return ui.snapshot?.active_round?.candidates.find((candidate) => candidate.candidate_id === candidateId) || null;
  }

  function previewCandidate(candidateId) {
    const candidate = getCandidate(candidateId);
    if (!candidate || candidate.status !== "ready" || !candidate.image_url) return;
    ui.previewCandidateId = candidateId;
    elements.previewImage.src = withVersion(candidate.image_url, ui.snapshot.version);
    elements.previewImage.classList.remove("hidden");
    elements.previewLabel.textContent = `PREVIEW ${candidate.slot} · ${roleLabels[candidate.role] || candidate.role}`;
    document.querySelectorAll(".candidate-card").forEach((card) => {
      card.classList.toggle("previewing", card.dataset.candidateId === candidateId);
    });
    markExposed(candidateId);
  }

  function endPreview(candidateId = null) {
    if (candidateId && ui.previewCandidateId !== candidateId) return;
    ui.previewCandidateId = null;
    elements.previewImage.classList.add("hidden");
    elements.previewImage.removeAttribute("src");
    elements.previewLabel.textContent = "CURRENT DESIGN";
    document.querySelectorAll(".candidate-card.previewing").forEach((card) => card.classList.remove("previewing"));
  }

  function scheduleExposure(candidateId, card) {
    if (ui.exposedCandidateIds.has(candidateId) || ui.exposureTimers.has(candidateId)) return;
    const timer = window.setTimeout(() => {
      ui.exposureTimers.delete(candidateId);
      const rect = card.getBoundingClientRect();
      const visibleWidth = Math.max(0, Math.min(rect.right, innerWidth) - Math.max(rect.left, 0));
      const visibleHeight = Math.max(0, Math.min(rect.bottom, innerHeight) - Math.max(rect.top, 0));
      const visibleFraction = (visibleWidth * visibleHeight) / Math.max(rect.width * rect.height, 1);
      if (document.visibilityState === "visible" && visibleFraction >= 0.5) markExposed(candidateId);
    }, 320);
    ui.exposureTimers.set(candidateId, timer);
  }

  function markExposed(candidateId) {
    ui.exposedCandidateIds.add(candidateId);
  }

  async function commitCandidate(candidateId) {
    const candidate = getCandidate(candidateId);
    if (!candidate || candidate.status !== "ready" || ui.busy) return;
    setBusy(true);
    endPreview();
    markExposed(candidateId);
    try {
      const snapshot = await api(
        `/api/sessions/${ui.sessionId}/candidates/${candidateId}/commit`,
        {
          method: "POST",
          body: JSON.stringify({
            exposed_candidate_ids: Array.from(ui.exposedCandidateIds),
            expected_version: ui.snapshot.version,
          }),
        },
      );
      applySnapshot(snapshot);
    } catch (error) {
      showToast(error.message);
      setBusy(false);
    }
  }

  async function reroll() {
    if (!ui.snapshot?.active_round || ui.busy) return;
    setBusy(true);
    endPreview();
    try {
      const snapshot = await api(`/api/sessions/${ui.sessionId}/reroll`, {
        method: "POST",
        body: JSON.stringify({ exposed_candidate_ids: Array.from(ui.exposedCandidateIds) }),
      });
      applySnapshot(snapshot);
      showToast(ui.exposedCandidateIds.size >= 2 ? "Kept the current design; searching wider" : "Round skipped; searching again");
    } catch (error) {
      showToast(error.message);
      setBusy(false);
    }
  }

  async function toggleFavorite(designId) {
    if (!designId || ui.busy) return;
    const favorite = !ui.snapshot.favorites.includes(designId);
    try {
      const snapshot = await api(`/api/sessions/${ui.sessionId}/designs/${designId}/favorite`, {
        method: "POST",
        body: JSON.stringify({ favorite }),
      });
      applySnapshot(snapshot);
      showToast(favorite ? "Added to persistent taste" : "Removed from favorites");
    } catch (error) {
      showToast(error.message);
    }
  }

  async function newWorld() {
    if (ui.busy) return;
    setBusy(true);
    endPreview();
    elements.canvasLoader.classList.remove("hidden");
    try {
      const snapshot = await api(`/api/sessions/${ui.sessionId}/new-world`, {
        method: "POST",
        body: "{}",
      });
      applySnapshot(snapshot);
      showToast("New stochastic world; persistent taste retained");
    } catch (error) {
      showToast(error.message);
      setBusy(false);
    }
  }

  function renderHistory(history) {
    const fragment = document.createDocumentFragment();
    for (const item of history) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = `history-item${item.current ? " current" : ""}`;
      button.innerHTML = `
        <img src="${withVersion(item.image_url, ui.snapshot.version)}" alt="Committed design in history" />
        ${item.favorite ? '<span class="history-marker">★</span>' : ""}
      `;
      button.addEventListener("click", () => restoreHistory(item.branch_node_id));
      fragment.appendChild(button);
    }
    elements.historyStrip.replaceChildren(fragment);
  }

  async function restoreHistory(branchNodeId) {
    if (ui.busy) return;
    setBusy(true);
    endPreview();
    try {
      const snapshot = await api(`/api/sessions/${ui.sessionId}/history/${branchNodeId}/restore`, {
        method: "POST",
        body: "{}",
      });
      applySnapshot(snapshot);
      showToast("Restored checkpoint; the next choice will fork from here");
    } catch (error) {
      showToast(error.message);
      setBusy(false);
    }
  }

  elements.startForm.addEventListener("submit", (event) => {
    event.preventDefault();
    const prompt = elements.prompt.value.trim() || "an evolving impossible garden";
    startSession(prompt);
  });

  elements.favoriteCurrent.addEventListener("click", () => {
    toggleFavorite(ui.snapshot?.current_design.design_id);
  });
  elements.reroll.addEventListener("click", reroll);
  elements.newWorld.addEventListener("click", newWorld);
  elements.historyToggle.addEventListener("click", () => {
    ui.historyOpen = !ui.historyOpen;
    elements.historyDrawer.classList.toggle("open", ui.historyOpen);
  });

  document.addEventListener("keydown", (event) => {
    const tag = event.target.tagName;
    if (tag === "INPUT" || tag === "TEXTAREA") return;
    if (!ui.snapshot) return;
    const number = Number(event.key);
    if (number >= 1 && number <= 4) {
      const candidate = ui.snapshot.active_round?.candidates.find((item) => item.slot === number);
      if (!candidate) return;
      event.preventDefault();
      if (event.shiftKey) previewCandidate(candidate.candidate_id);
      else commitCandidate(candidate.candidate_id);
      return;
    }
    if (event.key.toLowerCase() === "r") reroll();
    if (event.key.toLowerCase() === "f") toggleFavorite(ui.snapshot.current_design.design_id);
    if (event.key.toLowerCase() === "n") newWorld();
    if (event.key.toLowerCase() === "h") elements.historyToggle.click();
    if (event.key === "Escape") endPreview();
  });

  document.addEventListener("keyup", (event) => {
    if (event.shiftKey) return;
    if (["1", "2", "3", "4"].includes(event.key)) endPreview();
  });

  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState !== "visible") endPreview();
  });

  const remembered = localStorage.getItem("artOptimizerSessionId");
  if (remembered) resumeSession(remembered);
})();

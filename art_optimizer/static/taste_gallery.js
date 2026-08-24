import { formatRequestError } from "./experiment_core.js";

export function parseStrengths(value) {
  return String(value)
    .split(",")
    .map((item) => Number(item.trim()))
    .filter((item) => Number.isFinite(item));
}

export function tasteIdFromLabel(label) {
  const match = /^Taste\s+([A-Z])$/i.exec(String(label).trim());
  if (!match) return null;
  return `taste-${match[1].toUpperCase().charCodeAt(0) - 64}`;
}

export function orderedGalleryCells(gallery) {
  return [...(gallery?.cells || [])].sort(
    (left, right) => left.row - right.row || left.column - right.column,
  );
}

function boot() {
  const overlay = document.querySelector("#taste-gallery-overlay");
  if (!overlay) return;

  const elements = {
    overlay,
    panel: overlay.querySelector(".taste-gallery-panel"),
    title: document.querySelector("#taste-gallery-title"),
    subtitle: document.querySelector("#taste-gallery-subtitle"),
    close: document.querySelector("#taste-gallery-close"),
    rows: document.querySelector("#taste-gallery-rows"),
    strengths: document.querySelector("#taste-gallery-strengths"),
    regenerate: document.querySelector("#taste-gallery-regenerate"),
    loading: document.querySelector("#taste-gallery-loading"),
    grid: document.querySelector("#taste-gallery-grid"),
    selection: document.querySelector("#taste-gallery-selection"),
    activate: document.querySelector("#taste-gallery-activate"),
    tasteList: document.querySelector("#taste-list"),
  };

  const state = {
    tasteId: null,
    tasteLabel: null,
    gallery: null,
    selectedCell: null,
    seedNonce: 0,
    busy: false,
  };

  function requestId(prefix) {
    if (globalThis.crypto?.randomUUID) return `${prefix}_${globalThis.crypto.randomUUID()}`;
    return `${prefix}_${Date.now().toString(36)}_${Math.random().toString(36).slice(2)}`;
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

  function sessionId() {
    return localStorage.getItem("artOptimizerEmergentSessionId");
  }

  function setBusy(value) {
    state.busy = value;
    elements.loading.classList.toggle("hidden", !value);
    elements.regenerate.disabled = value;
    elements.rows.disabled = value;
    elements.strengths.disabled = value;
    elements.activate.disabled = value || !state.selectedCell;
    elements.grid.classList.toggle("busy", value);
  }

  function showError(error) {
    elements.selection.textContent = error.message || String(error);
    elements.selection.classList.add("error");
  }

  function openOverlay(tasteId, tasteLabel) {
    state.tasteId = tasteId;
    state.tasteLabel = tasteLabel;
    state.seedNonce = 0;
    state.gallery = null;
    state.selectedCell = null;
    elements.title.textContent = `${tasteLabel} gallery`;
    elements.subtitle.textContent =
      "Rows vary deterministic seeds. Columns scale this taste from the neutral action origin.";
    elements.selection.textContent = "Select a cell to inspect it.";
    elements.selection.classList.remove("error");
    elements.activate.disabled = true;
    elements.grid.replaceChildren();
    elements.overlay.classList.remove("hidden");
    document.body.classList.add("gallery-open");
    generateGallery();
  }

  function closeOverlay() {
    if (state.busy) return;
    elements.overlay.classList.add("hidden");
    document.body.classList.remove("gallery-open");
    state.gallery = null;
    state.selectedCell = null;
  }

  async function generateGallery() {
    const id = sessionId();
    if (!id || !state.tasteId || state.busy) return;
    setBusy(true);
    state.selectedCell = null;
    elements.activate.disabled = true;
    elements.grid.replaceChildren();
    elements.selection.textContent = "Rendering the gallery…";
    elements.selection.classList.remove("error");
    try {
      const snapshot = await api(`/api/emergent-tastes/sessions/${id}`);
      const gallery = await api(
        `/api/emergent-tastes/sessions/${id}/tastes/${state.tasteId}/gallery`,
        {
          method: "POST",
          body: JSON.stringify({
            request_id: requestId("gallery"),
            expected_mutation_version: snapshot.mutation_version,
            row_count: Number(elements.rows.value),
            strengths: parseStrengths(elements.strengths.value),
            seed_nonce: state.seedNonce,
          }),
        },
      );
      state.gallery = gallery;
      renderGallery(gallery);
      elements.selection.textContent =
        "Gallery inspection creates no votes. Select a cell to preview its seed and strength.";
    } catch (error) {
      showError(error);
    } finally {
      setBusy(false);
    }
  }

  function renderGallery(gallery) {
    const strengths = gallery.strengths || [];
    elements.grid.style.setProperty("--strength-columns", String(strengths.length));
    const fragment = document.createDocumentFragment();

    const corner = document.createElement("div");
    corner.className = "gallery-axis-corner";
    corner.innerHTML = "SEED ↓<br />STRENGTH →";
    fragment.appendChild(corner);

    strengths.forEach((strength) => {
      const header = document.createElement("div");
      header.className = "gallery-strength-header";
      header.textContent = `${Number(strength).toFixed(2)}×`;
      fragment.appendChild(header);
    });

    const cells = orderedGalleryCells(gallery);
    for (let row = 0; row < gallery.row_count; row += 1) {
      const seed = gallery.seeds[row];
      const rowLabel = document.createElement("div");
      rowLabel.className = "gallery-seed-label";
      rowLabel.innerHTML = `<span>seed ${row + 1}</span><code>${String(seed).slice(-9)}</code>`;
      fragment.appendChild(rowLabel);

      for (const cell of cells.filter((item) => item.row === row)) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "taste-gallery-cell";
        button.dataset.cellId = cell.cell_id;
        button.setAttribute(
          "aria-label",
          `Seed ${row + 1}, strength ${Number(cell.strength).toFixed(2)}`,
        );
        button.innerHTML = `
          <img src="${cell.image_url}" alt="${state.tasteLabel}, seed ${row + 1}, strength ${Number(cell.strength).toFixed(2)}" />
          <span class="gallery-cell-meta">${Number(cell.strength).toFixed(2)}×${cell.clipped ? " · clipped" : ""}</span>
        `;
        button.addEventListener("click", () => selectCell(cell, button));
        fragment.appendChild(button);
      }
    }
    elements.grid.replaceChildren(fragment);
  }

  function selectCell(cell, button) {
    state.selectedCell = cell;
    document.querySelectorAll(".taste-gallery-cell.selected").forEach((item) => {
      item.classList.remove("selected");
    });
    button.classList.add("selected");
    elements.selection.classList.remove("error");
    elements.selection.innerHTML = `
      <strong>${state.tasteLabel} · ${Number(cell.strength).toFixed(2)}×</strong>
      <span>seed ${cell.seed}${cell.clipped ? " · one or more action coordinates clipped" : ""}</span>
    `;
    elements.activate.disabled = state.busy;
  }

  async function activateSelected() {
    const id = sessionId();
    const gallery = state.gallery;
    const cell = state.selectedCell;
    if (!id || !gallery || !cell || state.busy) return;
    setBusy(true);
    elements.selection.textContent = "Starting a fresh fixed-root session from this cell…";
    try {
      const snapshot = await api(`/api/emergent-tastes/sessions/${id}`);
      const created = await api(
        `/api/emergent-tastes/sessions/${id}/galleries/${gallery.gallery_id}/cells/${cell.cell_id}/activate`,
        {
          method: "POST",
          body: JSON.stringify({
            request_id: requestId("gallery_activate"),
            expected_mutation_version: snapshot.mutation_version,
          }),
        },
      );
      localStorage.setItem("artOptimizerEmergentSessionId", created.session_id);
      location.reload();
    } catch (error) {
      showError(error);
      setBusy(false);
    }
  }

  function decorateTasteCards() {
    const cards = Array.from(elements.tasteList.querySelectorAll(".taste-card"));
    for (const card of cards) {
      const title = card.querySelector(".taste-card-title")?.textContent || "";
      const tasteId = tasteIdFromLabel(title);
      const hasComponent = Boolean(card.querySelector(".taste-resume"));
      if (!tasteId || !hasComponent) continue;
      card.dataset.tasteId = tasteId;
      card.classList.add("gallery-enabled");
      if (!card.querySelector(".taste-gallery-open")) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "taste-gallery-open";
        button.textContent = "Browse seed × strength gallery";
        button.addEventListener("click", (event) => {
          event.stopPropagation();
          openOverlay(tasteId, title.trim());
        });
        card.appendChild(button);
      }
      if (!card.dataset.galleryBound) {
        card.dataset.galleryBound = "true";
        card.addEventListener("click", (event) => {
          if (event.target.closest("button")) return;
          openOverlay(tasteId, title.trim());
        });
      }
    }
  }

  const observer = new MutationObserver(decorateTasteCards);
  observer.observe(elements.tasteList, { childList: true, subtree: true });
  decorateTasteCards();

  elements.close.addEventListener("click", closeOverlay);
  elements.regenerate.addEventListener("click", () => {
    state.seedNonce += 1;
    generateGallery();
  });
  elements.rows.addEventListener("change", generateGallery);
  elements.strengths.addEventListener("change", generateGallery);
  elements.activate.addEventListener("click", activateSelected);
  elements.overlay.addEventListener("click", (event) => {
    if (event.target === elements.overlay) closeOverlay();
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !elements.overlay.classList.contains("hidden")) {
      closeOverlay();
    }
  });
}

if (typeof document !== "undefined") boot();

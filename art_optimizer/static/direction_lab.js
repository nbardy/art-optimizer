import { formatRequestError } from "./experiment_core.js";

const STORAGE_KEY = "artOptimizerDirectionLab/v1";
export function nextPointSeed(seed) {
  let value = Number.isFinite(Number(seed)) ? Number(seed) >>> 0 : 0x9e3779b9;
  if (value === 0) value = 0x9e3779b9;
  value ^= value << 13;
  value ^= value >>> 17;
  value ^= value << 5;
  return value >>> 0;
}

export function appendCenterStep(path, step) {
  return [...(path || []), { ...step }];
}

export function popCenterStep(path) {
  return (path || []).slice(0, -1);
}

export function formatRms(value) {
  return `${Number(value || 0).toFixed(3)}×`;
}

function readState() {
  try {
    const parsed = JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
    return {
      prompt: parsed.prompt || "an evolving impossible garden",
      imageSeed: Number.isFinite(Number(parsed.imageSeed)) ? Number(parsed.imageSeed) : 424242,
      pointSeed: Number.isFinite(Number(parsed.pointSeed)) ? Number(parsed.pointSeed) : 1001,
      codecId: parsed.codecId || "orthogonal-shell",
      radius: Number.isFinite(Number(parsed.radius)) ? Number(parsed.radius) : 0.4,
      centerPath: Array.isArray(parsed.centerPath) ? parsed.centerPath : [],
      modelId: parsed.modelId || null,
    };
  } catch {
    return {
      prompt: "an evolving impossible garden",
      imageSeed: 424242,
      pointSeed: 1001,
      codecId: "orthogonal-shell",
      radius: 0.4,
      centerPath: [],
      modelId: null,
    };
  }
}

function boot() {
  const elements = {
    form: document.querySelector("#direction-form"),
    prompt: document.querySelector("#direction-prompt"),
    imageSeed: document.querySelector("#image-seed"),
    pointSeed: document.querySelector("#point-seed"),
    radius: document.querySelector("#direction-radius"),
    radiusOutput: document.querySelector("#radius-output"),
    codecList: document.querySelector("#codec-list"),
    generate: document.querySelector("#generate-slate"),
    explore: document.querySelector("#explore-selected"),
    newPoints: document.querySelector("#new-points"),
    stepBack: document.querySelector("#step-back"),
    reset: document.querySelector("#reset-center"),
    grid: document.querySelector("#direction-grid"),
    status: document.querySelector("#direction-status"),
    diagnostics: document.querySelector("#diagnostics"),
    cosine: document.querySelector("#cosine-matrix"),
    centerLabel: document.querySelector("#center-label"),
    walkPath: document.querySelector("#walk-path"),
    slateId: document.querySelector("#slate-id"),
    loading: document.querySelector("#direction-loading"),
    toast: document.querySelector("#direction-toast"),
    modelBadge: document.querySelector("#model-badge"),
  };

  const state = {
    ...readState(),
    codecs: [],
    slate: null,
    selectedCell: null,
    busy: false,
  };

  function saveState() {
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({
        prompt: state.prompt,
        imageSeed: state.imageSeed,
        pointSeed: state.pointSeed,
        codecId: state.codecId,
        radius: state.radius,
        centerPath: state.centerPath,
        modelId: state.modelId,
      }),
    );
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
      5200,
    );
  }

  function setBusy(value) {
    state.busy = value;
    elements.loading.classList.toggle("hidden", !value);
    elements.generate.disabled = value;
    elements.newPoints.disabled = value;
    elements.explore.disabled = value || !state.selectedCell;
    elements.stepBack.disabled = value || state.centerPath.length === 0;
    elements.reset.disabled = value || state.centerPath.length === 0;
  }

  function syncInputs() {
    elements.prompt.value = state.prompt;
    elements.imageSeed.value = String(state.imageSeed);
    elements.pointSeed.value = String(state.pointSeed);
    elements.radius.value = String(state.radius);
    elements.radiusOutput.textContent = `${state.radius.toFixed(2)}× base RMS`;
    elements.centerLabel.textContent =
      state.centerPath.length === 0
        ? "Prompt center"
        : `Selected embedding center · step ${state.centerPath.length}`;
    elements.walkPath.textContent = `depth ${state.centerPath.length}`;
    elements.stepBack.disabled = state.busy || state.centerPath.length === 0;
    elements.reset.disabled = state.busy || state.centerPath.length === 0;
  }

  function readInputs() {
    const prompt = elements.prompt.value.trim();
    const imageSeed = Math.max(0, Math.trunc(Number(elements.imageSeed.value)));
    if (state.centerPath.length && (prompt !== state.prompt || imageSeed !== state.imageSeed)) {
      state.centerPath = [];
      state.selectedCell = null;
      elements.status.textContent =
        "Prompt or diffusion seed changed, so the embedding walk was reset to its center.";
    }
    state.prompt = prompt;
    state.imageSeed = imageSeed;
    state.pointSeed = Math.max(0, Math.trunc(Number(elements.pointSeed.value)));
    state.radius = Number(elements.radius.value);
    state.codecId =
      document.querySelector("input[name='direction-codec']:checked")?.value ||
      state.codecId;
    saveState();
  }

  function renderCodecs() {
    const fragment = document.createDocumentFragment();
    for (const codec of state.codecs) {
      const label = document.createElement("label");
      label.className = "codec-option";
      const input = document.createElement("input");
      input.type = "radio";
      input.name = "direction-codec";
      input.value = codec.codec_id;
      input.checked = codec.codec_id === state.codecId;
      input.addEventListener("change", () => {
        state.codecId = codec.codec_id;
        state.radius = Number(codec.default_radius);
        syncInputs();
        saveState();
      });

      const card = document.createElement("span");
      card.className = "codec-card";
      const title = document.createElement("strong");
      title.textContent = codec.label;
      const description = document.createElement("span");
      description.textContent = codec.description;
      card.append(title, description);
      label.append(input, card);
      fragment.appendChild(label);
    }
    elements.codecList.replaceChildren(fragment);
  }

  function selectCell(cell, button) {
    state.selectedCell = cell;
    elements.grid.querySelectorAll(".direction-cell.selected").forEach((item) => {
      item.classList.remove("selected");
    });
    button.classList.add("selected");
    elements.explore.disabled = state.busy;
    elements.status.textContent =
      `Selected point ${cell.candidate_index + 1} at ${formatRms(
        cell.offset_rms_relative_to_base,
      )} from the original prompt embedding.`;
  }

  function renderSlate(slate) {
    const fragment = document.createDocumentFragment();
    for (const cell of slate.cells) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "direction-cell";
      button.dataset.candidateIndex = String(cell.candidate_index);
      button.innerHTML = `
        <img src="${cell.image_url}" alt="${slate.codec.label} candidate ${cell.candidate_index + 1}" />
        <span class="direction-cell-meta">
          <span class="direction-cell-index">POINT ${cell.candidate_index + 1}</span>
          <span>${formatRms(cell.offset_rms_relative_to_base)} from prompt</span>
        </span>
      `;
      button.addEventListener("click", () => selectCell(cell, button));
      button.addEventListener("dblclick", () => {
        selectCell(cell, button);
        exploreSelected();
      });
      fragment.appendChild(button);
    }
    elements.grid.replaceChildren(fragment);
  }

  function renderDiagnostics(slate) {
    const diagnostics = slate.diagnostics;
    const items = [
      ["center offset", formatRms(diagnostics.center_offset_rms_relative_to_base)],
      [
        "minimum pairwise separation",
        formatRms(diagnostics.minimum_pairwise_candidate_rms),
      ],
      ["direction effective rank", Number(diagnostics.direction_effective_rank).toFixed(2)],
      ["string axes", diagnostics.string_axes_used ? "yes" : "never"],
    ];
    const fragment = document.createDocumentFragment();
    for (const [label, value] of items) {
      const item = document.createElement("div");
      const name = document.createElement("span");
      name.textContent = label;
      const strong = document.createElement("strong");
      strong.textContent = value;
      item.append(name, strong);
      fragment.appendChild(item);
    }
    elements.diagnostics.replaceChildren(fragment);
    elements.cosine.textContent = diagnostics.direction_cosine_matrix
      .map((row) => row.map((value) => Number(value).toFixed(3)).join("  "))
      .join("\n");
    elements.slateId.textContent = slate.slate_id;
  }

  async function generateSlate() {
    if (state.busy) return;
    readInputs();
    state.selectedCell = null;
    setBusy(true);
    elements.status.classList.remove("error");
    elements.status.textContent =
      "Generating four points on the selected embedding shell…";
    try {
      const slate = await api("/api/direction-lab/slates", {
        method: "POST",
        body: JSON.stringify({
          prompt: state.prompt,
          image_seed: state.imageSeed,
          point_seed: state.pointSeed,
          codec_id: state.codecId,
          radius: state.radius,
          center_path: state.centerPath,
        }),
      });
      state.slate = slate;
      renderSlate(slate);
      renderDiagnostics(slate);
      elements.status.textContent =
        `${slate.codec.label}: same diffusion seed ${slate.image_seed}, ` +
        `four non-string points at radius ${Number(slate.radius).toFixed(2)}×.`;
      syncInputs();
      saveState();
    } catch (error) {
      elements.status.classList.add("error");
      elements.status.textContent = error.message;
      showToast(error.message);
    } finally {
      setBusy(false);
    }
  }

  async function exploreSelected() {
    if (!state.selectedCell || state.busy) return;
    state.centerPath = appendCenterStep(
      state.centerPath,
      state.selectedCell.step,
    );
    state.pointSeed = nextPointSeed(state.pointSeed);
    state.selectedCell = null;
    syncInputs();
    saveState();
    await generateSlate();
  }

  elements.form.addEventListener("submit", (event) => {
    event.preventDefault();
    generateSlate();
  });
  elements.radius.addEventListener("input", () => {
    state.radius = Number(elements.radius.value);
    elements.radiusOutput.textContent = `${state.radius.toFixed(2)}× base RMS`;
  });
  elements.newPoints.addEventListener("click", () => {
    state.pointSeed = nextPointSeed(state.pointSeed);
    syncInputs();
    saveState();
    generateSlate();
  });
  elements.explore.addEventListener("click", exploreSelected);
  elements.stepBack.addEventListener("click", () => {
    state.centerPath = popCenterStep(state.centerPath);
    state.selectedCell = null;
    syncInputs();
    saveState();
    generateSlate();
  });
  elements.reset.addEventListener("click", () => {
    state.centerPath = [];
    state.selectedCell = null;
    syncInputs();
    saveState();
    generateSlate();
  });

  Promise.all([api("/api/direction-codecs"), api("/healthz")])
    .then(([codecs, health]) => {
      state.codecs = codecs;
      if (!codecs.some((item) => item.codec_id === state.codecId)) {
        state.codecId = "orthogonal-shell";
      }
      renderCodecs();
      syncInputs();
      if (state.modelId && state.modelId !== health.model) {
        state.centerPath = [];
        state.selectedCell = null;
      }
      state.modelId = health.model;
      saveState();
      const supported =
        health.conditioning_mode === "embedding" &&
        health.model !== "procedural";
      elements.modelBadge.textContent = supported
        ? `${health.model} · embedding mode`
        : `${health.model} · Direction Lab needs FLUX/Krea embedding mode`;
      elements.modelBadge.classList.toggle("ready", supported);
      elements.modelBadge.classList.toggle("blocked", !supported);
    })
    .catch((error) => {
      showToast(error.message);
    });
}

if (typeof document !== "undefined") boot();

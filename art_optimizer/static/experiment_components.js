const ROLE_LABELS = {
  best_local: "local",
  diverse_posterior: "diverse",
  informative_probe: "probe",
  controlled_surprise: "surprise",
};

export function setImageSource(image, url) {
  if (!image || !url) return;
  const absolute = new URL(url, location.href).href;
  if (image.src !== absolute) image.src = url;
}

export function showToast(element, message, duration = 2400) {
  if (!element) return;
  element.textContent = message;
  element.classList.remove("hidden");
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => element.classList.add("hidden"), duration);
}

export async function mountExperimentSwitcher(element, activeId) {
  if (!element) return;
  const response = await fetch("/api/ui-experiments");
  const experiments = await response.json();
  element.replaceChildren(
    ...experiments.map((experiment) => {
      const link = document.createElement("a");
      link.href = `/ui/${experiment.experiment_id}`;
      link.textContent = experiment.label;
      link.title = experiment.description;
      link.className = experiment.experiment_id === activeId ? "active" : "";
      return link;
    }),
  );
}

export function createExposureTracker(studio) {
  const timers = new Map();
  const observer = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        const candidateId = entry.target.dataset.candidateId;
        if (!candidateId) continue;
        if (entry.isIntersecting && entry.intersectionRatio >= 0.5) {
          schedule(candidateId, entry.target);
        } else {
          cancel(candidateId);
        }
      }
    },
    { threshold: [0, 0.5, 1] },
  );

  function cancel(candidateId) {
    const timer = timers.get(candidateId);
    if (timer) clearTimeout(timer);
    timers.delete(candidateId);
  }

  function schedule(candidateId, element) {
    if (timers.has(candidateId)) return;
    const timer = setTimeout(() => {
      timers.delete(candidateId);
      const rect = element.getBoundingClientRect();
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
      if (document.visibilityState === "visible" && element.isConnected && fraction >= 0.5) {
        studio.markExposed(candidateId);
      }
    }, 320);
    timers.set(candidateId, timer);
  }

  return {
    observe(element) {
      observer.observe(element);
    },
    unobserve(element) {
      cancel(element.dataset.candidateId);
      observer.unobserve(element);
    },
    schedule,
    clear() {
      for (const timer of timers.values()) clearTimeout(timer);
      timers.clear();
      observer.disconnect();
    },
  };
}

export function createCandidateCard({
  candidate,
  studio,
  exposureTracker,
  favorites = [],
  showRole = false,
  laneLabel = null,
  onPreview,
  onPreviewEnd,
  onCommitted,
  onError,
}) {
  const card = document.createElement("article");
  card.className = "experiment-candidate";
  card.dataset.candidateId = candidate.candidate_id;
  card.dataset.slot = String(candidate.slot);
  card.tabIndex = candidate.status === "ready" ? 0 : -1;
  card.setAttribute("role", "button");
  card.setAttribute("aria-disabled", candidate.status === "ready" ? "false" : "true");

  const ready = candidate.status === "ready" && candidate.image_url;
  if (!ready) card.classList.add("loading");
  if (candidate.status === "failed") card.classList.add("failed");

  const image = document.createElement("img");
  image.alt = `Candidate ${candidate.slot}`;
  image.draggable = false;
  if (ready) {
    setImageSource(image, candidate.image_url);
    image.addEventListener("load", () => exposureTracker.schedule(candidate.candidate_id, card));
  }
  card.appendChild(image);

  if (!ready) {
    const skeleton = document.createElement("div");
    skeleton.className = "candidate-skeleton";
    card.appendChild(skeleton);
  }

  const badge = document.createElement("span");
  badge.className = "candidate-badge";
  badge.textContent = String(candidate.slot);
  card.appendChild(badge);

  if (showRole || laneLabel) {
    const role = document.createElement("span");
    role.className = "candidate-role-label";
    role.textContent = laneLabel || ROLE_LABELS[candidate.role] || candidate.role;
    card.appendChild(role);
  }

  const star = document.createElement("button");
  star.type = "button";
  star.className = "candidate-star";
  star.disabled = !ready;
  const favorited = candidate.design_id && favorites.includes(candidate.design_id);
  star.textContent = favorited ? "★" : "☆";
  star.classList.toggle("active", Boolean(favorited));
  star.setAttribute("aria-label", "Favorite candidate without committing it");
  star.addEventListener("click", async (event) => {
    event.stopPropagation();
    if (!candidate.design_id) return;
    studio.markExposed(candidate.candidate_id);
    try {
      await studio.favorite(candidate.design_id);
    } catch (error) {
      onError?.(error);
    }
  });
  card.appendChild(star);

  let held = false;
  let suppressClick = false;
  let holdTimer = null;
  let previewExposureTimer = null;
  const beginPreview = () => {
    if (!ready) return;
    clearTimeout(previewExposureTimer);
    previewExposureTimer = setTimeout(
      () => studio.markExposed(candidate.candidate_id),
      280,
    );
    onPreview?.(candidate);
  };
  const endPreview = () => {
    clearTimeout(previewExposureTimer);
    onPreviewEnd?.(candidate);
  };

  card.addEventListener("mouseenter", beginPreview);
  card.addEventListener("mouseleave", endPreview);
  card.addEventListener("focus", beginPreview);
  card.addEventListener("blur", endPreview);
  card.addEventListener("keydown", async (event) => {
    if (event.key === " ") {
      event.preventDefault();
      beginPreview();
    }
    if (event.key === "Enter" && ready) {
      event.preventDefault();
      try {
        await studio.commit(candidate.candidate_id);
        onCommitted?.(candidate);
      } catch (error) {
        onError?.(error);
      }
    }
  });
  card.addEventListener("keyup", (event) => {
    if (event.key === " ") endPreview();
  });
  card.addEventListener("pointerdown", (event) => {
    if (event.pointerType === "mouse" || event.target === star) return;
    clearTimeout(holdTimer);
    holdTimer = setTimeout(() => {
      held = true;
      suppressClick = true;
      beginPreview();
    }, 360);
  });
  const release = () => {
    clearTimeout(holdTimer);
    if (held) {
      held = false;
      endPreview();
      setTimeout(() => {
        suppressClick = false;
      }, 600);
    }
  };
  card.addEventListener("pointerup", release);
  card.addEventListener("pointercancel", (event) => {
    release(event);
    suppressClick = false;
  });
  card.addEventListener("click", async (event) => {
    if (event.target === star || held || !ready) return;
    if (suppressClick) {
      suppressClick = false;
      return;
    }
    try {
      await studio.commit(candidate.candidate_id);
      onCommitted?.(candidate);
    } catch (error) {
      onError?.(error);
    }
  });

  exposureTracker.observe(card);
  if (ready && image.complete && image.naturalWidth > 0) {
    exposureTracker.schedule(candidate.candidate_id, card);
  }
  return card;
}

export function renderConceptCards(container, state, studio, { compact = false } = {}) {
  if (!container) return;
  const cards = state.concepts.map((concept) => {
    const card = document.createElement("article");
    card.className = `concept-card${concept.effective ? " active" : ""}${compact ? " compact" : ""}`;
    card.dataset.conceptId = concept.conceptId;

    const preview = document.createElement("div");
    preview.className = "concept-preview";
    if (concept.exemplarImageUrl) {
      const image = document.createElement("img");
      image.src = concept.exemplarImageUrl;
      image.alt = `${concept.label} exemplar`;
      preview.appendChild(image);
    } else {
      preview.textContent = "↗";
    }
    card.appendChild(preview);

    const body = document.createElement("div");
    body.className = "concept-body";
    const title = document.createElement("strong");
    title.textContent = concept.label;
    body.appendChild(title);

    const meta = document.createElement("span");
    meta.textContent = `${concept.activation} · ${concept.support.toFixed(1)} yes / ${concept.opposition.toFixed(1)} no`;
    body.appendChild(meta);

    if (!compact) {
      const slider = document.createElement("input");
      slider.type = "range";
      slider.min = "0";
      slider.max = "1.5";
      slider.step = "0.05";
      slider.value = String(concept.strength);
      slider.setAttribute("aria-label", `${concept.label} amount`);
      slider.addEventListener("input", () => {
        studio.setConceptStrength(concept.conceptId, Number(slider.value));
      });
      body.appendChild(slider);
    }
    card.appendChild(body);

    const mode = document.createElement("button");
    mode.type = "button";
    mode.className = "concept-mode";
    mode.textContent = concept.activation === "auto" ? "AUTO" : concept.activation.toUpperCase();
    mode.title = "Cycle automatic, forced on, and forced off";
    mode.addEventListener("click", () => studio.cycleConceptActivation(concept.conceptId));
    card.appendChild(mode);
    return card;
  });

  if (!cards.length) {
    const empty = document.createElement("p");
    empty.className = "empty-concepts";
    empty.textContent = "Choose images to let reusable non-prompt directions emerge.";
    cards.push(empty);
  }
  container.replaceChildren(...cards);
}

export function renderHistory(container, history, studio, onError) {
  if (!container) return;
  container.replaceChildren(
    ...history.map((item) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = `history-thumb${item.current ? " current" : ""}`;
      const image = document.createElement("img");
      image.src = item.image_url;
      image.alt = "Committed design checkpoint";
      button.appendChild(image);
      if (item.favorite) {
        const marker = document.createElement("span");
        marker.textContent = "★";
        button.appendChild(marker);
      }
      button.addEventListener("click", async () => {
        try {
          await studio.restore(item.branch_node_id);
        } catch (error) {
          onError?.(error);
        }
      });
      return button;
    }),
  );
}

export function wireStartForm({ studio, form, prompt, startScreen, shell, onError }) {
  form?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const value = prompt.value.trim() || "an evolving impossible garden";
    try {
      await studio.start(value);
      startScreen?.classList.add("hidden");
      shell?.classList.remove("hidden");
    } catch (error) {
      onError?.(error);
    }
  });
}

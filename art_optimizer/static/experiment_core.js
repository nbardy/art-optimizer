const SESSION_KEY = "artOptimizerSessionId";
const CONCEPT_KEY = "artOptimizerConceptLibrary/v1";
const AUTO_THRESHOLD = 0.25;
const MAX_CONCEPTS = 12;

function clamp(value, minimum, maximum) {
  return Math.min(maximum, Math.max(minimum, value));
}

function vectorSubtract(left, right) {
  return left.map((value, index) => value - right[index]);
}

function vectorNorm(vector) {
  return Math.sqrt(vector.reduce((sum, value) => sum + value * value, 0));
}

function normalized(vector) {
  const length = vectorNorm(vector);
  if (length < 1e-9) return vector.map(() => 0);
  return vector.map((value) => value / length);
}

function dot(left, right) {
  return left.reduce((sum, value, index) => sum + value * right[index], 0);
}

function blendDirection(left, leftWeight, right, rightWeight) {
  return normalized(
    left.map((value, index) => value * leftWeight + right[index] * rightWeight),
  );
}

function makeId(prefix) {
  if (globalThis.crypto?.randomUUID) return `${prefix}_${globalThis.crypto.randomUUID()}`;
  return `${prefix}_${Date.now().toString(36)}_${Math.random().toString(36).slice(2)}`;
}

function readJSON(storage, key, fallback) {
  try {
    const raw = storage.getItem(key);
    return raw ? JSON.parse(raw) : fallback;
  } catch {
    return fallback;
  }
}

function writeJSON(storage, key, value) {
  try {
    storage.setItem(key, JSON.stringify(value));
  } catch {
    // Storage is a convenience for the experiment, never a blocker for image evolution.
  }
}

export class ConceptLibrary {
  constructor(storage = globalThis.localStorage) {
    this.storage = storage;
    this.state = readJSON(storage, CONCEPT_KEY, { version: 1, scopes: {} });
    if (!this.state || this.state.version !== 1 || typeof this.state.scopes !== "object") {
      this.state = { version: 1, scopes: {} };
    }
  }

  scopeFor(snapshot) {
    const basis = snapshot?.current_design?.control_basis_revision;
    const dimension = snapshot?.current_design?.action?.length;
    if (!basis || !dimension) return null;
    const current = this.state.scopes[basis];
    if (current?.dimension === dimension && Array.isArray(current.concepts)) return current;
    const scope = { dimension, nextLabel: 1, concepts: [] };
    this.state.scopes[basis] = scope;
    this.save();
    return scope;
  }

  save() {
    writeJSON(this.storage, CONCEPT_KEY, this.state);
  }

  effective(concept) {
    if (concept.activation === "on") return true;
    if (concept.activation === "off") return false;
    return concept.support - concept.opposition >= AUTO_THRESHOLD;
  }

  confidence(concept) {
    return concept.support / Math.max(concept.support + concept.opposition + 1, 1);
  }

  view(snapshot) {
    const scope = this.scopeFor(snapshot);
    if (!scope) return [];
    return scope.concepts
      .map((concept) => ({
        ...concept,
        effective: this.effective(concept),
        confidence: this.confidence(concept),
        netEvidence: concept.support - concept.opposition,
      }))
      .sort((left, right) => {
        if (left.effective !== right.effective) return left.effective ? -1 : 1;
        return right.netEvidence - left.netEvidence;
      });
  }

  observeCommit(snapshot, candidate) {
    const scope = this.scopeFor(snapshot);
    const anchor = snapshot?.current_design?.action;
    if (!scope || !candidate?.action || candidate.action.length !== anchor?.length) return false;
    const delta = vectorSubtract(candidate.action, anchor);
    const magnitude = vectorNorm(delta);
    if (magnitude < 0.06) return false;
    const direction = normalized(delta);

    let nearest = null;
    let nearestSimilarity = -1;
    for (const concept of scope.concepts) {
      const similarity = dot(direction, concept.direction);
      if (similarity > nearestSimilarity) {
        nearest = concept;
        nearestSimilarity = similarity;
      }
    }

    let acceptedConcept;
    if (nearest && nearestSimilarity >= 0.82) {
      nearest.direction = blendDirection(
        nearest.direction,
        nearest.support,
        direction,
        1,
      );
      nearest.magnitude = clamp(
        (nearest.magnitude * nearest.support + magnitude) / (nearest.support + 1),
        0.06,
        1.0,
      );
      nearest.support += 1;
      nearest.exemplarImageUrl = candidate.image_url || nearest.exemplarImageUrl;
      nearest.exemplarDesignId = candidate.design_id || nearest.exemplarDesignId;
      nearest.updatedAt = new Date().toISOString();
      acceptedConcept = nearest;
    } else {
      acceptedConcept = {
        conceptId: makeId("concept"),
        label: `Lane ${scope.nextLabel}`,
        direction,
        magnitude: clamp(magnitude, 0.06, 1.0),
        strength: 1,
        support: 1,
        opposition: 0,
        activation: "auto",
        exemplarImageUrl: candidate.image_url || null,
        exemplarDesignId: candidate.design_id || null,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      };
      scope.concepts.push(acceptedConcept);
      scope.nextLabel += 1;
    }

    for (const concept of scope.concepts) {
      if (concept === acceptedConcept) continue;
      const alignment = dot(direction, concept.direction);
      if (alignment < -0.6) concept.opposition += 0.08 * Math.abs(alignment);
    }

    scope.concepts.sort(
      (left, right) =>
        right.support - right.opposition - (left.support - left.opposition),
    );
    scope.concepts = scope.concepts.slice(0, MAX_CONCEPTS);
    this.save();
    return true;
  }

  observeReroll(snapshot, candidates) {
    const scope = this.scopeFor(snapshot);
    const anchor = snapshot?.current_design?.action;
    if (!scope || !anchor || candidates.length < 2) return false;
    const rejectedDirections = candidates
      .filter((candidate) => candidate?.action?.length === anchor.length)
      .map((candidate) => vectorSubtract(candidate.action, anchor))
      .filter((delta) => vectorNorm(delta) >= 0.06)
      .map(normalized);
    if (rejectedDirections.length < 2) return false;

    let changed = false;
    for (const concept of scope.concepts) {
      const alignment = Math.max(
        ...rejectedDirections.map((direction) => dot(direction, concept.direction)),
      );
      if (alignment >= 0.65) {
        concept.opposition += 0.2 * alignment;
        concept.updatedAt = new Date().toISOString();
        changed = true;
      }
    }
    if (changed) this.save();
    return changed;
  }

  setActivation(snapshot, conceptId, activation) {
    if (!["auto", "on", "off"].includes(activation)) return false;
    const concept = this.scopeFor(snapshot)?.concepts.find(
      (item) => item.conceptId === conceptId,
    );
    if (!concept) return false;
    concept.activation = activation;
    concept.updatedAt = new Date().toISOString();
    this.save();
    return true;
  }

  cycleActivation(snapshot, conceptId) {
    const concept = this.scopeFor(snapshot)?.concepts.find(
      (item) => item.conceptId === conceptId,
    );
    if (!concept) return false;
    const next = { auto: "on", on: "off", off: "auto" }[concept.activation] || "auto";
    return this.setActivation(snapshot, conceptId, next);
  }

  setStrength(snapshot, conceptId, strength) {
    const concept = this.scopeFor(snapshot)?.concepts.find(
      (item) => item.conceptId === conceptId,
    );
    if (!concept) return false;
    const value = Number(strength);
    if (!Number.isFinite(value)) return false;
    concept.strength = clamp(value, 0, 1.5);
    concept.updatedAt = new Date().toISOString();
    this.save();
    return true;
  }

  clearScope(snapshot) {
    const basis = snapshot?.current_design?.control_basis_revision;
    if (!basis || !this.state.scopes[basis]) return false;
    delete this.state.scopes[basis];
    this.save();
    return true;
  }

  composition(snapshot) {
    const concepts = this.view(snapshot).filter(
      (concept) => concept.effective && concept.strength > 1e-6,
    );
    const dimension = snapshot?.current_design?.action?.length || 0;
    if (!dimension) return [];
    if (!concepts.length) return Array(dimension).fill(0);
    const result = Array(dimension).fill(0);
    for (const concept of concepts) {
      const confidence = Math.max(0.35, concept.confidence);
      const coefficient = concept.strength * concept.magnitude * confidence;
      concept.direction.forEach((value, index) => {
        result[index] += value * coefficient;
      });
    }
    const normalization = Math.sqrt(concepts.length);
    return result.map((value) => clamp(value / normalization, -0.9, 0.9));
  }

  classifyCandidate(snapshot, candidate) {
    const anchor = snapshot?.current_design?.action;
    if (!anchor || candidate?.action?.length !== anchor.length) return "discovery";
    const delta = vectorSubtract(candidate.action, anchor);
    if (vectorNorm(delta) < 0.06) return "active";
    const direction = normalized(delta);
    const concepts = this.view(snapshot);
    const active = concepts.filter(
      (concept) => concept.effective && concept.strength > 0.05,
    );
    const inactive = concepts.filter(
      (concept) => !concept.effective || concept.strength <= 0.05,
    );
    const maxAlignment = (items) =>
      items.length ? Math.max(...items.map((item) => dot(direction, item.direction))) : -1;
    if (maxAlignment(active) >= 0.45) return "active";
    if (maxAlignment(inactive) >= 0.45) return "alternate";
    return "discovery";
  }
}

async function requestJSON(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(body.detail || `Request failed (${response.status})`);
    error.status = response.status;
    throw error;
  }
  return body;
}

export function createStudioController({ storage = globalThis.localStorage } = {}) {
  const conceptLibrary = new ConceptLibrary(storage);
  const listeners = new Set();
  const state = {
    snapshot: null,
    sessionId: null,
    eventSource: null,
    reconnectTimer: null,
    busy: false,
    connection: "offline",
    exposedCandidateIds: new Set(),
    activeRoundId: null,
    error: null,
  };

  function current() {
    return {
      snapshot: state.snapshot,
      sessionId: state.sessionId,
      busy: state.busy,
      connection: state.connection,
      error: state.error,
      concepts: conceptLibrary.view(state.snapshot),
      compositionAction: conceptLibrary.composition(state.snapshot),
      exposedCandidateIds: new Set(state.exposedCandidateIds),
    };
  }

  function emit() {
    const value = current();
    for (const listener of listeners) listener(value);
  }

  function subscribe(listener) {
    listeners.add(listener);
    listener(current());
    return () => listeners.delete(listener);
  }

  function setBusy(value) {
    state.busy = value;
    emit();
  }

  function setConnection(value) {
    state.connection = value;
    emit();
  }

  function applySnapshot(snapshot) {
    if (!snapshot?.session_id) return false;
    if (state.sessionId && snapshot.session_id !== state.sessionId) return false;
    if (state.snapshot && snapshot.version < state.snapshot.version) return false;
    state.sessionId = snapshot.session_id;
    if (snapshot.active_round?.round_id !== state.activeRoundId) {
      state.activeRoundId = snapshot.active_round?.round_id || null;
      state.exposedCandidateIds.clear();
    }
    state.snapshot = snapshot;
    state.error = null;
    conceptLibrary.scopeFor(snapshot);
    emit();
    return true;
  }

  async function recoverConflict(error) {
    if (error.status !== 409 || !state.sessionId) return;
    applySnapshot(await requestJSON(`/api/sessions/${state.sessionId}`));
  }

  function connectStream() {
    if (!state.sessionId) return;
    state.eventSource?.close();
    clearTimeout(state.reconnectTimer);
    setConnection("connecting");
    const source = new EventSource(`/api/sessions/${state.sessionId}/events`);
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
      source.close();
      setConnection("offline");
      state.reconnectTimer = setTimeout(connectStream, 1400);
    });
  }

  async function start(prompt) {
    if (state.busy) return null;
    setBusy(true);
    try {
      const snapshot = await requestJSON("/api/sessions", {
        method: "POST",
        body: JSON.stringify({ prompt }),
      });
      state.sessionId = snapshot.session_id;
      storage.setItem(SESSION_KEY, state.sessionId);
      applySnapshot(snapshot);
      connectStream();
      return snapshot;
    } catch (error) {
      state.error = error.message;
      emit();
      throw error;
    } finally {
      setBusy(false);
    }
  }

  async function resume(sessionId = storage.getItem(SESSION_KEY)) {
    if (!sessionId) return null;
    try {
      const snapshot = await requestJSON(`/api/sessions/${sessionId}`);
      state.sessionId = sessionId;
      applySnapshot(snapshot);
      connectStream();
      return snapshot;
    } catch (error) {
      if (error.status === 404) storage.removeItem(SESSION_KEY);
      state.error = error.message || "Could not resume the saved session";
      emit();
      return null;
    }
  }

  function commandPayload(extra = {}) {
    return {
      request_id: makeId("command"),
      expected_mutation_version: state.snapshot?.mutation_version ?? null,
      ...extra,
    };
  }

  function markExposed(candidateId) {
    if (!candidateId) return;
    state.exposedCandidateIds.add(candidateId);
  }

  function candidate(candidateId) {
    return (
      state.snapshot?.active_round?.candidates?.find(
        (item) => item.candidate_id === candidateId,
      ) || null
    );
  }

  async function commit(candidateId) {
    const chosen = candidate(candidateId);
    const before = state.snapshot;
    if (!chosen || chosen.status !== "ready" || state.busy) return null;
    markExposed(candidateId);
    setBusy(true);
    try {
      const snapshot = await requestJSON(
        `/api/sessions/${state.sessionId}/candidates/${candidateId}/commit`,
        {
          method: "POST",
          body: JSON.stringify(
            commandPayload({
              exposed_candidate_ids: Array.from(state.exposedCandidateIds),
            }),
          ),
        },
      );
      conceptLibrary.observeCommit(before, chosen);
      applySnapshot(snapshot);
      return snapshot;
    } catch (error) {
      await recoverConflict(error);
      state.error = error.message;
      emit();
      throw error;
    } finally {
      setBusy(false);
    }
  }

  async function reroll() {
    const before = state.snapshot;
    if (!before?.active_round || state.busy) return null;
    const exposedIds = Array.from(state.exposedCandidateIds);
    const exposedCandidates = before.active_round.candidates.filter((item) =>
      state.exposedCandidateIds.has(item.candidate_id),
    );
    setBusy(true);
    try {
      const snapshot = await requestJSON(`/api/sessions/${state.sessionId}/reroll`, {
        method: "POST",
        body: JSON.stringify(
          commandPayload({ exposed_candidate_ids: exposedIds }),
        ),
      });
      if (exposedCandidates.length >= 2) {
        conceptLibrary.observeReroll(before, exposedCandidates);
      }
      applySnapshot(snapshot);
      return { snapshot, exposureCount: exposedCandidates.length };
    } catch (error) {
      await recoverConflict(error);
      state.error = error.message;
      emit();
      throw error;
    } finally {
      setBusy(false);
    }
  }

  async function favorite(designId) {
    if (!designId || !state.snapshot || state.busy) return null;
    const value = !state.snapshot.favorites.includes(designId);
    setBusy(true);
    try {
      const snapshot = await requestJSON(
        `/api/sessions/${state.sessionId}/designs/${designId}/favorite`,
        {
          method: "POST",
          body: JSON.stringify(commandPayload({ favorite: value })),
        },
      );
      applySnapshot(snapshot);
      return { snapshot, favorite: value };
    } catch (error) {
      state.error = error.message;
      emit();
      throw error;
    } finally {
      setBusy(false);
    }
  }

  async function newWorld(mode = "taste_guided") {
    if (!state.snapshot || state.busy) return null;
    const targetAction = mode === "composition" ? conceptLibrary.composition(state.snapshot) : null;
    setBusy(true);
    try {
      const snapshot = await requestJSON(`/api/sessions/${state.sessionId}/new-world`, {
        method: "POST",
        body: JSON.stringify(
          commandPayload({
            mode,
            ...(targetAction ? { target_action: targetAction } : {}),
          }),
        ),
      });
      applySnapshot(snapshot);
      return snapshot;
    } catch (error) {
      await recoverConflict(error);
      state.error = error.message;
      emit();
      throw error;
    } finally {
      setBusy(false);
    }
  }

  async function restore(branchNodeId) {
    if (!branchNodeId || state.busy) return null;
    setBusy(true);
    try {
      const snapshot = await requestJSON(
        `/api/sessions/${state.sessionId}/history/${branchNodeId}/restore`,
        {
          method: "POST",
          body: JSON.stringify(commandPayload()),
        },
      );
      applySnapshot(snapshot);
      return snapshot;
    } catch (error) {
      await recoverConflict(error);
      state.error = error.message;
      emit();
      throw error;
    } finally {
      setBusy(false);
    }
  }

  function setConceptActivation(conceptId, activation) {
    const changed = conceptLibrary.setActivation(state.snapshot, conceptId, activation);
    if (changed) emit();
    return changed;
  }

  function cycleConceptActivation(conceptId) {
    const changed = conceptLibrary.cycleActivation(state.snapshot, conceptId);
    if (changed) emit();
    return changed;
  }

  function setConceptStrength(conceptId, strength) {
    const changed = conceptLibrary.setStrength(state.snapshot, conceptId, strength);
    if (changed) emit();
    return changed;
  }

  function clearConcepts() {
    const changed = conceptLibrary.clearScope(state.snapshot);
    if (changed) emit();
    return changed;
  }

  function close() {
    clearTimeout(state.reconnectTimer);
    state.eventSource?.close();
  }

  return {
    subscribe,
    current,
    applySnapshot,
    start,
    resume,
    connectStream,
    markExposed,
    candidate,
    commit,
    reroll,
    favorite,
    newWorld,
    restore,
    setConceptActivation,
    cycleConceptActivation,
    setConceptStrength,
    clearConcepts,
    classifyCandidate: (candidateValue) =>
      conceptLibrary.classifyCandidate(state.snapshot, candidateValue),
    close,
  };
}

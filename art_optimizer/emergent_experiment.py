from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from typing import Any, AsyncIterator

from .domain import (
    CommitPayload,
    CreateSessionRequest,
    ExposurePayload,
    RestorePayload,
    utc_now,
)
from .emergent_taste import (
    EmergentTasteEngine,
    TasteAlternative,
    TasteChoiceObservation,
    TasteDesignRef,
    TasteEngineState,
    deterministic_observation_id,
)
from .service import ArtOptimizerService, ConflictError, NotFoundError


TREATMENT_ID = "emergent-tastes"
CHOICE_EVENT_KIND = "emergent_taste_choice_recorded"
EXPLORE_EVENT_KIND = "emergent_taste_explored"


@dataclass(slots=True)
class _ProjectionCache:
    event_cursor: int
    dimension: int
    observations: list[TasteChoiceObservation]
    engine: EmergentTasteEngine
    state: TasteEngineState


@dataclass(slots=True)
class EmergentTasteExperiment:
    """Isolated UI/taste projection over the stable T0 generation loop.

    Candidate generation remains fixed-seed embedding/action search. This wrapper
    changes command vocabulary and adds one replayable taste inference projection;
    it does not mutate the legacy atlas or browser ConceptLibrary.
    """

    service: ArtOptimizerService
    _cache: dict[str, _ProjectionCache] = field(default_factory=dict)
    _locks: dict[str, asyncio.Lock] = field(default_factory=dict)

    async def create_session(self, request: CreateSessionRequest) -> dict[str, Any]:
        snapshot = await self.service.create_session(request)
        return await self._augment(snapshot)

    async def get_snapshot(self, session_id: str) -> dict[str, Any]:
        snapshot = await self.service.get_snapshot(session_id)
        return await self._augment(snapshot)

    async def stream(self, session_id: str) -> AsyncIterator[str]:
        async for chunk in self.service.stream(session_id):
            if chunk.startswith(":"):
                yield chunk
                continue
            event_name = "session.snapshot"
            event_id = "0"
            data: dict[str, Any] | None = None
            for line in chunk.splitlines():
                if line.startswith("id: "):
                    event_id = line.removeprefix("id: ")
                elif line.startswith("event: "):
                    event_name = line.removeprefix("event: ")
                elif line.startswith("data: "):
                    data = json.loads(line.removeprefix("data: "))
            if data is None:
                yield chunk
                continue
            payload = await self._augment(data)
            yield (
                f"id: {event_id}\n"
                f"event: {event_name}\n"
                f"data: {json.dumps(payload, separators=(',', ':'))}\n\n"
            )

    async def commit_candidate(
        self,
        session_id: str,
        candidate_id: str,
        payload: CommitPayload,
    ) -> dict[str, Any]:
        async with self._lock_for(session_id):
            observation_id = deterministic_observation_id(session_id, payload.request_id)
            cache = await self._load_cache_for_session(session_id)
            if any(item.observation_id == observation_id for item in cache.observations):
                result = await self.service.commit_candidate(
                    session_id,
                    candidate_id,
                    payload,
                )
                return await self._augment(result)

            before = await self.service.get_snapshot(session_id)
            draft = self._build_observation(
                before,
                payload,
                chosen_candidate_id=candidate_id,
                observation_weight=1.0,
            )
            receipts = cache.engine.predictive_receipts(cache.state, draft)
            draft = draft.model_copy(update={"prediction_receipts": receipts})

            result = await self.service.commit_candidate(
                session_id,
                candidate_id,
                payload,
            )
            observation = draft.model_copy(
                update={"result_branch_node_id": result["current_branch_node_id"]}
            )
            cache = await self._append_observation(session_id, cache, observation)
            return self._augment_with_cache(result, cache)

    async def none_of_these(
        self,
        session_id: str,
        payload: ExposurePayload,
    ) -> dict[str, Any]:
        async with self._lock_for(session_id):
            observation_id = deterministic_observation_id(session_id, payload.request_id)
            cache = await self._load_cache_for_session(session_id)
            if any(item.observation_id == observation_id for item in cache.observations):
                result = await self.service.reroll(session_id, payload)
                return await self._augment(result)

            before = await self.service.get_snapshot(session_id)
            draft = self._build_observation(
                before,
                payload,
                chosen_candidate_id=None,
                observation_weight=0.35,
            )
            # Match the underlying qualified anchor update: one exposed candidate is
            # a skipped round, not evidence that a taste rejected a meaningful slate.
            qualified = len(draft.alternatives) >= 2
            if qualified:
                receipts = cache.engine.predictive_receipts(cache.state, draft)
                draft = draft.model_copy(update={"prediction_receipts": receipts})

            result = await self.service.reroll(session_id, payload)
            if qualified:
                observation = draft.model_copy(
                    update={"result_branch_node_id": result["current_branch_node_id"]}
                )
                cache = await self._append_observation(session_id, cache, observation)
            return self._augment_with_cache(result, cache)

    async def explore(
        self,
        session_id: str,
        payload: ExposurePayload,
    ) -> dict[str, Any]:
        """Request wider embedding variation with no preference observation."""

        async with self._lock_for(session_id):
            before = await self.service.get_snapshot(session_id)
            neutral = ExposurePayload(
                request_id=payload.request_id,
                expected_mutation_version=payload.expected_mutation_version,
                expected_version=payload.expected_version,
                exposed_candidate_ids=[],
            )
            result = await self.service.reroll(session_id, neutral)
            if not self._has_request_event(
                session_id,
                EXPLORE_EVENT_KIND,
                payload.request_id,
            ):
                self.service.store.append_event(
                    session_id,
                    EXPLORE_EVENT_KIND,
                    {
                        "request_id": payload.request_id,
                        "round_id": (before.get("active_round") or {}).get("round_id"),
                        "seed": before["world"]["seed"],
                        "preference_effect": "none",
                        "variance_effect": "wider embedding/action proposals",
                    },
                )
            return await self._augment(result)

    async def restore(
        self,
        session_id: str,
        branch_node_id: str,
        payload: RestorePayload,
    ) -> dict[str, Any]:
        result = await self.service.restore(session_id, branch_node_id, payload)
        return await self._augment(result)

    async def _append_observation(
        self,
        session_id: str,
        cache: _ProjectionCache,
        observation: TasteChoiceObservation,
    ) -> _ProjectionCache:
        observations = [*cache.observations, observation]
        state = await asyncio.to_thread(cache.engine.fit_state, observations)
        event_id = self.service.store.append_event(
            session_id,
            CHOICE_EVENT_KIND,
            observation.model_dump(mode="json"),
        )
        updated = _ProjectionCache(
            event_cursor=event_id,
            dimension=cache.dimension,
            observations=observations,
            engine=cache.engine,
            state=state,
        )
        self._cache[session_id] = updated
        return updated

    async def _augment(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        cache = await self._load_cache(
            snapshot["session_id"],
            len(snapshot["current_design"]["action"]),
        )
        return self._augment_with_cache(snapshot, cache)

    def _augment_with_cache(
        self,
        snapshot: dict[str, Any],
        cache: _ProjectionCache,
    ) -> dict[str, Any]:
        payload = dict(snapshot)
        payload["treatment"] = {
            "treatment_id": TREATMENT_ID,
            "label": "Emergent tastes",
            "candidate_policy": "T0 fixed-root embedding/action search",
            "seed_policy": "fixed within the world",
            "taste_policy": cache.engine.revision,
            "planner_authority": "legacy T0 learner held constant for ablation",
        }
        payload["emergent_tastes"] = cache.engine.public_view(cache.state)
        return payload

    async def _load_cache_for_session(self, session_id: str) -> _ProjectionCache:
        snapshot = await self.service.get_snapshot(session_id)
        return await self._load_cache(
            session_id,
            len(snapshot["current_design"]["action"]),
        )

    async def _load_cache(
        self,
        session_id: str,
        dimension: int,
    ) -> _ProjectionCache:
        events = self.service.store.list_events(session_id)
        taste_events = [item for item in events if item["kind"] == CHOICE_EVENT_KIND]
        event_cursor = int(taste_events[-1]["event_id"]) if taste_events else 0
        cached = self._cache.get(session_id)
        if (
            cached is not None
            and cached.event_cursor == event_cursor
            and cached.dimension == dimension
        ):
            return cached
        observations = [
            TasteChoiceObservation.model_validate(item["payload"])
            for item in taste_events
        ]
        engine = EmergentTasteEngine(dimension)
        state = await asyncio.to_thread(engine.fit_state, observations)
        cache = _ProjectionCache(
            event_cursor=event_cursor,
            dimension=dimension,
            observations=observations,
            engine=engine,
            state=state,
        )
        self._cache[session_id] = cache
        return cache

    def _build_observation(
        self,
        snapshot: dict[str, Any],
        payload: ExposurePayload,
        *,
        chosen_candidate_id: str | None,
        observation_weight: float,
    ) -> TasteChoiceObservation:
        round_state = snapshot.get("active_round")
        if round_state is None or round_state.get("status") in {"closed", "cancelled"}:
            raise ConflictError("there is no active round")
        exposed = set(payload.exposed_candidate_ids)
        if chosen_candidate_id is not None:
            exposed.add(chosen_candidate_id)
        alternatives = [
            candidate
            for candidate in round_state["candidates"]
            if candidate["status"] == "ready"
            and candidate["candidate_id"] in exposed
        ]
        alternatives.sort(key=lambda item: int(item["slot"]))
        if not alternatives:
            raise ConflictError("no ready candidates were meaningfully exposed")
        chosen_index = 0
        if chosen_candidate_id is not None:
            matches = [
                index
                for index, candidate in enumerate(alternatives, start=1)
                if candidate["candidate_id"] == chosen_candidate_id
            ]
            if len(matches) != 1:
                raise NotFoundError("chosen candidate is not a ready exposed alternative")
            chosen_index = matches[0]

        current = snapshot["current_design"]
        branch_node_id = snapshot["current_branch_node_id"]
        return TasteChoiceObservation(
            observation_id=deterministic_observation_id(
                snapshot["session_id"],
                payload.request_id,
            ),
            request_id=payload.request_id,
            round_id=round_state["round_id"],
            seed=int(snapshot["world"]["seed"]),
            control_basis_revision=current["control_basis_revision"],
            anchor=TasteDesignRef(
                design_id=current["design_id"],
                action=current["action"],
                image_url=current["image_url"],
                branch_node_id=branch_node_id,
            ),
            alternatives=[
                TasteAlternative(
                    candidate_id=item["candidate_id"],
                    slot=int(item["slot"]),
                    design_id=item["design_id"],
                    action=item["action"],
                    image_url=item["image_url"],
                )
                for item in alternatives
            ],
            winner_index=chosen_index,
            result_branch_node_id=branch_node_id,
            created_at=utc_now(),
            observation_weight=observation_weight,
        )

    def _lock_for(self, session_id: str) -> asyncio.Lock:
        lock = self._locks.get(session_id)
        if lock is None:
            lock = asyncio.Lock()
            self._locks[session_id] = lock
        return lock

    def _has_request_event(
        self,
        session_id: str,
        kind: str,
        request_id: str,
    ) -> bool:
        return any(
            event["kind"] == kind and event["payload"].get("request_id") == request_id
            for event in self.service.store.list_events(session_id)
        )

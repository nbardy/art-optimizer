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
)
from .emergent_facts import (
    append_pending,
    build_observation,
    finalize_observation,
    has_observation,
    load_observations,
    recover_pending,
    validate_command_identity,
)
from .emergent_taste import (
    EmergentTasteEngine,
    TasteChoiceObservation,
    TasteEngineState,
    deterministic_observation_id,
)
from .service import ArtOptimizerService, ConflictError


TREATMENT_ID = "emergent-tastes"
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
    """Fixed-root interaction plus one recoverable preference-mode projection."""

    service: ArtOptimizerService
    _cache: dict[str, _ProjectionCache] = field(default_factory=dict)
    _locks: dict[str, asyncio.Lock] = field(default_factory=dict)

    async def create_session(self, request: CreateSessionRequest) -> dict[str, Any]:
        return await self._augment(await self.service.create_session(request))

    async def get_snapshot(self, session_id: str) -> dict[str, Any]:
        recover_pending(self.service, session_id)
        return await self._augment(await self.service.get_snapshot(session_id))

    async def stream(self, session_id: str) -> AsyncIterator[str]:
        recover_pending(self.service, session_id)
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
            recover_pending(self.service, session_id)
            observation_id = deterministic_observation_id(session_id, payload.request_id)
            validate_command_identity(
                self.service,
                session_id,
                observation_id=observation_id,
                command_kind="commit_candidate",
                candidate_id=candidate_id,
            )
            if has_observation(self.service, session_id, observation_id):
                return await self.get_snapshot(session_id)

            before = await self.service.get_snapshot(session_id)
            cache = await self._load_cache(
                session_id,
                len(before["current_design"]["action"]),
            )
            draft = build_observation(
                before,
                payload,
                chosen_candidate_id=candidate_id,
                observation_weight=1.0,
            )
            draft = draft.model_copy(
                update={
                    "prediction_receipts": cache.engine.predictive_receipts(
                        cache.state,
                        draft,
                    )
                }
            )
            append_pending(
                self.service,
                session_id,
                command_kind="commit_candidate",
                candidate_id=candidate_id,
                observation=draft,
            )
            try:
                result = await self.service.commit_candidate(
                    session_id,
                    candidate_id,
                    payload,
                )
            except ConflictError:
                recover_pending(self.service, session_id)
                if has_observation(self.service, session_id, observation_id):
                    return await self.get_snapshot(session_id)
                raise
            finalize_observation(
                self.service,
                session_id,
                draft.model_copy(
                    update={"result_branch_node_id": result["current_branch_node_id"]}
                ),
            )
            self._cache.pop(session_id, None)
            return await self._augment(result)

    async def none_of_these(
        self,
        session_id: str,
        payload: ExposurePayload,
    ) -> dict[str, Any]:
        async with self._lock_for(session_id):
            recover_pending(self.service, session_id)
            observation_id = deterministic_observation_id(session_id, payload.request_id)
            validate_command_identity(
                self.service,
                session_id,
                observation_id=observation_id,
                command_kind="none_of_these",
                candidate_id=None,
            )
            if has_observation(self.service, session_id, observation_id):
                return await self.get_snapshot(session_id)

            before = await self.service.get_snapshot(session_id)
            cache = await self._load_cache(
                session_id,
                len(before["current_design"]["action"]),
            )
            draft = build_observation(
                before,
                payload,
                chosen_candidate_id=None,
                observation_weight=0.35,
            )
            qualified = len(draft.alternatives) >= 2
            if qualified:
                draft = draft.model_copy(
                    update={
                        "prediction_receipts": cache.engine.predictive_receipts(
                            cache.state,
                            draft,
                        )
                    }
                )
                append_pending(
                    self.service,
                    session_id,
                    command_kind="none_of_these",
                    candidate_id=None,
                    observation=draft,
                )
            try:
                result = await self.service.reroll(session_id, payload)
            except ConflictError:
                recover_pending(self.service, session_id)
                if qualified and has_observation(self.service, session_id, observation_id):
                    return await self.get_snapshot(session_id)
                raise
            if qualified:
                finalize_observation(
                    self.service,
                    session_id,
                    draft.model_copy(
                        update={"result_branch_node_id": result["current_branch_node_id"]}
                    ),
                )
                self._cache.pop(session_id, None)
            return await self._augment(result)

    async def explore(
        self,
        session_id: str,
        payload: ExposurePayload,
    ) -> dict[str, Any]:
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
        async with self._lock_for(session_id):
            return await self._augment(
                await self.service.restore(session_id, branch_node_id, payload)
            )

    async def _augment(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        recover_pending(self.service, snapshot["session_id"])
        cache = await self._load_cache(
            snapshot["session_id"],
            len(snapshot["current_design"]["action"]),
        )
        payload = dict(snapshot)
        payload["treatment"] = {
            "treatment_id": TREATMENT_ID,
            "label": "Emergent tastes",
            "candidate_policy": "T0 fixed-root embedding/action search",
            "seed_policy": "fixed within the world",
            "taste_policy": cache.engine.revision,
            "planner_authority": "legacy T0 learner held constant for ablation",
        }
        taste_view = cache.engine.public_view(cache.state)
        anchor_observations = {
            item.observation_id
            for item in cache.observations
            if item.winner_index == 0
        }
        for component in taste_view["components"]:
            component["exemplars"] = [
                item
                for item in component["exemplars"]
                if item["observation_id"] not in anchor_observations
            ]
            component["latest_branch_node_id"] = (
                component["exemplars"][-1]["branch_node_id"]
                if component["exemplars"]
                else None
            )
        payload["emergent_tastes"] = taste_view
        return payload

    async def _load_cache_for_session(self, session_id: str) -> _ProjectionCache:
        snapshot = await self.service.get_snapshot(session_id)
        return await self._load_cache(
            session_id,
            len(snapshot["current_design"]["action"]),
        )

    async def _load_cache(self, session_id: str, dimension: int) -> _ProjectionCache:
        cursor, observations = load_observations(self.service, session_id)
        cached = self._cache.get(session_id)
        if (
            cached is not None
            and cached.event_cursor == cursor
            and cached.dimension == dimension
        ):
            return cached
        engine = EmergentTasteEngine(dimension)
        state = await asyncio.to_thread(engine.fit_state, observations)
        cache = _ProjectionCache(
            event_cursor=cursor,
            dimension=dimension,
            observations=observations,
            engine=engine,
            state=state,
        )
        self._cache[session_id] = cache
        return cache

    @staticmethod
    def _build_observation(
        snapshot,
        payload,
        *,
        chosen_candidate_id,
        observation_weight,
    ):
        return build_observation(
            snapshot,
            payload,
            chosen_candidate_id=chosen_candidate_id,
            observation_weight=observation_weight,
        )

    def _append_pending(
        self,
        session_id,
        *,
        command_kind,
        candidate_id,
        observation,
    ):
        append_pending(
            self.service,
            session_id,
            command_kind=command_kind,
            candidate_id=candidate_id,
            observation=observation,
        )

    def _lock_for(self, session_id: str) -> asyncio.Lock:
        lock = self._locks.get(session_id)
        if lock is None:
            lock = asyncio.Lock()
            self._locks[session_id] = lock
        return lock

    def _has_request_event(self, session_id: str, kind: str, request_id: str) -> bool:
        return any(
            event["kind"] == kind and event["payload"].get("request_id") == request_id
            for event in self.service.store.list_events(session_id)
        )

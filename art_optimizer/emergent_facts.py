from __future__ import annotations

import hashlib
import json
from typing import Any

from .domain import ExposurePayload, utc_now
from .emergent_taste import (
    TasteAlternative,
    TasteChoiceObservation,
    TasteDesignRef,
    deterministic_observation_id,
)
from .service import ArtOptimizerService, ConflictError, NotFoundError


PENDING_EVENT_KIND = "emergent_taste_choice_pending"
CHOICE_EVENT_KIND = "emergent_taste_choice_recorded"


def has_observation(
    service: ArtOptimizerService,
    session_id: str,
    observation_id: str,
) -> bool:
    return any(
        event["kind"] == CHOICE_EVENT_KIND
        and event["payload"].get("observation_id") == observation_id
        for event in service.store.list_events(session_id)
    )


def append_pending(
    service: ArtOptimizerService,
    session_id: str,
    *,
    command_kind: str,
    candidate_id: str | None,
    observation: TasteChoiceObservation,
) -> None:
    if any(
        event["kind"] == PENDING_EVENT_KIND
        and event["payload"].get("observation_id") == observation.observation_id
        for event in service.store.list_events(session_id)
    ):
        return
    service.store.append_event(
        session_id,
        PENDING_EVENT_KIND,
        {
            "observation_id": observation.observation_id,
            "request_id": observation.request_id,
            "command_kind": command_kind,
            "candidate_id": candidate_id,
            "observation": observation.model_dump(mode="json"),
        },
    )


def finalize_observation(
    service: ArtOptimizerService,
    session_id: str,
    observation: TasteChoiceObservation,
) -> bool:
    if has_observation(service, session_id, observation.observation_id):
        return False
    service.store.append_event(
        session_id,
        CHOICE_EVENT_KIND,
        observation.model_dump(mode="json"),
    )
    return True


def recover_pending(service: ArtOptimizerService, session_id: str) -> int:
    events = service.store.list_events(session_id)
    completed = {
        str(item["payload"].get("observation_id"))
        for item in events
        if item["kind"] == CHOICE_EVENT_KIND
    }
    base_by_request: dict[str, dict[str, Any]] = {}
    for item in events:
        if item["kind"] in {"candidate_committed", "round_rerolled", "round_skipped"}:
            request_id = item["payload"].get("request_id")
            if request_id:
                base_by_request[str(request_id)] = item

    recovered = 0
    for item in events:
        if item["kind"] != PENDING_EVENT_KIND:
            continue
        payload = item["payload"]
        observation_id = str(payload["observation_id"])
        if observation_id in completed:
            continue
        base_event = base_by_request.get(str(payload["request_id"]))
        if base_event is None:
            continue
        observation = TasteChoiceObservation.model_validate(payload["observation"])
        branch_node_id = base_event["payload"].get("branch_node_id")
        if branch_node_id:
            observation = observation.model_copy(
                update={"result_branch_node_id": str(branch_node_id)}
            )
        if finalize_observation(service, session_id, observation):
            completed.add(observation_id)
            recovered += 1
    return recovered


def load_observations(
    service: ArtOptimizerService,
    session_id: str,
) -> tuple[int, list[TasteChoiceObservation]]:
    recover_pending(service, session_id)
    events = [
        item
        for item in service.store.list_events(session_id)
        if item["kind"] == CHOICE_EVENT_KIND
    ]
    cursor = int(events[-1]["event_id"]) if events else 0
    return cursor, [
        TasteChoiceObservation.model_validate(item["payload"])
        for item in events
    ]


def representation_scope(snapshot: dict[str, Any]) -> dict[str, object]:
    renderer = snapshot.get("renderer") or {}
    current = snapshot["current_design"]
    manifest: dict[str, object] = {
        "schema": "fixed-root-scope/v2",
        "model_id": renderer.get("model_id", "unknown"),
        "renderer_revision": current["renderer_revision"],
        "codec_revision": renderer.get("codec_revision", "unknown"),
        "conditioning_mode": renderer.get("conditioning_mode", "unknown"),
        "control_basis_revision": current["control_basis_revision"],
        "prompt": snapshot["prompt"],
        "seed": int(snapshot["world"]["seed"]),
        "action_dimension": len(current["action"]),
    }
    encoded = json.dumps(manifest, sort_keys=True, separators=(",", ":"))
    manifest["scope_id"] = (
        f"fixed-root-scope/v1:{hashlib.sha256(encoded.encode()).hexdigest()}"
    )
    return manifest


def build_observation(
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
    scope = representation_scope(snapshot)
    branch_node_id = snapshot["current_branch_node_id"]
    return TasteChoiceObservation(
        observation_id=deterministic_observation_id(
            snapshot["session_id"],
            payload.request_id,
        ),
        request_id=payload.request_id,
        round_id=round_state["round_id"],
        seed=int(snapshot["world"]["seed"]),
        control_basis_revision=str(scope["scope_id"]),
        representation_scope_id=str(scope["scope_id"]),
        representation_scope=scope,
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
        receipt_semantics="power_evidence_v1",
    )

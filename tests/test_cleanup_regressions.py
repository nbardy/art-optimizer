from __future__ import annotations

import asyncio
import itertools
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pytest

from art_optimizer.composition import build_service
from art_optimizer.config import Settings
from art_optimizer.domain import (
    CommitPayload,
    CreateSessionRequest,
    ExposurePayload,
    NewWorldPayload,
    RestorePayload,
)
from art_optimizer.emergent_experiment import EmergentTasteExperiment
from art_optimizer.emergent_taste import (
    EmergentTasteEngine,
    TasteAlternative,
    TasteChoiceObservation,
    TasteDesignRef,
)


def make_settings(tmp_path: Path) -> Settings:
    return Settings(
        data_dir=tmp_path,
        database_path=tmp_path / "state.sqlite3",
        artifacts_dir=tmp_path / "artifacts",
        renderer_size=64,
    )


def observation(
    index: int,
    winner_index: int,
    weight: float = 1.0,
) -> TasteChoiceObservation:
    return TasteChoiceObservation(
        observation_id=f"observation-{index}",
        request_id=f"request-{index}",
        round_id=f"round-{index}",
        seed=42,
        control_basis_revision="scope-one",
        representation_scope_id="scope-one",
        anchor=TasteDesignRef(design_id=f"anchor-{index}", action=[0.0]),
        alternatives=[
            TasteAlternative(
                candidate_id=f"left-{index}",
                design_id=f"left-design-{index}",
                action=[-0.8],
                slot=1,
            ),
            TasteAlternative(
                candidate_id=f"right-{index}",
                design_id=f"right-design-{index}",
                action=[0.8],
                slot=2,
            ),
        ],
        winner_index=winner_index,
        result_branch_node_id=f"branch-{index}",
        created_at=datetime.now(UTC).isoformat(),
        observation_weight=weight,
        receipt_semantics="power_evidence_v1",
    )


def test_weighted_receipt_matches_the_fitted_power_likelihood() -> None:
    engine = EmergentTasteEngine(1, max_components=1)
    state = engine.fit_state([])
    item = observation(0, winner_index=2, weight=0.35)

    receipt = engine.predictive_receipts(state, item)["k=1"]
    probability = engine._choice_probability(np.zeros(1), item)

    assert receipt == pytest.approx(probability**0.35)


def test_forward_backward_matches_brute_force_hidden_paths() -> None:
    engine = EmergentTasteEngine(1, max_components=2, persistence=0.7)
    prevalence = np.asarray([0.5, 0.5])
    emissions = np.asarray([[0.8, 0.2], [0.3, 0.7], [0.6, 0.4]])
    responsibilities, filtered, log_likelihood = engine._forward_backward(
        emissions,
        prevalence,
    )

    transition = engine._transition_matrix(prevalence)
    path_weights: dict[tuple[int, ...], float] = {}
    for path in itertools.product(range(2), repeat=3):
        weight = prevalence[path[0]] * emissions[0, path[0]]
        for time_index in range(1, 3):
            weight *= transition[path[time_index - 1], path[time_index]]
            weight *= emissions[time_index, path[time_index]]
        path_weights[path] = float(weight)
    normalizer = sum(path_weights.values())
    expected = np.zeros_like(responsibilities)
    for path, weight in path_weights.items():
        for time_index, state_index in enumerate(path):
            expected[time_index, state_index] += weight / normalizer

    np.testing.assert_allclose(responsibilities, expected, atol=1e-10)
    np.testing.assert_allclose(filtered, expected[-1], atol=1e-10)
    assert log_likelihood == pytest.approx(np.log(normalizer))


def test_em_objective_uses_one_consistent_parameter_iterate() -> None:
    engine = EmergentTasteEngine(1, max_components=2, em_iterations=20)
    observations: list[TasteChoiceObservation] = []
    state = engine.fit_state([])
    for index, winner in enumerate([1] * 5 + [2] * 5):
        item = observation(index, winner)
        item = item.model_copy(
            update={"prediction_receipts": engine.predictive_receipts(state, item)}
        )
        observations.append(item)
        state = engine.fit_state(observations)

    fit = state.fits[2]
    expected = fit.log_likelihood - 0.5 * float(
        np.square(fit.centers).sum() / engine.prior_variance
    )
    assert fit.objective == pytest.approx(expected)


async def wait_for_ready(service, session_id: str, timeout: float = 8.0) -> dict:
    deadline = asyncio.get_running_loop().time() + timeout
    while asyncio.get_running_loop().time() < deadline:
        snapshot = await service.get_snapshot(session_id)
        candidates = (snapshot.get("active_round") or {}).get("candidates", [])
        if len(candidates) == 4 and all(item["status"] == "ready" for item in candidates):
            return snapshot
        await asyncio.sleep(0.05)
    raise AssertionError("candidate round did not become ready")


def test_reroll_checkpoint_survives_world_navigation(tmp_path: Path) -> None:
    async def run() -> None:
        service = build_service(make_settings(tmp_path))
        try:
            created = await service.create_session(
                CreateSessionRequest(prompt="checkpoint test", seed=123)
            )
            ready = await wait_for_ready(service, created["session_id"])
            rerolled = await service.reroll(
                created["session_id"],
                ExposurePayload(
                    request_id="command_checkpoint_reroll",
                    expected_mutation_version=ready["mutation_version"],
                    exposed_candidate_ids=[
                        item["candidate_id"]
                        for item in ready["active_round"]["candidates"]
                    ],
                ),
            )
            checkpoint = rerolled["current_branch_node_id"]
            assert rerolled["learner"]["observation_count"] == 1

            moved = await service.new_world(
                created["session_id"],
                NewWorldPayload(
                    request_id="command_checkpoint_new_world",
                    expected_mutation_version=rerolled["mutation_version"],
                ),
            )
            restored = await service.restore(
                created["session_id"],
                checkpoint,
                RestorePayload(
                    request_id="command_checkpoint_restore",
                    expected_mutation_version=moved["mutation_version"],
                ),
            )
            assert restored["learner"]["observation_count"] == 1
            assert restored["current_branch_node_id"] == checkpoint
        finally:
            await service.shutdown()

    asyncio.run(run())


def test_pending_preference_fact_recovers_after_base_commit(tmp_path: Path) -> None:
    async def run() -> None:
        service = build_service(make_settings(tmp_path))
        experiment = EmergentTasteExperiment(service)
        try:
            created = await experiment.create_session(
                CreateSessionRequest(prompt="pending recovery", seed=999)
            )
            ready = await wait_for_ready(service, created["session_id"])
            candidates = ready["active_round"]["candidates"]
            payload = CommitPayload(
                request_id="command_pending_recovery",
                expected_mutation_version=ready["mutation_version"],
                exposed_candidate_ids=[item["candidate_id"] for item in candidates],
            )
            cache = await experiment._load_cache_for_session(created["session_id"])
            draft = experiment._build_observation(
                ready,
                payload,
                chosen_candidate_id=candidates[0]["candidate_id"],
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
            experiment._append_pending(
                created["session_id"],
                command_kind="commit_candidate",
                candidate_id=candidates[0]["candidate_id"],
                observation=draft,
            )

            await service.commit_candidate(
                created["session_id"],
                candidates[0]["candidate_id"],
                payload,
            )
            recovered = await experiment.get_snapshot(created["session_id"])
            assert recovered["emergent_tastes"]["observation_count"] == 1
            events = service.store.list_events(created["session_id"])
            assert sum(
                item["kind"] == "emergent_taste_choice_recorded"
                for item in events
            ) == 1
        finally:
            await service.shutdown()

    asyncio.run(run())

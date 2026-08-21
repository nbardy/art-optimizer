from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

import numpy as np

from .domain import AtlasComponent, AtlasEvidence, PreferenceAtlasState, new_id, utc_now


@dataclass(slots=True)
class AtlasGuidance:
    component_id: str | None
    action_bias: np.ndarray | None
    mode: str


class PersistentPreferenceAtlas:
    """Event-sourced, multimodal preference memory.

    Components are rebuilt from retractable evidence, but their identities remain
    stable across ordinary updates. Evidence from incompatible feature encoders or
    generator control bases is never averaged together.
    """

    EVIDENCE_WEIGHTS = {
        "commit": 0.05,
        "revisit": 0.25,
        "favorite": 1.00,
        "export": 1.50,
    }

    def __init__(self, state: PreferenceAtlasState | None = None) -> None:
        self.state = state or PreferenceAtlasState()

    def add_evidence(
        self,
        *,
        design_id: str,
        feature_vector: list[float],
        action: list[float],
        kind: str,
        feature_revision: str = "procedural-features-13d/v1",
        control_basis_revision: str = "procedural-global-8d/v1",
        renderer_revision: str = "procedural-field/v2",
    ) -> AtlasEvidence:
        if kind not in self.EVIDENCE_WEIGHTS:
            raise ValueError(f"unsupported atlas evidence kind: {kind}")
        feature = np.asarray(feature_vector, dtype=np.float64)
        action_vector = np.asarray(action, dtype=np.float64)
        if feature.ndim != 1 or feature.size == 0 or not np.isfinite(feature).all():
            raise ValueError("atlas feature vector must be one-dimensional and finite")
        if action_vector.ndim != 1 or action_vector.size == 0 or not np.isfinite(action_vector).all():
            raise ValueError("atlas action must be one-dimensional and finite")

        evidence = AtlasEvidence(
            evidence_id=new_id("evidence"),
            design_id=design_id,
            feature_vector=feature.astype(float).tolist(),
            action=action_vector.astype(float).tolist(),
            kind=kind,  # type: ignore[arg-type]
            weight=self.EVIDENCE_WEIGHTS[kind],
            feature_revision=feature_revision,
            control_basis_revision=control_basis_revision,
            renderer_revision=renderer_revision,
        )
        self.state.evidence.append(evidence)
        self.rebuild()
        return evidence

    def retract_favorite(self, design_id: str) -> bool:
        changed = False
        for evidence in self.state.evidence:
            if evidence.design_id == design_id and evidence.kind == "favorite" and evidence.active:
                evidence.active = False
                changed = True
        if changed:
            self.rebuild()
        return changed

    def rebuild(self) -> None:
        previous_components = [component.model_copy(deep=True) for component in self.state.components]
        active_evidence = sorted(
            (item for item in self.state.evidence if item.active),
            key=lambda item: (item.created_at, item.evidence_id),
        )
        grouped: dict[tuple[str, str, int, int], list[AtlasEvidence]] = {}
        for evidence in active_evidence:
            key = (
                evidence.feature_revision,
                evidence.control_basis_revision,
                len(evidence.feature_vector),
                len(evidence.action),
            )
            grouped.setdefault(key, []).append(evidence)

        component_dicts: list[dict[str, Any]] = []
        provisional: list[AtlasEvidence] = []
        for group_key, group in grouped.items():
            strong = [item for item in group if item.kind in {"favorite", "export"}]
            weak = [item for item in group if item.kind in {"commit", "revisit"}]
            group_components: list[dict[str, Any]] = []

            # Strong evidence establishes the durable skeleton first. This means a
            # commit followed by a favorite for the same design cannot strand the
            # earlier weak evidence forever in the provisional buffer.
            for evidence in strong:
                feature = np.asarray(evidence.feature_vector, dtype=np.float64)
                action = np.asarray(evidence.action, dtype=np.float64)
                if not group_components:
                    group_components.append(self._new_component_dict(evidence, feature, action))
                    continue
                distances = [self._distance(feature, component) for component in group_components]
                nearest = int(np.argmin(distances))
                if distances[nearest] > 3.25:
                    group_components.append(self._new_component_dict(evidence, feature, action))
                else:
                    self._update_component_dict(group_components[nearest], evidence, feature, action)

            unassigned_weak: list[AtlasEvidence] = []
            for evidence in weak:
                feature = np.asarray(evidence.feature_vector, dtype=np.float64)
                action = np.asarray(evidence.action, dtype=np.float64)
                if group_components:
                    distances = [self._distance(feature, component) for component in group_components]
                    nearest = int(np.argmin(distances))
                    if distances[nearest] <= 2.35:
                        self._update_component_dict(group_components[nearest], evidence, feature, action)
                        continue
                unassigned_weak.append(evidence)

            promoted, remaining = self._promote_weak_clusters(unassigned_weak)
            group_components.extend(promoted)
            provisional.extend(remaining)
            component_dicts.extend(group_components)

        self._preserve_component_identities(component_dicts, previous_components)

        total_mass = sum(float(component["evidence_mass"]) for component in component_dicts)
        component_models: list[AtlasComponent] = []
        for component in component_dicts:
            evidence_mass = float(component["evidence_mass"])
            proposal_weight = evidence_mass / total_mass if total_mass > 0.0 else 0.0
            component_models.append(
                AtlasComponent(
                    component_id=str(component["component_id"]),
                    centroid=np.asarray(component["centroid"], dtype=np.float64).astype(float).tolist(),
                    variance=np.maximum(
                        np.asarray(component["variance"], dtype=np.float64), 0.015
                    ).astype(float).tolist(),
                    action_centroid=np.asarray(
                        component["action_centroid"], dtype=np.float64
                    ).astype(float).tolist(),
                    feature_revision=str(component["feature_revision"]),
                    control_basis_revision=str(component["control_basis_revision"]),
                    evidence_mass=evidence_mass,
                    evidence_count=int(component["evidence_count"]),
                    proposal_weight=proposal_weight,
                    exemplar_design_ids=list(component["exemplar_design_ids"])[-8:],
                    last_activated_at=str(component["last_activated_at"]),
                    status="active",
                )
            )

        component_models.sort(key=lambda item: (-item.proposal_weight, item.component_id))
        self.state.components = component_models
        self.state.provisional = provisional
        self.state.updated_at = utc_now()

    def choose_guidance(
        self,
        rng: np.random.Generator,
        *,
        control_basis_revision: str | None = None,
        action_dimension: int | None = None,
    ) -> AtlasGuidance:
        components = [component for component in self.state.components if component.status == "active"]
        if control_basis_revision is not None:
            components = [
                component
                for component in components
                if component.control_basis_revision == control_basis_revision
            ]
        if action_dimension is not None:
            components = [
                component for component in components if len(component.action_centroid) == action_dimension
            ]
        if not components or rng.random() < self.state.outside_prior_mass:
            return AtlasGuidance(component_id=None, action_bias=None, mode="outside_prior")

        weights = np.asarray([max(component.proposal_weight, 1e-9) for component in components])
        weights /= weights.sum()
        component = components[int(rng.choice(len(components), p=weights))]
        return AtlasGuidance(
            component_id=component.component_id,
            action_bias=np.asarray(component.action_centroid, dtype=np.float64),
            mode="within_prior",
        )

    def alternate_action_bias(
        self,
        active_component_id: str | None,
        *,
        control_basis_revision: str | None = None,
        action_dimension: int | None = None,
    ) -> np.ndarray | None:
        alternatives = [
            component
            for component in self.state.components
            if component.status == "active" and component.component_id != active_component_id
        ]
        if control_basis_revision is not None:
            alternatives = [
                component
                for component in alternatives
                if component.control_basis_revision == control_basis_revision
            ]
        if action_dimension is not None:
            alternatives = [
                component for component in alternatives if len(component.action_centroid) == action_dimension
            ]
        if not alternatives:
            return None
        alternatives.sort(key=lambda component: component.proposal_weight, reverse=True)
        return np.asarray(alternatives[0].action_centroid, dtype=np.float64)

    def summary(self) -> dict[str, object]:
        return {
            "revision": self.state.revision,
            "component_count": len(self.state.components),
            "provisional_count": len(self.state.provisional),
            "evidence_count": len([item for item in self.state.evidence if item.active]),
            "outside_prior_mass": self.state.outside_prior_mass,
            "components": [
                {
                    "component_id": component.component_id,
                    "weight": component.proposal_weight,
                    "evidence_mass": component.evidence_mass,
                    "evidence_count": component.evidence_count,
                    "feature_revision": component.feature_revision,
                    "control_basis_revision": component.control_basis_revision,
                    "exemplars": component.exemplar_design_ids,
                }
                for component in self.state.components
            ],
        }

    def _promote_weak_clusters(
        self, evidence_items: list[AtlasEvidence]
    ) -> tuple[list[dict[str, Any]], list[AtlasEvidence]]:
        promoted: list[dict[str, Any]] = []
        consumed: set[str] = set()
        for index, evidence in enumerate(evidence_items):
            if evidence.evidence_id in consumed:
                continue
            anchor = np.asarray(evidence.feature_vector, dtype=np.float64)
            cluster = [evidence]
            for other in evidence_items[index + 1 :]:
                if other.evidence_id in consumed or other.design_id == evidence.design_id:
                    continue
                distance = float(
                    np.linalg.norm(np.asarray(other.feature_vector, dtype=np.float64) - anchor)
                )
                if distance <= 0.75:
                    cluster.append(other)
            if len({item.design_id for item in cluster}) < 3:
                continue

            first = cluster[0]
            component = self._new_component_dict(
                first,
                np.asarray(first.feature_vector, dtype=np.float64),
                np.asarray(first.action, dtype=np.float64),
            )
            for item in cluster[1:]:
                self._update_component_dict(
                    component,
                    item,
                    np.asarray(item.feature_vector, dtype=np.float64),
                    np.asarray(item.action, dtype=np.float64),
                )
            promoted.append(component)
            consumed.update(item.evidence_id for item in cluster)

        remaining = [item for item in evidence_items if item.evidence_id not in consumed]
        return promoted, remaining

    @staticmethod
    def _distance(feature: np.ndarray, component: dict[str, Any]) -> float:
        centroid = np.asarray(component["centroid"], dtype=np.float64)
        variance = np.maximum(np.asarray(component["variance"], dtype=np.float64), 0.025)
        return float(np.sqrt(np.mean(((feature - centroid) ** 2) / variance)))

    @staticmethod
    def _stable_component_id(evidence: AtlasEvidence) -> str:
        material = (
            f"{evidence.feature_revision}:{evidence.control_basis_revision}:{evidence.evidence_id}"
        ).encode("utf-8")
        return f"taste_{hashlib.sha256(material).hexdigest()[:24]}"

    def _new_component_dict(
        self,
        evidence: AtlasEvidence,
        feature: np.ndarray,
        action: np.ndarray,
    ) -> dict[str, Any]:
        return {
            "component_id": self._stable_component_id(evidence),
            "centroid": feature.astype(np.float64),
            "variance": np.full(feature.shape, 0.035, dtype=np.float64),
            "action_centroid": action.astype(np.float64),
            "feature_revision": evidence.feature_revision,
            "control_basis_revision": evidence.control_basis_revision,
            "evidence_mass": float(evidence.weight),
            "evidence_count": 1,
            "exemplar_design_ids": [evidence.design_id]
            if evidence.kind in {"favorite", "export"}
            else [],
            "last_activated_at": evidence.created_at,
        }

    @staticmethod
    def _update_component_dict(
        component: dict[str, Any],
        evidence: AtlasEvidence,
        feature: np.ndarray,
        action: np.ndarray,
    ) -> None:
        old_mass = float(component["evidence_mass"])
        new_mass = old_mass + evidence.weight
        rate = evidence.weight / max(new_mass, 1e-12)

        old_centroid = np.asarray(component["centroid"], dtype=np.float64)
        delta = feature - old_centroid
        new_centroid = old_centroid + rate * delta
        old_variance = np.asarray(component["variance"], dtype=np.float64)
        new_variance = (1.0 - rate) * old_variance + rate * (delta**2)

        old_action = np.asarray(component["action_centroid"], dtype=np.float64)
        new_action = old_action + rate * (action - old_action)

        component["centroid"] = new_centroid
        component["variance"] = np.maximum(new_variance, 0.015)
        component["action_centroid"] = new_action
        component["evidence_mass"] = new_mass
        component["evidence_count"] = int(component["evidence_count"]) + 1
        exemplars = list(component["exemplar_design_ids"])
        if evidence.kind in {"favorite", "export"} and evidence.design_id not in exemplars:
            exemplars.append(evidence.design_id)
        component["exemplar_design_ids"] = exemplars[-8:]
        component["last_activated_at"] = evidence.created_at

    def _preserve_component_identities(
        self,
        new_components: list[dict[str, Any]],
        previous_components: list[AtlasComponent],
    ) -> None:
        unused = set(range(len(previous_components)))
        for component in new_components:
            compatible = [
                index
                for index in unused
                if previous_components[index].feature_revision == component["feature_revision"]
                and previous_components[index].control_basis_revision
                == component["control_basis_revision"]
                and len(previous_components[index].centroid)
                == len(np.asarray(component["centroid"]))
            ]
            if not compatible:
                continue

            new_exemplars = set(component["exemplar_design_ids"])
            overlap_matches = [
                index
                for index in compatible
                if new_exemplars.intersection(previous_components[index].exemplar_design_ids)
            ]
            candidates = overlap_matches or compatible
            centroid = np.asarray(component["centroid"], dtype=np.float64)
            distances = [
                float(
                    np.linalg.norm(
                        centroid - np.asarray(previous_components[index].centroid, dtype=np.float64)
                    )
                    / np.sqrt(max(centroid.size, 1))
                )
                for index in candidates
            ]
            best_position = int(np.argmin(distances))
            best_index = candidates[best_position]
            if overlap_matches or distances[best_position] <= 0.18:
                component["component_id"] = previous_components[best_index].component_id
                unused.remove(best_index)

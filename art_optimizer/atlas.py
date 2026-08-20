from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .domain import (
    AtlasComponent,
    AtlasEvidence,
    PreferenceAtlasState,
    new_id,
    utc_now,
)


@dataclass(slots=True)
class AtlasGuidance:
    component_id: str | None
    action_bias: np.ndarray | None
    mode: str


class PersistentPreferenceAtlas:
    """Event-sourced multimodal preference memory.

    Strong novel evidence may spawn a component. Weak novel evidence is held in a
    provisional buffer until several coherent events support a new mode.
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
    ) -> AtlasEvidence:
        if kind not in self.EVIDENCE_WEIGHTS:
            raise ValueError(f"unsupported atlas evidence kind: {kind}")
        evidence = AtlasEvidence(
            evidence_id=new_id("evidence"),
            design_id=design_id,
            feature_vector=feature_vector,
            action=action,
            kind=kind,  # type: ignore[arg-type]
            weight=self.EVIDENCE_WEIGHTS[kind],
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
        components: list[dict[str, object]] = []
        provisional: list[AtlasEvidence] = []

        for evidence in [item for item in self.state.evidence if item.active]:
            feature = np.asarray(evidence.feature_vector, dtype=np.float64)
            action = np.asarray(evidence.action, dtype=np.float64)

            if not components:
                if evidence.kind in {"favorite", "export"}:
                    components.append(self._new_component_dict(evidence, feature, action))
                else:
                    provisional.append(evidence)
                continue

            distances = [self._distance(feature, component) for component in components]
            nearest_index = int(np.argmin(distances))
            nearest_distance = distances[nearest_index]

            # Strong evidence may establish a genuinely new taste mode.
            if evidence.kind in {"favorite", "export"} and nearest_distance > 3.25:
                components.append(self._new_component_dict(evidence, feature, action))
                continue

            # Weak evidence only updates an existing nearby component.
            if evidence.kind in {"commit", "revisit"} and nearest_distance > 2.35:
                provisional.append(evidence)
                continue

            self._update_component_dict(components[nearest_index], evidence, feature, action)

        # Promote a coherent cluster of at least three weak events from distinct designs.
        remaining: list[AtlasEvidence] = []
        consumed: set[str] = set()
        for index, evidence in enumerate(provisional):
            if evidence.evidence_id in consumed:
                continue
            anchor = np.asarray(evidence.feature_vector, dtype=np.float64)
            cluster = [evidence]
            for other in provisional[index + 1 :]:
                if other.evidence_id in consumed or other.design_id == evidence.design_id:
                    continue
                distance = float(np.linalg.norm(np.asarray(other.feature_vector) - anchor))
                if distance <= 0.75:
                    cluster.append(other)
            if len({item.design_id for item in cluster}) >= 3:
                first = cluster[0]
                component = self._new_component_dict(
                    first,
                    np.asarray(first.feature_vector),
                    np.asarray(first.action),
                )
                for item in cluster[1:]:
                    self._update_component_dict(
                        component,
                        item,
                        np.asarray(item.feature_vector),
                        np.asarray(item.action),
                    )
                components.append(component)
                consumed.update(item.evidence_id for item in cluster)
            else:
                remaining.append(evidence)

        total_mass = sum(float(component["evidence_mass"]) for component in components)
        component_models: list[AtlasComponent] = []
        for component in components:
            evidence_mass = float(component["evidence_mass"])
            proposal_weight = evidence_mass / total_mass if total_mass > 0 else 0.0
            component_models.append(
                AtlasComponent(
                    component_id=str(component["component_id"]),
                    centroid=np.asarray(component["centroid"]).tolist(),
                    variance=np.maximum(np.asarray(component["variance"]), 0.015).tolist(),
                    action_centroid=np.asarray(component["action_centroid"]).tolist(),
                    evidence_mass=evidence_mass,
                    evidence_count=int(component["evidence_count"]),
                    proposal_weight=proposal_weight,
                    exemplar_design_ids=list(component["exemplar_design_ids"])[-8:],
                    last_activated_at=str(component["last_activated_at"]),
                    status="active",
                )
            )

        self.state.components = component_models
        self.state.provisional = [item for item in remaining if item.evidence_id not in consumed]
        self.state.updated_at = utc_now()

    def choose_guidance(self, rng: np.random.Generator) -> AtlasGuidance:
        components = [component for component in self.state.components if component.status == "active"]
        if not components or rng.random() < self.state.outside_prior_mass:
            return AtlasGuidance(component_id=None, action_bias=None, mode="outside_prior")

        weights = np.asarray([max(component.proposal_weight, 1e-6) for component in components])
        weights /= weights.sum()
        component = components[int(rng.choice(len(components), p=weights))]
        return AtlasGuidance(
            component_id=component.component_id,
            action_bias=np.asarray(component.action_centroid, dtype=np.float64),
            mode="within_prior",
        )

    def alternate_action_bias(self, active_component_id: str | None) -> np.ndarray | None:
        alternatives = [
            component
            for component in self.state.components
            if component.status == "active" and component.component_id != active_component_id
        ]
        if not alternatives:
            return None
        alternatives.sort(key=lambda component: component.proposal_weight, reverse=True)
        return np.asarray(alternatives[0].action_centroid, dtype=np.float64)

    def summary(self) -> dict[str, object]:
        return {
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
                    "exemplars": component.exemplar_design_ids,
                }
                for component in self.state.components
            ],
        }

    @staticmethod
    def _distance(feature: np.ndarray, component: dict[str, object]) -> float:
        centroid = np.asarray(component["centroid"], dtype=np.float64)
        variance = np.maximum(np.asarray(component["variance"], dtype=np.float64), 0.025)
        return float(np.sqrt(np.mean(((feature - centroid) ** 2) / variance)))

    @staticmethod
    def _new_component_dict(
        evidence: AtlasEvidence,
        feature: np.ndarray,
        action: np.ndarray,
    ) -> dict[str, object]:
        return {
            "component_id": new_id("taste"),
            "centroid": feature.astype(np.float64),
            "variance": np.full(feature.shape, 0.035, dtype=np.float64),
            "action_centroid": action.astype(np.float64),
            "evidence_mass": float(evidence.weight),
            "evidence_count": 1,
            "exemplar_design_ids": [evidence.design_id],
            "last_activated_at": evidence.created_at,
        }

    @staticmethod
    def _update_component_dict(
        component: dict[str, object],
        evidence: AtlasEvidence,
        feature: np.ndarray,
        action: np.ndarray,
    ) -> None:
        old_mass = float(component["evidence_mass"])
        new_mass = old_mass + evidence.weight
        rate = evidence.weight / max(new_mass, 1e-9)

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

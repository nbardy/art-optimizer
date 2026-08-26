from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class UIExperiment:
    experiment_id: str
    label: str
    description: str
    filename: str
    treatment_id: str
    concept_controls: str

    def public_metadata(self) -> dict[str, str]:
        payload = asdict(self)
        payload["route"] = f"/ui/{self.experiment_id}"
        return payload


_EXPERIMENTS = {
    "current-image": UIExperiment(
        experiment_id="current-image",
        label="Current image",
        description="The original one-canvas, four-corner controlled-search interaction.",
        filename="index.html",
        treatment_id="t0-controlled-search",
        concept_controls="none",
    ),
    "implicit-lanes": UIExperiment(
        experiment_id="implicit-lanes",
        label="Implicit lanes",
        description=(
            "T0 presentation variant with automatically grouped browser-local directions."
        ),
        filename="implicit.html",
        treatment_id="t0-controlled-search",
        concept_controls="optional",
    ),
    "concept-shelf": UIExperiment(
        experiment_id="concept-shelf",
        label="Concept shelf",
        description="T0 presentation variant with a visible browser-local direction shelf.",
        filename="shelf.html",
        treatment_id="t0-controlled-search",
        concept_controls="visible",
    ),
    "lane-board": UIExperiment(
        experiment_id="lane-board",
        label="Lane board",
        description="T0 presentation variant that groups candidates by heuristic lanes.",
        filename="lanes.html",
        treatment_id="t0-controlled-search",
        concept_controls="structural",
    ),
    "emergent-tastes": UIExperiment(
        experiment_id="emergent-tastes",
        label="Emergent tastes",
        description=(
            "Fixed-root authored-axis search with chronologically tested latent taste modes "
            "and seed-by-strength taste galleries."
        ),
        filename="emergent.html",
        treatment_id="emergent-tastes",
        concept_controls="emergent",
    ),
    "direction-lab": UIExperiment(
        experiment_id="direction-lab",
        label="Random Direction Lab",
        description=(
            "Four non-string embedding point codecs on an explicit RMS shell, with a fixed "
            "diffusion seed and an iterative choose-the-new-center workflow."
        ),
        filename="direction_lab.html",
        treatment_id="random-direction-lab",
        concept_controls="none",
    ),
}


def ui_catalog() -> list[dict[str, str]]:
    return [experiment.public_metadata() for experiment in _EXPERIMENTS.values()]


def get_ui_experiment(experiment_id: str) -> UIExperiment:
    experiment = _EXPERIMENTS.get(experiment_id)
    if experiment is None:
        available = ", ".join(_EXPERIMENTS)
        raise KeyError(f"unknown UI experiment {experiment_id!r}; choose one of: {available}")
    return experiment


def validate_ui_files(static_dir: Path) -> None:
    required = ["experiments.html", "experiments.js", "experiments.css"]
    required.extend(item.filename for item in _EXPERIMENTS.values())
    missing = [filename for filename in required if not (static_dir / filename).is_file()]
    if missing:
        raise ValueError(f"UI directory is missing bundled experiments: {', '.join(missing)}")

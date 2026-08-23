from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class UIExperiment:
    experiment_id: str
    label: str
    description: str
    filename: str
    concept_controls: str

    def public_metadata(self) -> dict[str, str]:
        return asdict(self)


_EXPERIMENTS = {
    "current-image": UIExperiment(
        experiment_id="current-image",
        label="Current image",
        description="The original one-canvas, four-corner committed-image interaction.",
        filename="index.html",
        concept_controls="none",
    ),
    "implicit-lanes": UIExperiment(
        experiment_id="implicit-lanes",
        label="Implicit lanes",
        description=(
            "Choices learn reusable directions automatically; concept controls stay behind "
            "progressive disclosure."
        ),
        filename="implicit.html",
        concept_controls="optional",
    ),
    "concept-shelf": UIExperiment(
        experiment_id="concept-shelf",
        label="Concept shelf",
        description=(
            "A visible shelf composes learned non-prompt directions with tri-state control."
        ),
        filename="shelf.html",
        concept_controls="visible",
    ),
    "lane-board": UIExperiment(
        experiment_id="lane-board",
        label="Lane board",
        description=(
            "Candidates are organized by whether they reinforce active concepts, reopen an "
            "inactive concept, or explore unexplained space."
        ),
        filename="lanes.html",
        concept_controls="structural",
    ),
    "emergent-tastes": UIExperiment(
        experiment_id="emergent-tastes",
        label="Emergent tastes",
        description=(
            "A fixed-root embedding-search UI where latent taste modes emerge from "
            "chronologically tested votes instead of manual shelves or labels."
        ),
        filename="emergent.html",
        concept_controls="emergent",
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


def selected_ui_id() -> str:
    return os.environ.get("ART_OPTIMIZER_UI", "current-image").strip().lower()


def validate_ui_files(static_dir: Path) -> None:
    missing = [
        item.filename
        for item in _EXPERIMENTS.values()
        if not (static_dir / item.filename).is_file()
    ]
    if missing:
        raise ValueError(f"UI directory is missing bundled experiments: {', '.join(missing)}")

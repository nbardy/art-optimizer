from __future__ import annotations

import hashlib
import json
import os
from typing import Any

from ..rendering import ImageRenderer
from .contracts import RepresentationScope


def _digest(payload: Any) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def normalized_prompt(prompt: str) -> str:
    return " ".join(prompt.split())


def prompt_digest(prompt: str) -> str:
    return hashlib.sha256(normalized_prompt(prompt).encode("utf-8")).hexdigest()


def _backend(renderer: ImageRenderer) -> Any:
    return getattr(renderer, "_backend", renderer)


def build_representation_scope(
    renderer: ImageRenderer,
    prompt: str,
) -> RepresentationScope:
    """Materialize a canonical, honest compatibility manifest.

    Diffusers may resolve a floating repository revision only when the model is
    downloaded. Until a revision is explicitly pinned, the scope records
    ``unresolved`` and is deliberately non-portable across machines.
    """

    capabilities = renderer.capabilities()
    backend = _backend(renderer)
    configured_revision = (
        getattr(backend, "model_revision", None)
        or os.environ.get("ART_OPTIMIZER_MODEL_REVISION")
    )
    if capabilities.model_id == "procedural":
        model_revision = capabilities.renderer_revision
        portable = True
    else:
        model_revision = configured_revision or "unresolved"
        portable = configured_revision is not None

    model_source = (
        getattr(backend, "model_source", None)
        or capabilities.model_source
        or os.environ.get("ART_OPTIMIZER_MODEL_SOURCE", "")
        or "unknown"
    )
    conditioning_mode = (
        getattr(backend, "conditioning_mode", None)
        or capabilities.conditioning_mode
        or "unknown"
    )
    normalized = normalized_prompt(prompt)
    prompt_hash = prompt_digest(normalized)

    direction_manifest = {
        "schema": "conditioning-basis-instance/v1",
        "model_id": capabilities.model_id,
        "model_source": model_source,
        "model_revision": model_revision,
        "renderer_revision": capabilities.renderer_revision,
        "control_codec_revision": capabilities.codec_revision,
        "control_basis_revision": capabilities.control_basis_revision,
        "conditioning_mode": conditioning_mode,
        "prompt_digest": prompt_hash,
        "action_dimension": capabilities.action_dimension,
    }
    direction_bank_digest = _digest(direction_manifest)
    scope_manifest = {
        **direction_manifest,
        "direction_bank_digest": direction_bank_digest,
        "prompt_scope_id": f"prompt_{prompt_hash[:24]}",
    }
    scope_id = f"scope_{_digest(scope_manifest)}"
    return RepresentationScope(
        scope_id=scope_id,
        model_id=capabilities.model_id,
        model_source=model_source,
        model_revision=model_revision,
        renderer_revision=capabilities.renderer_revision,
        control_codec_revision=capabilities.codec_revision,
        control_basis_revision=capabilities.control_basis_revision,
        direction_bank_digest=direction_bank_digest,
        prompt_digest=prompt_hash,
        prompt_scope_id=scope_manifest["prompt_scope_id"],
        action_dimension=capabilities.action_dimension,
        conditioning_mode=conditioning_mode,
        portable=portable,
    )


def root_noise_digest(
    scope: RepresentationScope,
    *,
    seed: int,
) -> str:
    return _digest(
        {
            "schema": "root-noise-context/v1",
            "scope_id": scope.scope_id,
            "seed": int(seed),
        }
    )


def comparison_context_digest(
    scope: RepresentationScope,
    *,
    seed: int,
) -> str:
    return _digest(
        {
            "schema": "same-context-comparison/v1",
            "scope_id": scope.scope_id,
            "prompt_digest": scope.prompt_digest,
            "root_noise_digest": root_noise_digest(scope, seed=seed),
        }
    )


def stable_int(*parts: object, bits: int = 62) -> int:
    material = "\0".join(str(part) for part in parts).encode("utf-8")
    value = int.from_bytes(hashlib.sha256(material).digest()[:8], "little")
    return value & ((1 << bits) - 1)


def stable_id(prefix: str, *parts: object) -> str:
    material = "\0".join(str(part) for part in parts).encode("utf-8")
    return f"{prefix}_{hashlib.sha256(material).hexdigest()[:32]}"

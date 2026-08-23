"""Round 2 truthful-search runtime.

The package is intentionally isolated from the preserved T0 baseline. It adds
typed command semantics, exact representation scope, hybrid-root provenance,
perceptual duplicate diagnostics, an explicit render queue, and read-only
shadow-engine evaluation.
"""

from .contracts import TRUTHFUL_SEARCH_TREATMENT_ID

__all__ = ["TRUTHFUL_SEARCH_TREATMENT_ID"]

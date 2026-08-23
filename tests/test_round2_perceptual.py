from __future__ import annotations

import numpy as np

from art_optimizer.round2.perceptual import (
    PERCEPTUAL_REVISION,
    cosine_distance,
    image_embedding,
    slate_receipt,
)


def split_image(*, reverse: bool = False) -> np.ndarray:
    image = np.zeros((32, 32, 3), dtype=np.uint8)
    left = (0, 0, 255) if reverse else (255, 0, 0)
    right = (255, 0, 0) if reverse else (0, 0, 255)
    image[:, :16] = left
    image[:, 16:] = right
    return image


def test_perceptual_embedding_is_deterministic_and_spatial() -> None:
    first = image_embedding(split_image())
    repeated = image_embedding(split_image())
    reversed_layout = image_embedding(split_image(reverse=True))

    np.testing.assert_allclose(first, repeated, atol=0.0)
    assert first.shape == (194,)
    assert cosine_distance(first, repeated) == 0.0
    assert cosine_distance(first, reversed_layout) > 0.05


def test_slate_receipt_marks_anchor_and_candidate_duplicates() -> None:
    anchor = image_embedding(split_image())
    same = image_embedding(split_image())
    different = image_embedding(split_image(reverse=True))
    receipt = slate_receipt(
        session_id="session_test",
        round_id="round_test",
        anchor_id="anchor_design",
        anchor_embedding=anchor,
        candidate_embeddings={
            "candidate_same": same,
            "candidate_different": different,
            "candidate_same_again": same,
        },
    )

    assert receipt.revision == PERCEPTUAL_REVISION
    assert receipt.duplicate_of["candidate_same"] == "anchor_design"
    assert receipt.duplicate_of["candidate_same_again"] == "anchor_design"
    assert "candidate_different" not in receipt.duplicate_of
    assert len(receipt.distance_matrix) == 3

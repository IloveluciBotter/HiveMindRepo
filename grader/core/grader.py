"""
core/grader.py

Measures centering and surface condition on a perspective-corrected card
image (1000×1400 px canonical frame from vision.align_card).

Public functions
----------------
measure_centering(warped)     – returns horizontal and vertical centering %
detect_edge_wear(warped)      – returns an estimated condition % (0–100)
"""

import cv2
import numpy as np
from dataclasses import dataclass
from typing import Tuple


# ─────────────────────────────────────────────
#  Constants – tuned for a 1000×1400 warped frame
# ─────────────────────────────────────────────

# The artwork border sits roughly 6 % in from each physical card edge.
# Adjust this if your card art starts at a different pixel offset.
ARTWORK_INSET_RATIO: float = 0.06

# The outer "wear zone" is the outermost 5 % of the card on each side.
WEAR_ZONE_RATIO: float = 0.05

# Pixel intensity threshold used to classify a pixel as "white/silver"
# (indicative of edge whitening from wear).
WHITENING_THRESHOLD: int = 200


# ─────────────────────────────────────────────
#  Data container
# ─────────────────────────────────────────────

@dataclass
class GradeReport:
    """All numeric outputs produced by the grader for one card image."""
    centering_ratio_horizontal: float   # L/(L+R)*100  →  50 is perfect
    centering_ratio_vertical: float     # T/(T+B)*100  →  50 is perfect
    estimated_condition_score: float    # 0–100, higher is better


# ─────────────────────────────────────────────
#  Centering
# ─────────────────────────────────────────────

def measure_centering(warped: np.ndarray) -> Tuple[float, float]:
    """
    Calculate how well-centred the artwork is inside the card frame.

    The card has a physical border around the artwork.  We find where that
    inner artwork border starts on all four sides by scanning inward from
    each edge and detecting the first significant dark line (the printed
    border).

    Formula (same for vertical)
    ---------------------------
        horizontal_ratio = L / (L + R) * 100

    A perfect score is 50.  A value above 50 means the artwork is shifted
    right; below 50 means it is shifted left.

    Parameters
    ----------
    warped : np.ndarray
        A 1000×1400 BGR image produced by align_card().

    Returns
    -------
    (centering_ratio_horizontal, centering_ratio_vertical) : (float, float)
    """
    _validate_warped(warped)

    h, w = warped.shape[:2]
    gray = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)

    # Estimate the artwork inset in pixels.
    inset_x = int(w * ARTWORK_INSET_RATIO)
    inset_y = int(h * ARTWORK_INSET_RATIO)

    # ── Find inner border edges with column/row projection ────────────────
    # We look for the darkest column/row within a search band near each edge.
    # "Darkest" ≈ the printed artwork border line.

    left = _find_dark_edge(gray, axis="col", start=inset_x // 2, end=inset_x * 3)
    right = _find_dark_edge(
        gray, axis="col", start=w - inset_x * 3, end=w - inset_x // 2, reverse=True
    )
    top = _find_dark_edge(gray, axis="row", start=inset_y // 2, end=inset_y * 3)
    bottom = _find_dark_edge(
        gray, axis="row", start=h - inset_y * 3, end=h - inset_y // 2, reverse=True
    )

    # Distances from the physical card edge to the artwork border.
    L = float(left)
    R = float(w - right)
    T = float(top)
    B = float(h - bottom)

    # Guard against a degenerate case where both sides measure 0.
    h_ratio = (L / (L + R) * 100) if (L + R) > 0 else 50.0
    v_ratio = (T / (T + B) * 100) if (T + B) > 0 else 50.0

    return round(h_ratio, 2), round(v_ratio, 2)


# ─────────────────────────────────────────────
#  Condition / edge wear
# ─────────────────────────────────────────────

def detect_edge_wear(warped: np.ndarray) -> float:
    """
    Estimate a surface condition score by examining the card's outer border.

    A card in mint condition has a uniform, solid-coloured border (usually
    black or yellow).  Edge wear shows up as bright white or silver streaks
    where the card's ink has chipped away.

    Method
    ------
    1. Create a mask that isolates the outermost WEAR_ZONE_RATIO (5 %) on
       all four sides, excluding the corners (which are always a bit rough).
    2. Count pixels in that mask whose brightness exceeds WHITENING_THRESHOLD.
    3. Express that count as a fraction of the total mask area → "wear ratio".
    4. Condition score = (1 − wear_ratio) × 100.

    Parameters
    ----------
    warped : np.ndarray
        A 1000×1400 BGR image.

    Returns
    -------
    float
        Condition score 0–100.  100 means no detectable edge whitening.
    """
    _validate_warped(warped)

    h, w = warped.shape[:2]
    gray = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)

    # ── Build the border mask ─────────────────────────────────────────────
    px = int(w * WEAR_ZONE_RATIO)   # horizontal strip thickness
    py = int(h * WEAR_ZONE_RATIO)   # vertical strip thickness

    mask = np.zeros((h, w), dtype=np.uint8)

    # Left and right strips (full height).
    mask[:, :px] = 255
    mask[:, w - px:] = 255

    # Top and bottom strips (full width).
    mask[:py, :] = 255
    mask[h - py:, :] = 255

    # ── Count whitened pixels inside the mask ─────────────────────────────
    border_pixels = gray[mask == 255]
    whitened = int(np.sum(border_pixels >= WHITENING_THRESHOLD))
    total = int(border_pixels.size)

    if total == 0:
        return 100.0

    wear_ratio = whitened / total
    condition_score = (1.0 - wear_ratio) * 100.0

    return round(condition_score, 2)


# ─────────────────────────────────────────────
#  Internal helpers
# ─────────────────────────────────────────────

def _find_dark_edge(
    gray: np.ndarray,
    axis: str,
    start: int,
    end: int,
    reverse: bool = False,
) -> int:
    """
    Scan a band of columns (axis='col') or rows (axis='row') and return the
    index of the darkest one – a proxy for the artwork border line.

    Parameters
    ----------
    gray    : grayscale image
    axis    : 'col' or 'row'
    start   : beginning of the search band (inclusive)
    end     : end of the search band (exclusive)
    reverse : if True, scan from end back to start (used for right/bottom)

    Returns
    -------
    int – column or row index of the detected edge.
    """
    start = max(0, start)

    if axis == "col":
        end = min(gray.shape[1], end)
        means = np.mean(gray[:, start:end], axis=0)
    else:
        end = min(gray.shape[0], end)
        means = np.mean(gray[start:end, :], axis=1)

    if means.size == 0:
        return start

    dark_idx = int(np.argmin(means))
    return start + dark_idx


def _validate_warped(image: np.ndarray) -> None:
    """Raise ValueError if the image is not a plausible warped card frame."""
    if image is None or image.size == 0:
        raise ValueError("grader received an empty image.")
    if image.ndim != 3 or image.shape[2] != 3:
        raise ValueError("grader expects a 3-channel BGR image.")

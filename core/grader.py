"""
Grading metrics: centering (edge-to-artwork margins) and border whitening (condition).
"""

from __future__ import annotations

from typing import Tuple

import cv2
import numpy as np


# Fraction of width/height treated as outer border strip for wear detection.
BORDER_FRACTION = 0.05

# Pixels at or above this intensity in grayscale count as "white/silver" wear.
HIGH_INTENSITY_THRESHOLD = 200


def _find_inner_artwork_bbox(gray: np.ndarray) -> Tuple[int, int, int, int] | None:
    """
    Estimate the inner artwork rectangle using Canny contours.

    Returns (x, y, w, h) in pixel coordinates relative to the warped card image,
    or None if no plausible inner box is found.
    """
    h, w = gray.shape[:2]
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 40, 120)
    kernel = np.ones((5, 5), np.uint8)
    edges = cv2.dilate(edges, kernel, iterations=2)

    contours, hierarchy = cv2.findContours(
        edges, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE
    )
    if hierarchy is None:
        return None

    img_area = float(h * w)
    best_rect = None
    best_score = -1.0

    for i, cnt in enumerate(contours):
        area = cv2.contourArea(cnt)
        if area < 0.25 * img_area or area > 0.98 * img_area:
            continue
        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)
        if len(approx) < 4:
            continue
        x, y, rw, rh = cv2.boundingRect(approx)
        if rw < 10 or rh < 10:
            continue
        # Prefer large rectangles that are well inside the image
        margin_penalty = (x + y + (w - x - rw) + (h - y - rh)) / (2 * (w + h))
        score = area * (1.0 - margin_penalty)
        if score > best_score:
            best_score = score
            best_rect = (x, y, rw, rh)

    return best_rect


def measure_centering(
    warped_bgr: np.ndarray,
) -> Tuple[float, float, str]:
    """
    Compute centering ratios from physical card edges to inner artwork border.

    Horizontal ratio = (L / (L + R)) * 100 (50 = centered).
    Vertical ratio = (T / (T + B)) * 100.

    Returns:
        (centering_ratio_horizontal, centering_ratio_vertical, notes)
    """
    h, w = warped_bgr.shape[:2]
    gray = cv2.cvtColor(warped_bgr, cv2.COLOR_BGR2GRAY)

    inner = _find_inner_artwork_bbox(gray)
    if inner is None:
        return (
            float("nan"),
            float("nan"),
            "Inner artwork border could not be detected; centering not computed.",
        )

    ix, iy, iw, ih = inner
    L = float(ix)
    R = float(w - (ix + iw))
    T = float(iy)
    B = float(h - (iy + ih))

    eps = 1e-6
    horiz = (L / (L + R + eps)) * 100.0
    vert = (T / (T + B + eps)) * 100.0

    return horiz, vert, "OK"


def detect_edge_wear(
    warped_bgr: np.ndarray,
    border_fraction: float = BORDER_FRACTION,
    high_intensity_threshold: int = HIGH_INTENSITY_THRESHOLD,
) -> Tuple[float, str]:
    """
    Mask the outer ``border_fraction`` of the card on each side and measure whitening.

    Counts grayscale pixels >= ``high_intensity_threshold`` in the border mask.
    Returns estimated_condition_score in [0, 100], where lower scores mean more
    visible whitening/wear in the border region.
    """
    if not (0 < border_fraction < 0.5):
        raise ValueError("border_fraction must be between 0 and 0.5.")

    h, w = warped_bgr.shape[:2]
    gray = cv2.cvtColor(warped_bgr, cv2.COLOR_BGR2GRAY)

    mx = int(round(w * border_fraction))
    my = int(round(h * border_fraction))
    mx = max(1, min(mx, w // 2 - 1))
    my = max(1, min(my, h // 2 - 1))

    mask = np.zeros((h, w), dtype=np.uint8)
    # Top and bottom strips (full width)
    mask[0:my, :] = 1
    mask[h - my : h, :] = 1
    # Left and right strips (excluding corners already counted — use full height for side strips)
    mask[:, 0:mx] = 1
    mask[:, w - mx : w] = 1

    border_pixels = mask.astype(bool)
    total = int(np.count_nonzero(border_pixels))
    if total == 0:
        return 0.0, "Border mask empty; condition not computed."

    bright = np.count_nonzero(gray[border_pixels] >= high_intensity_threshold)
    wear_ratio = bright / float(total)
    # Map wear to a 0-100 condition score (more bright pixels => lower score).
    estimated = max(0.0, min(100.0, 100.0 * (1.0 - wear_ratio)))

    return estimated, f"Border wear_ratio={wear_ratio:.4f} (bright/total in border mask)."

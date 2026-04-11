"""
core/vision.py

Handles image quality gating and perspective correction for the card grading
pipeline.

Two public entry points:
    QualityGate.check(image)  – reject blurry / badly-lit photos early
    align_card(image)         – detect the card contour and warp to a
                                canonical 1000×1400 px frame
"""

import cv2
import numpy as np
from dataclasses import dataclass, field
from typing import Optional, Tuple


# ─────────────────────────────────────────────
#  Data containers
# ─────────────────────────────────────────────

@dataclass
class QualityReport:
    """Result returned by QualityGate.check()."""
    passed: bool
    blur_score: float
    mean_brightness: float
    rejection_reason: Optional[str] = None


@dataclass
class AlignResult:
    """Result returned by align_card()."""
    warped: np.ndarray                  # 1000×1400 BGR image
    debug: np.ndarray                   # original frame annotated with edges/contour
    card_contour: Optional[np.ndarray]  # the four-point polygon found, or None


# ─────────────────────────────────────────────
#  Quality Gate
# ─────────────────────────────────────────────

class QualityGate:
    """
    Rejects images that are unsuitable for grading before any expensive
    processing begins.

    Checks performed
    ----------------
    1. Blur  – Laplacian variance below `blur_threshold` → rejected.
    2. Dark  – mean pixel value below `dark_threshold` → rejected.
    3. Glare – mean pixel value above `glare_threshold` → rejected.
    """

    BLUR_THRESHOLD: float = 100.0   # Laplacian variance; higher = sharper
    DARK_THRESHOLD: float = 40.0    # 0-255 mean brightness
    GLARE_THRESHOLD: float = 220.0  # 0-255 mean brightness

    def check(self, image: np.ndarray) -> QualityReport:
        """
        Evaluate an image and return a QualityReport.

        Parameters
        ----------
        image : np.ndarray
            A BGR image loaded with cv2.imread.

        Returns
        -------
        QualityReport
            .passed is True only when every check succeeds.
        """
        if image is None or image.size == 0:
            return QualityReport(
                passed=False,
                blur_score=0.0,
                mean_brightness=0.0,
                rejection_reason="Image is empty or could not be loaded.",
            )

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # ── Blur ──────────────────────────────────────────────────────────
        # Laplacian measures how quickly pixel values change; a blurry image
        # has very gradual changes, so variance stays low.
        blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())

        # ── Brightness ────────────────────────────────────────────────────
        mean_brightness = float(gray.mean())

        if blur_score < self.BLUR_THRESHOLD:
            return QualityReport(
                passed=False,
                blur_score=blur_score,
                mean_brightness=mean_brightness,
                rejection_reason=(
                    f"Image too blurry (score={blur_score:.1f}, "
                    f"threshold={self.BLUR_THRESHOLD})."
                ),
            )

        if mean_brightness < self.DARK_THRESHOLD:
            return QualityReport(
                passed=False,
                blur_score=blur_score,
                mean_brightness=mean_brightness,
                rejection_reason=(
                    f"Image too dark (brightness={mean_brightness:.1f}, "
                    f"min={self.DARK_THRESHOLD})."
                ),
            )

        if mean_brightness > self.GLARE_THRESHOLD:
            return QualityReport(
                passed=False,
                blur_score=blur_score,
                mean_brightness=mean_brightness,
                rejection_reason=(
                    f"Extreme glare detected (brightness={mean_brightness:.1f}, "
                    f"max={self.GLARE_THRESHOLD})."
                ),
            )

        return QualityReport(
            passed=True,
            blur_score=blur_score,
            mean_brightness=mean_brightness,
        )


# ─────────────────────────────────────────────
#  Perspective alignment
# ─────────────────────────────────────────────

# Target output dimensions (portrait, same aspect ratio as a Pokémon card).
WARP_WIDTH: int = 1000
WARP_HEIGHT: int = 1400

# Destination corners in the warped frame (top-left, top-right,
# bottom-right, bottom-left).
_DEST_CORNERS = np.array(
    [
        [0, 0],
        [WARP_WIDTH - 1, 0],
        [WARP_WIDTH - 1, WARP_HEIGHT - 1],
        [0, WARP_HEIGHT - 1],
    ],
    dtype=np.float32,
)


def _order_corners(pts: np.ndarray) -> np.ndarray:
    """
    Sort four points into [top-left, top-right, bottom-right, bottom-left]
    order so the perspective transform is always consistent.

    Parameters
    ----------
    pts : np.ndarray
        Shape (4, 2) array of (x, y) corner coordinates.
    """
    rect = np.zeros((4, 2), dtype=np.float32)

    # Top-left has the smallest sum; bottom-right has the largest.
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]

    # Top-right has the smallest difference; bottom-left has the largest.
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]

    return rect


def align_card(image: np.ndarray) -> AlignResult:
    """
    Detect the card's outline in *image* and warp it into a canonical
    1000×1400 px frame.

    Steps
    -----
    1. Convert to grayscale → Gaussian blur → Canny edge detection.
    2. Find external contours; pick the largest quadrilateral.
    3. Apply a perspective transform (four-point warp).
    4. If no card is found, return the centre-cropped image with a warning.

    Parameters
    ----------
    image : np.ndarray
        A BGR image (ideally quality-gate–approved).

    Returns
    -------
    AlignResult
        .warped  – the 1000×1400 corrected card image.
        .debug   – the original image annotated with detected edges/contour.
        .card_contour – the four-point polygon, or None if detection failed.
    """
    if image is None or image.size == 0:
        raise ValueError("align_card received an empty image.")

    debug = image.copy()
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # ── Pre-processing ────────────────────────────────────────────────────
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    # Canny with auto-thresholds derived from the median pixel value.
    median = float(np.median(blurred))
    sigma = 0.33
    lower = max(0, int((1.0 - sigma) * median))
    upper = min(255, int((1.0 + sigma) * median))
    edges = cv2.Canny(blurred, lower, upper)

    # Dilate edges slightly so thin lines connect into closed shapes.
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    edges = cv2.dilate(edges, kernel, iterations=1)

    # Save edge map onto the debug image as a semi-transparent overlay.
    edge_overlay = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
    cv2.addWeighted(edge_overlay, 0.4, debug, 0.6, 0, debug)

    # ── Contour detection ─────────────────────────────────────────────────
    contours, _ = cv2.findContours(
        edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    card_contour = _find_card_contour(contours, image.shape)

    # ── Perspective warp ──────────────────────────────────────────────────
    if card_contour is not None:
        cv2.drawContours(debug, [card_contour], -1, (0, 255, 0), 3)

        src_corners = _order_corners(
            card_contour.reshape(4, 2).astype(np.float32)
        )
        M = cv2.getPerspectiveTransform(src_corners, _DEST_CORNERS)
        warped = cv2.warpPerspective(image, M, (WARP_WIDTH, WARP_HEIGHT))
    else:
        # Fallback: centre-crop the image to the target aspect ratio so the
        # pipeline can still produce an output (with a degraded score).
        warped = _centre_crop(image)

    return AlignResult(warped=warped, debug=debug, card_contour=card_contour)


# ─────────────────────────────────────────────
#  Internal helpers
# ─────────────────────────────────────────────

def _find_card_contour(
    contours: Tuple, image_shape: Tuple[int, ...]
) -> Optional[np.ndarray]:
    """
    Return the largest quadrilateral contour that plausibly represents a
    trading card, or None if none qualifies.

    A candidate must:
    • Approximate to exactly 4 vertices.
    • Cover at least 10 % of the total image area (ignores tiny specks).
    • Have an aspect ratio between 0.5 and 1.0 (portrait-ish rectangle).
    """
    h, w = image_shape[:2]
    image_area = h * w
    min_area = image_area * 0.10

    best = None
    best_area = 0.0

    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < min_area:
            continue

        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)

        if len(approx) != 4:
            continue

        x, y, cw, ch = cv2.boundingRect(approx)
        if ch == 0:
            continue
        aspect = cw / ch
        if not (0.5 <= aspect <= 1.0):
            continue

        if area > best_area:
            best_area = area
            best = approx

    return best


def _centre_crop(image: np.ndarray) -> np.ndarray:
    """
    Fallback: resize/crop the image to WARP_WIDTH×WARP_HEIGHT while
    preserving the centre of the frame.
    """
    h, w = image.shape[:2]
    target_ratio = WARP_WIDTH / WARP_HEIGHT
    current_ratio = w / h

    if current_ratio > target_ratio:
        # Image is too wide – crop horizontally.
        new_w = int(h * target_ratio)
        x_start = (w - new_w) // 2
        cropped = image[:, x_start : x_start + new_w]
    else:
        # Image is too tall – crop vertically.
        new_h = int(w / target_ratio)
        y_start = (h - new_h) // 2
        cropped = image[y_start : y_start + new_h, :]

    return cv2.resize(cropped, (WARP_WIDTH, WARP_HEIGHT), interpolation=cv2.INTER_AREA)

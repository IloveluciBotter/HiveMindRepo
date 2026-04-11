"""
Computer-vision helpers: quality gating, blur detection, and card alignment.

Uses Laplacian variance for blur, simple brightness checks for glare/darkness,
and Canny contours plus perspective warp to straighten the card.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

import cv2
import numpy as np


# Fixed output size (width x height), vertical portrait.
WARP_W = 1000
WARP_H = 1400

# Blur rejection: Laplacian variance below this is considered too blurry.
LAPLACIAN_VARIANCE_THRESHOLD = 100.0

# Brightness gate on V channel (0-255): outside this range = extreme dark/glare.
BRIGHTNESS_MIN = 35
BRIGHTNESS_MAX = 245


class QualityGate:
    """
    Reject images that are too blurry or have extreme under/over exposure.

    Blur is measured with Laplacian variance on a grayscale image (higher = sharper).
    Exposure uses mean value (V) from HSV on the full image.
    """

    def __init__(
        self,
        blur_threshold: float = LAPLACIAN_VARIANCE_THRESHOLD,
        brightness_min: int = BRIGHTNESS_MIN,
        brightness_max: int = BRIGHTNESS_MAX,
    ) -> None:
        self.blur_threshold = blur_threshold
        self.brightness_min = brightness_min
        self.brightness_max = brightness_max

    def laplacian_variance(self, gray: np.ndarray) -> float:
        """Return variance of the Laplacian (focus measure)."""
        if gray.ndim != 2:
            raise ValueError("laplacian_variance expects a single-channel image.")
        lap = cv2.Laplacian(gray, cv2.CV_64F)
        return float(lap.var())

    def mean_brightness_v(self, bgr: np.ndarray) -> float:
        """Mean V channel (brightness) in HSV space, 0-255."""
        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
        return float(np.mean(hsv[:, :, 2]))

    def check(self, bgr: np.ndarray) -> Tuple[bool, str, float]:
        """
        Run all quality checks.

        Returns:
            (passed, reason_message, blur_score)
        """
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        blur_score = self.laplacian_variance(gray)

        if blur_score < self.blur_threshold:
            return (
                False,
                f"Image too blurry (Laplacian variance {blur_score:.1f} < {self.blur_threshold}).",
                blur_score,
            )

        v_mean = self.mean_brightness_v(bgr)
        if v_mean < self.brightness_min:
            return (
                False,
                f"Image too dark (mean V={v_mean:.1f} < {self.brightness_min}).",
                blur_score,
            )
        if v_mean > self.brightness_max:
            return (
                False,
                f"Possible extreme glare/overexposure (mean V={v_mean:.1f} > {self.brightness_max}).",
                blur_score,
            )

        return True, "OK", blur_score


@dataclass
class AlignmentResult:
    """Outcome of card detection and perspective warp."""

    warped: np.ndarray | None
    edges_debug: np.ndarray
    success: bool
    message: str


def _order_quad_points(pts: np.ndarray) -> np.ndarray:
    """Order four points as: top-left, top-right, bottom-right, bottom-left."""
    rect = np.zeros((4, 2), dtype=np.float32)
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect


def _largest_quad_contour(
    gray: np.ndarray,
    min_area_ratio: float = 0.15,
) -> np.ndarray | None:
    """
    Find the largest quadrilateral contour (candidate card outline) using Canny + contours.
    """
    h, w = gray.shape[:2]
    img_area = float(h * w)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150)
    kernel = np.ones((3, 3), np.uint8)
    edges = cv2.dilate(edges, kernel, iterations=1)

    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    best = None
    best_area = 0.0

    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < min_area_ratio * img_area:
            continue
        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)
        if len(approx) == 4 and cv2.isContourConvex(approx):
            if area > best_area:
                best_area = area
                best = approx.reshape(4, 2).astype(np.float32)

    return best


def align_card(bgr: np.ndarray) -> AlignmentResult:
    """
    Detect the card with Canny edges and contours, then warp to WARP_W x WARP_H.

    If no suitable quadrilateral is found, returns success=False and message explains why.
    """
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150)
    kernel = np.ones((3, 3), np.uint8)
    edges_dilated = cv2.dilate(edges, kernel, iterations=1)

    quad = _largest_quad_contour(gray)
    if quad is None:
        # Still return edge visualization for debugging
        edges_bgr = cv2.cvtColor(edges_dilated, cv2.COLOR_GRAY2BGR)
        return AlignmentResult(
            warped=None,
            edges_debug=edges_bgr,
            success=False,
            message="No card-like quadrilateral contour was detected (Canny + contours).",
        )

    rect = _order_quad_points(quad)
    dst = np.array(
        [
            [0, 0],
            [WARP_W - 1, 0],
            [WARP_W - 1, WARP_H - 1],
            [0, WARP_H - 1],
        ],
        dtype=np.float32,
    )
    matrix = cv2.getPerspectiveTransform(rect, dst)
    warped = cv2.warpPerspective(bgr, matrix, (WARP_W, WARP_H))

    # Debug image: show detected edges and polygon overlay on a copy of the original
    debug = bgr.copy()
    cv2.polylines(debug, [quad.astype(np.int32).reshape(-1, 1, 2)], True, (0, 255, 0), 3)
    overlay_edges = cv2.cvtColor(edges_dilated, cv2.COLOR_GRAY2BGR)
    # Resize overlay to match if needed (same size as input)
    if overlay_edges.shape[:2] != debug.shape[:2]:
        overlay_edges = cv2.resize(overlay_edges, (debug.shape[1], debug.shape[0]))
    combined = cv2.addWeighted(debug, 0.7, overlay_edges, 0.5, 0)

    return AlignmentResult(
        warped=warped,
        edges_debug=combined,
        success=True,
        message="Card aligned successfully.",
    )

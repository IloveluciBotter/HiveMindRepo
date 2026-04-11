"""Computer vision utilities for Pokémon card intake and alignment."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple

import cv2
import numpy as np


@dataclass
class QualityGate:
    """Simple gatekeeper checks for blur and exposure quality."""

    blur_threshold: float = 100.0
    darkness_mean_threshold: float = 40.0
    brightness_mean_threshold: float = 220.0
    glare_pixel_threshold: float = 0.20
    darkness_pixel_threshold: float = 0.20

    def blur_score(self, image: np.ndarray) -> float:
        """Return Laplacian variance; higher means sharper."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        return float(laplacian.var())

    def exposure_stats(self, image: np.ndarray) -> Dict[str, float]:
        """Return simple brightness and clipping statistics."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        mean_intensity = float(np.mean(gray))
        bright_ratio = float(np.mean(gray >= 245))
        dark_ratio = float(np.mean(gray <= 10))
        return {
            "mean_intensity": mean_intensity,
            "bright_ratio": bright_ratio,
            "dark_ratio": dark_ratio,
        }

    def evaluate(self, image: np.ndarray) -> Dict[str, float | bool | str]:
        """Evaluate image quality and return decision + metrics."""
        blur_value = self.blur_score(image)
        exposure = self.exposure_stats(image)

        if blur_value < self.blur_threshold:
            return {
                "passed": False,
                "blur_score": blur_value,
                "reason": "Image rejected: too blurry.",
                **exposure,
            }

        if (
            exposure["mean_intensity"] < self.darkness_mean_threshold
            or exposure["dark_ratio"] > self.darkness_pixel_threshold
        ):
            return {
                "passed": False,
                "blur_score": blur_value,
                "reason": "Image rejected: too dark.",
                **exposure,
            }

        if (
            exposure["mean_intensity"] > self.brightness_mean_threshold
            or exposure["bright_ratio"] > self.glare_pixel_threshold
        ):
            return {
                "passed": False,
                "blur_score": blur_value,
                "reason": "Image rejected: glare / overexposure detected.",
                **exposure,
            }

        return {
            "passed": True,
            "blur_score": blur_value,
            "reason": "ok",
            **exposure,
        }


def _order_quad_points(points: np.ndarray) -> np.ndarray:
    """Return points ordered as top-left, top-right, bottom-right, bottom-left."""
    rect = np.zeros((4, 2), dtype=np.float32)
    summed = points.sum(axis=1)
    diff = np.diff(points, axis=1)

    rect[0] = points[np.argmin(summed)]
    rect[2] = points[np.argmax(summed)]
    rect[1] = points[np.argmin(diff)]
    rect[3] = points[np.argmax(diff)]
    return rect


def _find_card_contour(edge_map: np.ndarray, image_area: int) -> np.ndarray:
    """Find the most likely card contour as a quadrilateral."""
    contours, _ = cv2.findContours(edge_map, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        raise ValueError("No contours found; card could not be detected.")

    contours = sorted(contours, key=cv2.contourArea, reverse=True)
    expected_aspect = 1000.0 / 1400.0
    best_quad = None
    best_score = -1.0

    for contour in contours:
        area = cv2.contourArea(contour)
        if area < image_area * 0.15:
            continue
        perimeter = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.02 * perimeter, True)
        if len(approx) == 4:
            x, y, w, h = cv2.boundingRect(approx)
            if h <= 0:
                continue
            aspect = float(w) / float(h)
            aspect_score = 1.0 - min(abs(aspect - expected_aspect), 1.0)
            area_score = min(area / float(image_area), 1.0)
            score = (0.65 * area_score) + (0.35 * aspect_score)
            if score > best_score:
                best_score = score
                best_quad = approx.reshape(4, 2).astype(np.float32)

    if best_quad is not None:
        return best_quad

    best = contours[0]
    area = cv2.contourArea(best)
    if area < image_area * 0.15:
        raise ValueError("Largest contour is too small; card could not be isolated.")

    rect = cv2.minAreaRect(best)
    box = cv2.boxPoints(rect)
    return box.astype(np.float32)


def align_card(
    image: np.ndarray,
    debug_path: str = "processed_debug.jpg",
    final_path: str = "final_scan.jpg",
    output_size: Tuple[int, int] = (1000, 1400),
) -> np.ndarray:
    """
    Detect card boundary and warp it to a fixed 1000x1400 frame.

    Saves:
      - processed_debug.jpg: edge map + selected contour
      - final_scan.jpg: perspective-corrected card image
    """
    if image is None or image.size == 0:
        raise ValueError("Invalid image array: input is empty.")

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    denoised = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(denoised, 60, 170)
    kernel = np.ones((5, 5), np.uint8)
    closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=2)

    debug = cv2.cvtColor(closed, cv2.COLOR_GRAY2BGR)

    height, width = gray.shape
    try:
        card_points = _find_card_contour(closed, image_area=height * width)
    except ValueError as exc:
        cv2.imwrite(debug_path, debug)
        raise ValueError(f"Card detection failed during alignment: {exc}") from exc

    ordered = _order_quad_points(card_points)

    target_w, target_h = output_size
    destination = np.array(
        [
            [0, 0],
            [target_w - 1, 0],
            [target_w - 1, target_h - 1],
            [0, target_h - 1],
        ],
        dtype=np.float32,
    )

    matrix = cv2.getPerspectiveTransform(ordered, destination)
    warped = cv2.warpPerspective(image, matrix, (target_w, target_h))

    cv2.polylines(debug, [card_points.astype(np.int32)], True, (0, 255, 0), 3)
    cv2.imwrite(debug_path, debug)
    cv2.imwrite(final_path, warped)

    return warped

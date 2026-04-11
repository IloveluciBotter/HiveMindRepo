"""Scoring utilities for centering and condition estimation."""

from __future__ import annotations

from typing import Dict, Tuple

import cv2
import numpy as np


def _smooth_1d(signal: np.ndarray, ksize: int = 21) -> np.ndarray:
    """Smooth a 1D signal with a simple box filter."""
    kernel = np.ones(ksize, dtype=np.float32) / float(ksize)
    return np.convolve(signal, kernel, mode="same")


def _detect_inner_border(card_image: np.ndarray) -> Tuple[int, int, int, int]:
    """
    Detect inner frame border (left, right, top, bottom) using gradient profiles.

    This assumes card image is already perspective-aligned to a vertical frame.
    """
    gray = cv2.cvtColor(card_image, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    h, w = gray.shape

    # Ignore small margins to reduce outer-edge dominance.
    y0, y1 = int(0.08 * h), int(0.92 * h)
    x0, x1 = int(0.08 * w), int(0.92 * w)

    grad_x = np.abs(cv2.Sobel(gray[y0:y1, :], cv2.CV_32F, 1, 0, ksize=3))
    grad_y = np.abs(cv2.Sobel(gray[:, x0:x1], cv2.CV_32F, 0, 1, ksize=3))

    col_profile = _smooth_1d(np.mean(grad_x, axis=0), ksize=21)
    row_profile = _smooth_1d(np.mean(grad_y, axis=1), ksize=21)

    left_window = (int(0.02 * w), int(0.28 * w))
    right_window = (int(0.72 * w), int(0.98 * w))
    top_window = (int(0.02 * h), int(0.22 * h))
    bottom_window = (int(0.78 * h), int(0.98 * h))

    left = int(np.argmax(col_profile[left_window[0] : left_window[1]]) + left_window[0])
    right = int(np.argmax(col_profile[right_window[0] : right_window[1]]) + right_window[0])
    top = int(np.argmax(row_profile[top_window[0] : top_window[1]]) + top_window[0])
    bottom = int(
        np.argmax(row_profile[bottom_window[0] : bottom_window[1]]) + bottom_window[0]
    )

    if right <= left or bottom <= top:
        raise ValueError("Inner artwork border detection failed.")

    return left, right, top, bottom


def calculate_centering(card_image: np.ndarray) -> Dict[str, float]:
    """
    Calculate centering ratios using edge-to-inner-border distances.

    Formula:
      horizontal = (L / (L + R)) * 100
      vertical   = (T / (T + B)) * 100
    """
    if card_image is None or card_image.size == 0:
        raise ValueError("Invalid card image supplied for centering.")

    h, w = card_image.shape[:2]
    left, right, top, bottom = _detect_inner_border(card_image)

    l_dist = float(left)
    r_dist = float((w - 1) - right)
    t_dist = float(top)
    b_dist = float((h - 1) - bottom)

    if (l_dist + r_dist) <= 0 or (t_dist + b_dist) <= 0:
        raise ValueError("Centering distances are invalid.")

    horizontal = (l_dist / (l_dist + r_dist)) * 100.0
    vertical = (t_dist / (t_dist + b_dist)) * 100.0

    return {
        "centering_ratio_horizontal": round(horizontal, 1),
        "centering_ratio_vertical": round(vertical, 1),
        "inner_border_left_px": round(l_dist, 1),
        "inner_border_right_px": round(r_dist, 1),
        "inner_border_top_px": round(t_dist, 1),
        "inner_border_bottom_px": round(b_dist, 1),
    }


def detect_edge_wear(card_image: np.ndarray, border_pct: float = 0.05) -> float:
    """
    Estimate card condition from white/silver wear pixels near outer edges.

    A larger fraction of bright low-saturation pixels in outer 5% border
    implies more visible edge wear, lowering the final condition score.
    """
    if card_image is None or card_image.size == 0:
        raise ValueError("Invalid card image supplied for edge wear detection.")

    h, w = card_image.shape[:2]
    border_x = max(1, int(w * border_pct))
    border_y = max(1, int(h * border_pct))

    mask = np.zeros((h, w), dtype=np.uint8)
    mask[:border_y, :] = 255
    mask[h - border_y :, :] = 255
    mask[:, :border_x] = 255
    mask[:, w - border_x :] = 255

    hsv = cv2.cvtColor(card_image, cv2.COLOR_BGR2HSV)
    # White/silver-like pixels are usually bright and low saturation.
    wear_pixels = (hsv[:, :, 2] >= 200) & (hsv[:, :, 1] <= 60)
    border_pixels = mask == 255

    total_border = int(np.count_nonzero(border_pixels))
    if total_border == 0:
        raise ValueError("Border mask is empty; cannot score condition.")

    wear_count = int(np.count_nonzero(wear_pixels & border_pixels))
    wear_ratio = wear_count / float(total_border)

    # Linear mapping; tune constants with real labeled samples later.
    condition = max(0.0, min(100.0, 100.0 - (wear_ratio * 300.0)))
    return round(condition, 1)

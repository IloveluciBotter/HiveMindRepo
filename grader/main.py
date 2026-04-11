"""
main.py – Pokémon Card Grader entry point.

Usage
-----
    python main.py path/to/card_photo.jpg

Outputs (written next to the input file, or in the current directory)
----------------------------------------------------------------------
    processed_debug.jpg   – original photo with detected edges/contour overlaid
    final_scan.jpg        – perspective-corrected 1000×1400 px card image

Printed to stdout
-----------------
    JSON object with:
        blur_score                    (float)
        centering_ratio_horizontal    (float, 50 = perfect)
        centering_ratio_vertical      (float, 50 = perfect)
        estimated_condition_score     (float, 0–100)
"""

import json
import sys
import os
import cv2

from core.vision import QualityGate, align_card
from core.grader import measure_centering, detect_edge_wear


def grade_card(image_path: str) -> dict:
    """
    Full grading pipeline for a single card photo.

    Parameters
    ----------
    image_path : str
        Path to the input image file (JPEG, PNG, etc.)

    Returns
    -------
    dict
        Keys: blur_score, centering_ratio_horizontal,
              centering_ratio_vertical, estimated_condition_score.

    Raises
    ------
    FileNotFoundError  – if image_path does not exist.
    RuntimeError       – if the image fails the quality gate.
    """
    # ── Load ──────────────────────────────────────────────────────────────
    if not os.path.isfile(image_path):
        raise FileNotFoundError(f"No file found at: {image_path}")

    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(
            f"OpenCV could not decode the image at: {image_path}\n"
            "Check that it is a valid JPEG/PNG file."
        )

    # ── Quality gate ──────────────────────────────────────────────────────
    gate = QualityGate()
    quality = gate.check(image)

    if not quality.passed:
        raise RuntimeError(
            f"Image rejected by quality gate: {quality.rejection_reason}"
        )

    # ── Perspective alignment ─────────────────────────────────────────────
    align_result = align_card(image)

    if align_result.card_contour is None:
        print(
            "WARNING: Card outline not detected – using centre-crop fallback. "
            "Centering and condition scores may be less accurate.",
            file=sys.stderr,
        )

    # ── Save debug and final images ───────────────────────────────────────
    base_dir = os.path.dirname(os.path.abspath(image_path))
    debug_path = os.path.join(base_dir, "processed_debug.jpg")
    final_path = os.path.join(base_dir, "final_scan.jpg")

    cv2.imwrite(debug_path, align_result.debug)
    cv2.imwrite(final_path, align_result.warped)

    print(f"Debug image saved  → {debug_path}", file=sys.stderr)
    print(f"Final scan saved   → {final_path}", file=sys.stderr)

    # ── Grading ───────────────────────────────────────────────────────────
    h_ratio, v_ratio = measure_centering(align_result.warped)
    condition = detect_edge_wear(align_result.warped)

    result = {
        "blur_score": round(quality.blur_score, 2),
        "centering_ratio_horizontal": h_ratio,
        "centering_ratio_vertical": v_ratio,
        "estimated_condition_score": condition,
    }

    return result


# ─────────────────────────────────────────────
#  CLI entry point
# ─────────────────────────────────────────────

def main() -> None:
    if len(sys.argv) < 2:
        print(
            "Usage: python main.py <path_to_card_image>",
            file=sys.stderr,
        )
        sys.exit(1)

    image_path = sys.argv[1]

    try:
        result = grade_card(image_path)
        print(json.dumps(result, indent=2))
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

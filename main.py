#!/usr/bin/env python3
"""
Entry point: quality gate -> align card -> centering & condition -> JSON + saved images.

Saves ``processed_debug.jpg`` (detected edges / overlay) and ``final_scan.jpg`` (warped card).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import cv2

from core.grader import detect_edge_wear, measure_centering
from core.vision import QualityGate, align_card


def run_pipeline(
    image_path: Path,
    output_dir: Path,
    verbose: bool = False,
) -> dict[str, Any]:
    """
    Run the full grading flow.

    Returns a JSON-serializable dict with blur_score, centering_ratio_horizontal,
    centering_ratio_vertical, and estimated_condition_score. If ``verbose`` is True,
    adds quality/alignment notes and messages.
    """
    if not image_path.is_file():
        raise FileNotFoundError(f"Input image not found: {image_path}")

    bgr = cv2.imread(str(image_path))
    if bgr is None:
        raise ValueError(f"Could not read image: {image_path}")

    output_dir.mkdir(parents=True, exist_ok=True)
    debug_path = output_dir / "processed_debug.jpg"
    final_path = output_dir / "final_scan.jpg"

    gate = QualityGate()
    passed, reason, blur_score = gate.check(bgr)

    result: dict[str, Any] = {
        "blur_score": round(blur_score, 4),
        "centering_ratio_horizontal": None,
        "centering_ratio_vertical": None,
        "estimated_condition_score": None,
    }
    if verbose:
        result["_quality_passed"] = passed
        result["_quality_message"] = reason

    if not passed:
        # Still write a debug frame (original) so every run produces both files.
        cv2.imwrite(str(debug_path), bgr)
        cv2.imwrite(str(final_path), bgr)
        if verbose:
            result["_alignment_message"] = "Skipped (quality gate failed)."
        return result

    alignment = align_card(bgr)
    cv2.imwrite(str(debug_path), alignment.edges_debug)

    if not alignment.success or alignment.warped is None:
        if verbose:
            result["_alignment_message"] = alignment.message
        cv2.imwrite(str(final_path), bgr)
        return result

    warped = alignment.warped
    cv2.imwrite(str(final_path), warped)

    ch, cv_, centering_note = measure_centering(warped)
    cond, wear_note = detect_edge_wear(warped)

    result["centering_ratio_horizontal"] = None if ch != ch else round(float(ch), 4)  # NaN check
    result["centering_ratio_vertical"] = None if cv_ != cv_ else round(float(cv_), 4)
    result["estimated_condition_score"] = round(cond, 4)
    if verbose:
        result["_centering_note"] = centering_note
        result["_condition_note"] = wear_note
        result["_alignment_message"] = alignment.message

    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Pokémon card grading pipeline (scaffold).")
    parser.add_argument(
        "image",
        type=Path,
        help="Path to input photo of a card.",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=Path("."),
        help="Directory for processed_debug.jpg and final_scan.jpg (default: current dir).",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Include diagnostic fields (prefixed with _) in JSON output.",
    )
    args = parser.parse_args()

    try:
        out = run_pipeline(args.image, args.output_dir, verbose=args.verbose)
        print(json.dumps(out, indent=2))
    except (FileNotFoundError, ValueError) as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

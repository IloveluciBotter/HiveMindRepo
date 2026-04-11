"""Entry point for Pokémon card preprocessing + preliminary grading."""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict

import cv2

from core.grader import calculate_centering, detect_edge_wear
from core.vision import QualityGate, align_card


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run card quality checks, alignment, and basic grading."
    )
    parser.add_argument("--image", required=True, help="Path to raw card photo.")
    parser.add_argument(
        "--output-dir",
        default=".",
        help="Directory where processed_debug.jpg and final_scan.jpg are saved.",
    )
    return parser


def run_pipeline(image_path: str, output_dir: str = ".") -> Dict[str, Any]:
    """Run end-to-end intake flow and return JSON-compatible metrics."""
    debug_path = os.path.join(output_dir, "processed_debug.jpg")
    final_path = os.path.join(output_dir, "final_scan.jpg")

    os.makedirs(output_dir, exist_ok=True)

    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"Unable to read image: {image_path}")

    gate = QualityGate()
    gate_result = gate.evaluate(image)
    blur_score = round(float(gate_result["blur_score"]), 2)

    if not gate_result["passed"]:
        raise ValueError(str(gate_result["reason"]))

    aligned = align_card(image, debug_path=debug_path, final_path=final_path)
    centering = calculate_centering(aligned)
    condition_score = detect_edge_wear(aligned)

    return {
        "blur_score": blur_score,
        "centering_ratio_horizontal": centering["centering_ratio_horizontal"],
        "centering_ratio_vertical": centering["centering_ratio_vertical"],
        "estimated_condition_score": condition_score,
    }


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    result: Dict[str, Any] = {
        "blur_score": None,
        "centering_ratio_horizontal": None,
        "centering_ratio_vertical": None,
        "estimated_condition_score": None,
    }

    try:
        result = run_pipeline(args.image, args.output_dir)
        print(json.dumps(result, indent=2))
        return 0
    except Exception as exc:  # pylint: disable=broad-except
        error_result = {**result, "error": str(exc)}
        print(json.dumps(error_result, indent=2))
        return 1


if __name__ == "__main__":
    sys.exit(main())

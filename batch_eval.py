import argparse
import os
from typing import Dict, List

import cv2

from omr_eval import load_answer_key, batch_evaluate_folder, EvaluationConfig


def main() -> None:
    parser = argparse.ArgumentParser(description="Batch evaluate OMR sheets in a folder")
    parser.add_argument("folder", help="Folder containing sheet images")
    parser.add_argument("set_id", help="Exam set identifier (e.g., A, B)")
    parser.add_argument("answer_key", help="Answer key file (JSON/CSV)")
    parser.add_argument("--out", default="results.csv", help="Output CSV path")
    args = parser.parse_args()

    if not os.path.isdir(args.folder):
        raise SystemExit(f"Folder not found: {args.folder}")
    if not os.path.exists(args.answer_key):
        raise SystemExit(f"Answer key not found: {args.answer_key}")

    ak = load_answer_key(args.answer_key)
    if args.set_id not in ak:
        raise SystemExit(f"Set '{args.set_id}' not present in answer key")

    cfg = EvaluationConfig()
    batch_evaluate_folder(args.folder, args.set_id, ak, cfg, args.out)
    print(f"Saved results to {args.out} and artifacts/ directory.")


if __name__ == "__main__":
    main()



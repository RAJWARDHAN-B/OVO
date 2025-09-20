"""
OMR evaluation core utilities.

This module provides functions to:
- Load answer keys (JSON or CSV)
- Preprocess and rectify OMR sheet images
- Detect bubble grid and infer marked answers (A–E)
- Score responses against answer keys with per-subject breakdowns
- Save audit artifacts (rectified image, overlay, JSON results)

Assumptions for MVP (configurable):
- 100 questions, 5 choices (A–E), 5 subjects × 20 questions each
- Bubble positions form a grid; detection is based on contour filtering

Note: This is a classical CV approach intended to work on typical OMR sheets.
For challenging cases, you may extend with ML-based classification of marks.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict, field
from typing import Dict, List, Optional, Tuple, Any

import cv2
import numpy as np


CHOICES = ["A", "B", "C", "D", "E"]


@dataclass
class SubjectConfig:
    subject_names: List[str]
    questions_per_subject: int

    @staticmethod
    def default() -> "SubjectConfig":
        return SubjectConfig(
            subject_names=[
                "Subject 1",
                "Subject 2",
                "Subject 3",
                "Subject 4",
                "Subject 5",
            ],
            questions_per_subject=20,
        )


@dataclass
class EvaluationConfig:
    expected_questions: int = 100
    expected_choices: int = 5
    min_bubble_area_ratio: float = 5e-6  # relative to image area
    max_bubble_area_ratio: float = 2e-3  # relative to image area
    row_merge_tolerance: float = 0.02  # fraction of image height
    selection_threshold_ratio: float = 0.55  # relative to max filled pixel count in a row
    min_selection_margin: float = 0.10  # winner vs runner-up margin (fraction of winner)
    save_artifacts_dir: str = "artifacts"
    subject_config: SubjectConfig = field(default_factory=SubjectConfig.default)


@dataclass
class QuestionResult:
    question_index: int
    selected_option: Optional[str]
    confidence: float
    is_ambiguous: bool
    is_blank: bool
    correct_option: Optional[str]
    is_correct: Optional[bool]


@dataclass
class SheetResult:
    sheet_id: str
    sheet_set: str
    per_question: List[QuestionResult]
    per_subject_scores: Dict[str, int]
    total_score: int
    ambiguous_count: int
    blank_count: int


def _order_points(pts: np.ndarray) -> np.ndarray:
    # Orders four points in tl, tr, br, bl order
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]  # tl
    rect[2] = pts[np.argmax(s)]  # br
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]  # tr
    rect[3] = pts[np.argmax(diff)]  # bl
    return rect


def _four_point_transform(image: np.ndarray, pts: np.ndarray) -> np.ndarray:
    rect = _order_points(pts)
    (tl, tr, br, bl) = rect
    width_a = np.linalg.norm(br - bl)
    width_b = np.linalg.norm(tr - tl)
    max_width = int(max(width_a, width_b))

    height_a = np.linalg.norm(tr - br)
    height_b = np.linalg.norm(tl - bl)
    max_height = int(max(height_a, height_b))

    dst = np.array(
        [[0, 0], [max_width - 1, 0], [max_width - 1, max_height - 1], [0, max_height - 1]],
        dtype="float32",
    )
    M = cv2.getPerspectiveTransform(rect, dst)
    warped = cv2.warpPerspective(image, M, (max_width, max_height))
    return warped


def _find_document_contour(image: np.ndarray) -> Optional[np.ndarray]:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edged = cv2.Canny(blurred, 50, 150)
    contours, _ = cv2.findContours(edged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    contours = sorted(contours, key=cv2.contourArea, reverse=True)
    for c in contours:
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)
        if len(approx) == 4:
            return approx.reshape(4, 2)
    return None


def _binarize(image: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    # Contrast normalization
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    gray = clahe.apply(gray)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    adaptive = cv2.adaptiveThreshold(
        blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 25, 10
    )
    fg_ratio = float(cv2.countNonZero(adaptive)) / float(adaptive.size)
    # Fallback to Otsu if adaptive is degenerate
    if fg_ratio < 0.02 or fg_ratio > 0.98:
        _, adaptive = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    adaptive = cv2.morphologyEx(adaptive, cv2.MORPH_OPEN, kernel, iterations=1)
    adaptive = cv2.morphologyEx(adaptive, cv2.MORPH_CLOSE, kernel, iterations=1)
    return adaptive


def _extract_bubbles(binary_img: np.ndarray, config: EvaluationConfig) -> List[Tuple[np.ndarray, Tuple[int, int, int, int]]]:
    contours, _ = cv2.findContours(binary_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    h, w = binary_img.shape[:2]
    min_area = config.min_bubble_area_ratio * (h * w)
    max_area = config.max_bubble_area_ratio * (h * w)
    candidates: List[Tuple[np.ndarray, Tuple[int, int, int, int]]] = []
    for c in contours:
        area = cv2.contourArea(c)
        if area < min_area or area > max_area:
            continue
        x, y, bw, bh = cv2.boundingRect(c)
        aspect = bw / float(bh if bh != 0 else 1)
        if aspect < 0.5 or aspect > 1.8:  # roughly circular/square/rounded squares
            continue
        # circularity check
        perimeter = cv2.arcLength(c, True)
        if perimeter == 0:
            continue
        circularity = 4 * np.pi * area / (perimeter * perimeter)
        if circularity < 0.3:  # allow less perfect circles
            continue
        candidates.append((c, (x, y, bw, bh)))
    return candidates


def _group_bubbles_into_rows(
    bubbles: List[Tuple[np.ndarray, Tuple[int, int, int, int]]], image_height: int, config: EvaluationConfig
) -> List[List[Tuple[np.ndarray, Tuple[int, int, int, int]]]]:
    if not bubbles:
        return []
    # Sort by y (top to bottom)
    bubbles_sorted = sorted(bubbles, key=lambda b: b[1][1])
    rows: List[List[Tuple[np.ndarray, Tuple[int, int, int, int]]]] = []
    row: List[Tuple[np.ndarray, Tuple[int, int, int, int]]] = []
    tol = config.row_merge_tolerance * image_height
    current_y: Optional[float] = None
    for b in bubbles_sorted:
        _, (x, y, bw, bh) = b
        cy = y + bh / 2.0
        if current_y is None:
            current_y = cy
            row = [b]
            continue
        if abs(cy - current_y) <= tol:
            row.append(b)
        else:
            # finalize previous row
            row = sorted(row, key=lambda bb: bb[1][0])  # sort left-to-right within row
            rows.append(row)
            row = [b]
            current_y = cy
    if row:
        row = sorted(row, key=lambda bb: bb[1][0])
        rows.append(row)
    return rows


def _select_option_for_row(
    row: List[Tuple[np.ndarray, Tuple[int, int, int, int]]], binary_img: np.ndarray, config: EvaluationConfig
) -> Tuple[Optional[int], float, bool, bool, List[int]]:
    # Compute filled pixel counts per bubble by masking the binary image
    filled_counts: List[int] = []
    for contour, _bbox in row:
        mask = np.zeros(binary_img.shape, dtype=np.uint8)
        cv2.drawContours(mask, [contour], -1, 255, -1)
        count = int(cv2.countNonZero(cv2.bitwise_and(binary_img, binary_img, mask=mask)))
        filled_counts.append(count)

    max_count = max(filled_counts) if filled_counts else 0
    if max_count <= 0:
        return None, 0.0, False, True, filled_counts

    threshold = config.selection_threshold_ratio * float(max_count)
    above = [i for i, c in enumerate(filled_counts) if c >= threshold]
    if len(above) == 0:
        # Treat as blank if no bubble passes threshold
        return None, 0.0, False, True, filled_counts
    if len(above) > 1:
        # ambiguous (multiple marks)
        # choose the winner for reporting but flag as ambiguous
        winner = int(np.argmax(filled_counts))
        conf = 1.0 if max_count == 0 else (filled_counts[winner] - np.partition(filled_counts, -2)[-2]) / float(max_count)
        return winner, max(0.0, conf), True, False, filled_counts

    winner = above[0]
    # Compute margin vs runner-up
    sorted_counts = sorted(filled_counts, reverse=True)
    runner = sorted_counts[1] if len(sorted_counts) > 1 else 0
    margin = 0.0 if max_count == 0 else (max_count - runner) / float(max_count)
    is_ambiguous = margin < config.min_selection_margin
    confidence = margin
    return winner, max(0.0, confidence), is_ambiguous, False, filled_counts


def _compute_subject_scores(
    per_question: List[QuestionResult], subject_config: SubjectConfig
) -> Dict[str, int]:
    scores: Dict[str, int] = {}
    qps = subject_config.questions_per_subject
    for s_idx, name in enumerate(subject_config.subject_names):
        start = s_idx * qps
        end = start + qps
        correct = sum(1 for q in per_question[start:end] if q.is_correct)
        scores[name] = int(correct)
    return scores


def _parse_subject_grid_answer_csv(path: str) -> Optional[List[str]]:
    import csv
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = [r for r in reader if any(c.strip() for c in r)]
    if not rows:
        return None
    # Expect 5 columns (subjects); header present, 20 rows of answers like "1 - a"
    header = rows[0]
    if len(header) < 5:
        return None
    cells = rows[1:]
    # Flatten column-wise to 100 answers
    answers: List[str] = []
    for r in range(min(20, len(cells))):
        row = cells[r]
        for c in range(5):
            if c >= len(row):
                val = ""
            else:
                val = row[c]
            ans = _extract_letter_from_cell(val)
            answers.append(ans)
    if len(answers) == 100:
        return answers
    # Some files may include extra rows or spacing; attempt to trim/pad
    if len(answers) > 100:
        return answers[:100]
    return answers + [""] * (100 - len(answers))


def _parse_subject_grid_answer_csv_stream(reader_header: List[str], raw_io) -> Optional[List[str]]:
    import csv
    raw_io.seek(0)
    reader = csv.reader(raw_io)
    rows = [r for r in reader if any(c.strip() for c in r)]
    if not rows:
        return None
    header = rows[0]
    if len(header) < 5:
        return None
    answers: List[str] = []
    for r in range(1, min(21, len(rows))):
        row = rows[r]
        for c in range(5):
            val = row[c] if c < len(row) else ""
            ans = _extract_letter_from_cell(val)
            answers.append(ans)
    if len(answers) == 100:
        return answers
    if len(answers) > 100:
        return answers[:100]
    return answers + [""] * (100 - len(answers))


def _extract_letter_from_cell(cell: str) -> str:
    # cells like "1 - a" or "59 - a,b" (choose first letter) or "81. a"
    s = (cell or "").strip()
    if not s:
        return ""
    # split by comma and take first segment
    first = s.split(",")[0]
    # find last alpha char
    for ch in reversed(first):
        if ch.isalpha():
            return ch.upper()
    return ""


def load_answer_key(path: str) -> Dict[str, List[str]]:
    """
    Load answer keys.

    Supported formats:
    - JSON: {"A": ["B", "C", ...], "B": ["A", ...]}
    - CSV: First row headers: set, q1, q2, ..., q100 (case-insensitive)
           Or long-form rows: set, question, answer (1-based question)
    Returns a dict mapping set_id -> list of answers (length 100).
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Answer key file not found: {path}")

    # If a directory is passed (e.g., sheets/Keys), scan for CSVs like KeySetA.csv, KeySetB.csv
    if os.path.isdir(path):
        results: Dict[str, List[str]] = {}
        for name in os.listdir(path):
            fp = os.path.join(path, name)
            if not os.path.isfile(fp):
                continue
            extn = os.path.splitext(name)[1].lower()
            if extn != ".csv":
                continue
            set_id = None
            base = os.path.splitext(name)[0]
            # Try to extract trailing set letter from filenames like KeySetA.csv
            if base.lower().startswith("keyset") and len(base) >= 7:
                set_id = base[-1].upper()
            else:
                set_id = base.upper()
            parsed = _parse_subject_grid_answer_csv(fp)
            if parsed:
                results[set_id] = parsed
        if not results:
            raise ValueError("No valid answer CSVs found in directory")
        return results

    ext = os.path.splitext(path)[1].lower()
    if ext == ".json":
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        normalized: Dict[str, List[str]] = {}
        for set_id, answers in data.items():
            if not isinstance(answers, list):
                raise ValueError("JSON answer key values must be arrays of answers")
            normalized[set_id] = [str(a).strip().upper() for a in answers]
        return normalized
    elif ext == ".csv":
        import csv

        with open(path, newline="", encoding="utf-8") as f:
            # Peek header to decide format
            import io as _io
            content = f.read()
            f2 = _io.StringIO(content)
            f3 = _io.StringIO(content)
            reader = csv.DictReader(f2)
            fieldnames = [fn.lower() for fn in (reader.fieldnames or [])]
            if "set" in fieldnames and any(fn.startswith("q") for fn in fieldnames):
                # wide format
                results: Dict[str, List[str]] = {}
                for row in reader:
                    set_id = (row.get("set") or row.get("Set") or row.get("SET") or "").strip()
                    if not set_id:
                        continue
                    answers = []
                    for i in range(1, 101):
                        key = f"q{i}"
                        # try different casings
                        val = row.get(key) or row.get(key.upper()) or row.get(key.capitalize())
                        answers.append((val or "").strip().upper())
                    results[set_id] = answers
                return results
            else:
                # Try subject-grid format (5 columns for subjects, 20 rows)
                f3.seek(0)
                res = _parse_subject_grid_answer_csv_stream(reader_header=fieldnames, raw_io=f3)
                if res:
                    # If coming from single file, assume set id from filename stem's last char if present
                    base = os.path.splitext(os.path.basename(path))[0]
                    set_id = base[-1].upper() if base.lower().startswith("keyset") and len(base) >= 7 else base.upper()
                    return {set_id: res}

                # Fallback: long format set,question,answer
                f4 = _io.StringIO(content)
                reader2 = csv.DictReader(f4)
                results_map: Dict[str, Dict[int, str]] = {}
                for row in reader2:
                    set_id = (row.get("set") or "").strip()
                    q_raw = (row.get("question") or row.get("q") or "0").strip()
                    try:
                        qn = int(q_raw)
                    except Exception:
                        qn = 0
                    ans = (row.get("answer") or row.get("ans") or "").strip().upper()
                    if not set_id or qn <= 0:
                        continue
                    results_map.setdefault(set_id, {})[qn] = ans
                normalized: Dict[str, List[str]] = {}
                for sid, mapping in results_map.items():
                    answers = [mapping.get(i, "") for i in range(1, 101)]
                    normalized[sid] = answers
                return normalized
    else:
        raise ValueError("Unsupported answer key format. Use JSON or CSV.")


def evaluate_sheet(
    image_bgr: np.ndarray,
    sheet_id: str,
    sheet_set: str,
    answer_key: Dict[str, List[str]],
    config: Optional[EvaluationConfig] = None,
) -> Tuple[SheetResult, np.ndarray, np.ndarray]:
    """
    Evaluate a single OMR sheet.

    Returns: (result, rectified_image_bgr, overlay_bgr)
    """
    if config is None:
        config = EvaluationConfig()

    if sheet_set not in answer_key:
        raise KeyError(f"Set '{sheet_set}' not found in answer key")
    correct_answers = answer_key[sheet_set]

    # Infer number of choices from answer key (4 if no 'E', else 5)
    def _infer_choices_from_answers(answers: List[str]) -> List[str]:
        used = {a.strip().upper() for a in answers if isinstance(a, str)}
        return ["A", "B", "C", "D", "E"] if "E" in used or len(used) > 4 else ["A", "B", "C", "D"]

    effective_choices = _infer_choices_from_answers(correct_answers)
    expected_choices = len(effective_choices)

    # 1) Rectify document
    doc_contour = _find_document_contour(image_bgr)
    if doc_contour is not None:
        rectified = _four_point_transform(image_bgr, doc_contour.astype(np.float32))
    else:
        rectified = image_bgr.copy()

    # 2) Binarize and find bubbles
    binary = _binarize(rectified)
    bubbles = _extract_bubbles(binary, config)
    rows = _group_bubbles_into_rows(bubbles, binary.shape[0], config)

    # Filter to rows that likely represent answer rows: must have expected_choices bubbles
    answer_rows = [r for r in rows if len(r) == expected_choices]

    # If there are too many/too few rows, attempt best-effort by picking the 100 rows
    if len(answer_rows) < config.expected_questions:
        # Pad with empty rows
        pass
    if len(answer_rows) > config.expected_questions:
        answer_rows = answer_rows[: config.expected_questions]

    per_q: List[QuestionResult] = []
    ambiguous = 0
    blanks = 0

    # Prepare overlay
    overlay = rectified.copy()
    overlay_binary_color = cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)
    overlay = cv2.addWeighted(overlay, 0.8, overlay_binary_color, 0.2, 0)

    # Sort final rows top-to-bottom again for safety
    answer_rows = sorted(answer_rows, key=lambda r: sum(bb[1][1] for bb in r) / len(r))

    for q_idx in range(config.expected_questions):
        if q_idx < len(answer_rows):
            row = answer_rows[q_idx]
            chosen_idx, conf, is_amb, is_blank, counts = _select_option_for_row(row, binary, config)
            selected = (
                effective_choices[chosen_idx]
                if chosen_idx is not None and chosen_idx < len(effective_choices)
                else None
            )
        else:
            selected = None
            conf = 0.0
            is_amb = False
            is_blank = True
            counts = []

        correct_opt = None
        is_correct = None
        if q_idx < len(correct_answers):
            correct_opt = (correct_answers[q_idx] or "").strip().upper() if correct_answers else None
            if selected is not None and correct_opt in effective_choices:
                is_correct = selected == correct_opt

        per_q.append(
            QuestionResult(
                question_index=q_idx + 1,
                selected_option=selected,
                confidence=float(conf),
                is_ambiguous=bool(is_amb),
                is_blank=bool(is_blank),
                correct_option=correct_opt,
                is_correct=is_correct,
            )
        )

        if is_amb:
            ambiguous += 1
        if is_blank:
            blanks += 1

        # Draw overlay glyphs
        if q_idx < len(answer_rows):
            for idx, (contour, bbox) in enumerate(answer_rows[q_idx]):
                color = (0, 255, 0) if selected == (effective_choices[idx] if idx < len(effective_choices) else None) else (0, 0, 255)
                cv2.drawContours(overlay, [contour], -1, color, 2)

    # Compute subject scores and total
    subject_scores = _compute_subject_scores(per_q, config.subject_config)
    total_score = int(sum(subject_scores.values()))

    result = SheetResult(
        sheet_id=sheet_id,
        sheet_set=sheet_set,
        per_question=per_q,
        per_subject_scores=subject_scores,
        total_score=total_score,
        ambiguous_count=ambiguous,
        blank_count=blanks,
    )

    return result, rectified, overlay


def save_artifacts(
    result: SheetResult, rectified_bgr: np.ndarray, overlay_bgr: np.ndarray, base_dir: Optional[str] = None
) -> str:
    cfg_dir = base_dir or os.path.join(EvaluationConfig().save_artifacts_dir)
    sheet_dir = os.path.join(cfg_dir, result.sheet_id)
    os.makedirs(sheet_dir, exist_ok=True)

    # Save images
    rectified_path = os.path.join(sheet_dir, "rectified.jpg")
    overlay_path = os.path.join(sheet_dir, "overlay.jpg")
    cv2.imwrite(rectified_path, rectified_bgr)
    cv2.imwrite(overlay_path, overlay_bgr)

    # Save JSON
    result_path = os.path.join(sheet_dir, "result.json")
    serializable = asdict(result)
    # Convert dataclass QuestionResult to dicts
    serializable["per_question"] = [asdict(q) for q in result.per_question]
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(serializable, f, indent=2)

    return sheet_dir


def batch_evaluate_folder(
    folder: str,
    sheet_set: str,
    answer_key: Dict[str, List[str]],
    config: Optional[EvaluationConfig] = None,
    output_csv_path: Optional[str] = None,
) -> List[SheetResult]:
    if config is None:
        config = EvaluationConfig()
    image_exts = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}
    results: List[SheetResult] = []
    rows: List[Dict[str, Any]] = []

    for name in sorted(os.listdir(folder)):
        path = os.path.join(folder, name)
        if not os.path.isfile(path):
            continue
        ext = os.path.splitext(name)[1].lower()
        if ext not in image_exts:
            continue
        sheet_id = os.path.splitext(name)[0]
        image = cv2.imread(path)
        if image is None:
            continue
        try:
            result, rectified, overlay = evaluate_sheet(image, sheet_id, sheet_set, answer_key, config)
            results.append(result)
            # Save artifacts
            save_artifacts(result, rectified, overlay)
            # Flatten row for CSV
            row: Dict[str, Any] = {
                "sheet_id": result.sheet_id,
                "sheet_set": result.sheet_set,
                "total_score": result.total_score,
                "ambiguous": result.ambiguous_count,
                "blank": result.blank_count,
            }
            # per-subject
            for sub_name, score in result.per_subject_scores.items():
                row[f"score_{sub_name}"] = score
            # per-question answers and correctness
            for q in result.per_question:
                row[f"Q{q.question_index}_sel"] = q.selected_option or ""
                row[f"Q{q.question_index}_ok"] = "1" if q.is_correct else ("0" if q.is_correct is not None else "")
            rows.append(row)
        except Exception as e:
            # record failure row
            rows.append({
                "sheet_id": sheet_id,
                "sheet_set": sheet_set,
                "error": str(e),
            })

    if output_csv_path:
        import pandas as pd

        df = pd.DataFrame(rows)
        df.to_csv(output_csv_path, index=False)

    return results


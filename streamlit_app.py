import io
import os
import zipfile
from typing import Dict, List, Optional

import cv2
import numpy as np
import pandas as pd
import streamlit as st

from omr_eval import (
    load_answer_key,
    evaluate_sheet,
    save_artifacts,
    batch_evaluate_folder,
    EvaluationConfig,
)


st.set_page_config(page_title="Automated OMR Evaluation (MVP)", layout="wide")


@st.cache_data(show_spinner=False)
def _load_answer_key_cached(path: str) -> Dict[str, List[str]]:
    return load_answer_key(path)


def _bytes_to_bgr(file_bytes: bytes) -> Optional[np.ndarray]:
    arr = np.frombuffer(file_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    return img


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def main() -> None:
    st.title("Automated OMR Evaluation & Scoring System - MVP")
    st.caption("Evaluate OMR sheets, compute subject-wise and total scores, and export results.")

    with st.sidebar:
        st.header("Configuration")
        default_answer_paths = [
            "answer_key.json",
            os.path.join("sheets", "answer.csv"),
            os.path.join("sheets", "Keys"),
        ]
        selected_answer_path = st.selectbox(
            "Answer key file",
            options=default_answer_paths + ["Custom upload..."],
            index=0 if os.path.exists("answer_key.json") else 1,
        )
        if selected_answer_path == "Custom upload...":
            ak_file = st.file_uploader("Upload answer key (JSON/CSV)", type=["json", "csv"], accept_multiple_files=False)
            answer_key: Optional[Dict[str, List[str]]] = None
            if ak_file is not None:
                temp_path = os.path.join(st.session_state.get("_temp_dir", "."), f"_ak_{ak_file.name}")
                _ensure_dir(os.path.dirname(temp_path))
                with open(temp_path, "wb") as f:
                    f.write(ak_file.getbuffer())
                answer_key = _load_answer_key_cached(temp_path)
        else:
            try:
                answer_key = _load_answer_key_cached(selected_answer_path)
            except Exception as e:
                st.error(f"Failed to load answer key from '{selected_answer_path}': {e}")
                answer_key = None

        set_id = ""
        if answer_key:
            set_options = sorted(answer_key.keys())
            # Present a simple A/B radio if possible
            set_id = st.radio("Select exam set", options=set_options, horizontal=True)
        else:
            st.warning("Load a valid answer key to proceed.")

        st.divider()
        st.subheader("Processing Mode")
        mode = st.radio("Choose input mode", ["Upload images", "Process local sample folder"])  # noqa: F841

    st.divider()

    results_rows: List[dict] = []

    if answer_key and set_id:
        tabs = st.tabs(["Upload & Evaluate", "Batch (Folder)", "Session Results"])

        with tabs[0]:
            st.subheader("Upload images")
            uploads = st.file_uploader(
                "Drop OMR sheet images (JPG/PNG)",
                type=["jpg", "jpeg", "png", "bmp", "tif", "tiff"],
                accept_multiple_files=True,
            )
            col_a, col_b, col_c = st.columns([1, 1, 1])
            with col_a:
                student_prefix = st.text_input("Optional student ID prefix", value="")
            with col_b:
                save_artifacts_flag = st.checkbox("Save artifacts (rectified, overlay, JSON)", value=True)
            with col_c:
                eval_btn = st.button("Evaluate Uploaded Images", type="primary")

            if eval_btn and uploads:
                cfg = EvaluationConfig()
                per_sheet_outputs: List[dict] = []
                for f in uploads:
                    sheet_id = os.path.splitext(f.name)[0]
                    if student_prefix:
                        sheet_id = f"{student_prefix}_{sheet_id}"
                    img = _bytes_to_bgr(f.getbuffer())
                    if img is None:
                        st.warning(f"Skipping {f.name}: cannot read image")
                        continue
                    try:
                        result, rectified, overlay = evaluate_sheet(img, sheet_id, set_id, answer_key, cfg)
                        if save_artifacts_flag:
                            save_artifacts(result, rectified, overlay)
                        st.success(f"Processed {f.name}: Total {result.total_score}")
                        with st.expander(f"Details - {sheet_id}"):
                            col1, col2 = st.columns(2)
                            with col1:
                                st.image(cv2.cvtColor(rectified, cv2.COLOR_BGR2RGB), caption="Rectified", use_container_width=True)
                            with col2:
                                st.image(cv2.cvtColor(overlay, cv2.COLOR_BGR2RGB), caption="Overlay", use_container_width=True)
                            st.json({
                                "per_subject_scores": result.per_subject_scores,
                                "total_score": result.total_score,
                                "ambiguous": result.ambiguous_count,
                                "blank": result.blank_count,
                            })
                        # flat row
                        row = {
                            "sheet_id": result.sheet_id,
                            "sheet_set": result.sheet_set,
                            "total_score": result.total_score,
                            **{f"score_{k}": v for k, v in result.per_subject_scores.items()},
                        }
                        per_sheet_outputs.append(row)
                    except Exception as e:
                        st.error(f"Error processing {f.name}: {e}")

                if per_sheet_outputs:
                    df = pd.DataFrame(per_sheet_outputs)
                    st.dataframe(df, use_container_width=True)
                    csv_bytes = df.to_csv(index=False).encode("utf-8")
                    st.download_button("Download CSV", data=csv_bytes, file_name="results.csv", mime="text/csv", key="dl_uploaded")
                    st.session_state["last_results_df"] = df

        with tabs[1]:
            st.subheader("Batch process local folder")
            st.caption("This runs only on the server machine, useful for local runs with sample data.")
            default_folder = os.path.join("sheets", f"Set {'A' if set_id == 'A' else 'B'}") if set_id in ("A","B") else os.path.join("sheets", "Set A")
            folder = st.text_input("Folder path", value=default_folder)
            out_csv = st.text_input("Output CSV path", value="batch_results.csv")
            run_btn = st.button("Run Batch Evaluation")
            if run_btn:
                if not os.path.isdir(folder):
                    st.error("Folder not found.")
                else:
                    cfg = EvaluationConfig()
                    with st.spinner("Processing folder..."):
                        _ = batch_evaluate_folder(folder, set_id, answer_key, cfg, out_csv)
                    st.success(f"Completed. Results saved to {out_csv} and artifacts/.")
                    try:
                        df = pd.read_csv(out_csv)
                        st.dataframe(df.head(200), use_container_width=True)
                        st.session_state["last_results_df"] = df
                    except Exception:
                        pass

        with tabs[2]:
            st.subheader("Session Results")
            df = st.session_state.get("last_results_df")
            if isinstance(df, pd.DataFrame):
                st.dataframe(df, use_container_width=True)
                csv_bytes = df.to_csv(index=False).encode("utf-8")
                st.download_button("Download CSV", data=csv_bytes, file_name="results.csv", mime="text/csv", key="dl_session")
            else:
                st.info("No results yet. Upload images or run batch to see results here.")

    else:
        st.info("Please load a valid answer key and select a set to begin.")


if __name__ == "__main__":
    main()



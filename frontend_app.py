import streamlit as st
import pandas as pd
import requests
from io import BytesIO

API_BASE = st.secrets.get("API_BASE", "http://127.0.0.1:8000")

st.set_page_config(page_title="OMR Evaluation Dashboard", layout="wide")
st.title("OMR Evaluation System")

tab_upload, tab_dashboard = st.tabs(["Upload & Evaluate", "Dashboard"])


with tab_upload:
    st.subheader("Upload OMR Sheets")
    set_version = st.selectbox("Set Version", ["A", "B"], index=0)
    student_ids_text = st.text_area(
        "Optional: Student IDs (one per line, aligned with files)",
        placeholder="student1\nstudent2\n...",
    )
    uploaded_files = st.file_uploader(
        "Select image files (.jpg/.jpeg/.png)", type=["jpg", "jpeg", "png"], accept_multiple_files=True
    )

    if st.button("Process"):
        if not uploaded_files:
            st.warning("Please select at least one file.")
        else:
            student_ids = [s for s in student_ids_text.splitlines() if s.strip()] or None
            files_payload = [("files", (f.name, f.getvalue(), f.type or "image/jpeg")) for f in uploaded_files]
            params = {"set_version": set_version}
            if student_ids:
                for sid in student_ids:
                    params.setdefault("student_ids", []).append(sid)

            with st.spinner("Uploading and evaluating..."):
                resp = requests.post(f"{API_BASE}/upload", files=files_payload, params=params, timeout=300)
            if resp.status_code == 200:
                data = resp.json()
                st.success(f"Processed {data['processed']} sheets")
                df = pd.DataFrame([
                    {
                        "ID": r["id"],
                        "File": r["file_name"],
                        "Set": r["set_version"],
                        "Student": r.get("student_id"),
                        **r["subject_scores"],
                        "Total": r["total_score"],
                        "Created": r["created_at"],
                    }
                    for r in data["results"]
                ])
                st.dataframe(df, use_container_width=True)
            else:
                st.error(f"Error: {resp.status_code} - {resp.text}")


with tab_dashboard:
    st.subheader("Summary Metrics")
    col1, col2 = st.columns([2, 1])

    with col1:
        r = requests.get(f"{API_BASE}/results", params={"limit": 500})
        if r.status_code == 200 and r.json():
            rows = r.json()
            df = pd.DataFrame([
                {
                    "ID": x["id"],
                    "File": x["file_name"],
                    "Set": x["set_version"],
                    "Student": x.get("student_id"),
                    **x["subject_scores"],
                    "Total": x["total_score"],
                    "Created": x["created_at"],
                }
                for x in rows
            ])
            st.dataframe(df, use_container_width=True, height=400)
        else:
            st.info("No results yet. Upload sheets to see data.")

    with col2:
        m = requests.get(f"{API_BASE}/metrics").json()
        st.metric("Total Sheets", m["total_sheets"])
        st.metric("Average Score", f"{m['average_score']:.1f}")
        st.metric("Max Score", m["max_score"])
        st.metric("Min Score", m["min_score"])
        st.metric("Perfect Sheets", m["perfect_sheets"]) 

        if m.get("per_subject_average"):
            st.write("Per-Subject Averages")
            avg_df = pd.DataFrame(
                {
                    "Subject": list(m["per_subject_average"].keys()),
                    "Average": list(m["per_subject_average"].values()),
                }
            )
            st.bar_chart(avg_df.set_index("Subject"))

    st.subheader("Export")
    resp = requests.get(f"{API_BASE}/export/csv")
    if resp.status_code == 200:
        st.download_button(
            label="Download Results CSV",
            data=resp.content,
            file_name="results.csv",
            mime="text/csv",
        )
    else:
        st.caption("No export available yet.")



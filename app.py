# import streamlit as st
# from omr_eval import evaluate_batch
# import pandas as pd

# st.title("OMR Evaluation MVP (Multiple Sets)")

# if st.button("Run Evaluation"):
#     results = evaluate_batch("sheets")
#     st.success(f"Processed {len(results)} sheets!")
#     df = pd.DataFrame([{
#         "File": r["file"], 
#         "Version": r["version"], 
#         "S1": r["subject_scores"]["S1"],
#         "S2": r["subject_scores"]["S2"],
#         "S3": r["subject_scores"]["S3"],
#         "S4": r["subject_scores"]["S4"],
#         "S5": r["subject_scores"]["S5"],
#         "Total": r["total"]
#     } for r in results])
#     st.dataframe(df)
#     csv = df.to_csv(index=False).encode('utf-8')
#     st.download_button("Download CSV", csv, "results.csv", "text/csv")
import streamlit as st
from omr_eval import evaluate_batch
import pandas as pd

st.title("OMR Evaluation MVP (5 Subjects, Multiple Sets)")

if st.button("Run Evaluation"):
    results = evaluate_batch("sheets")
    st.success(f"Processed {len(results)} sheets!")

    df = pd.DataFrame([{
        "File": r["file"],
        "Python": r["subject_scores"]["Python"],
        "EDA": r["subject_scores"]["EDA"],
        "SQL": r["subject_scores"]["SQL"],
        "Power BI": r["subject_scores"]["Power BI"],
        "Statistics": r["subject_scores"]["Statistics"],
        "Total": r["total"]
    } for r in results])

    st.dataframe(df)
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("Download CSV", csv, "results.csv", "text/csv")

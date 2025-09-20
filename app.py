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
import numpy as np

st.title("OMR Evaluation System (5 Subjects, Multiple Sets)")
st.markdown("**Enhanced Detection Algorithm with Improved Accuracy**")

if st.button("Run Evaluation"):
    with st.spinner("Processing OMR sheets..."):
        results = evaluate_batch("sheets")
    
    st.success(f"Processed {len(results)} sheets!")

    # Create results dataframe
    df = pd.DataFrame([{
        "File": r["file"],
        "Python": r["subject_scores"]["Python"],
        "EDA": r["subject_scores"]["EDA"],
        "SQL": r["subject_scores"]["SQL"],
        "Power BI": r["subject_scores"]["Power BI"],
        "Statistics": r["subject_scores"]["Statistics"],
        "Total": r["total"]
    } for r in results])

    # Display summary statistics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Sheets", len(results))
    
    with col2:
        avg_score = df["Total"].mean()
        st.metric("Average Score", f"{avg_score:.1f}")
    
    with col3:
        max_score = df["Total"].max()
        st.metric("Highest Score", max_score)
    
    with col4:
        perfect_sheets = len(df[df["Total"] == 100])
        st.metric("Perfect Sheets", perfect_sheets)

    # Display results table
    st.subheader("Detailed Results")
    st.dataframe(df, use_container_width=True)
    
    # Subject-wise analysis
    st.subheader("Subject-wise Performance")
    subject_stats = df[["Python", "EDA", "SQL", "Power BI", "Statistics"]].describe()
    st.dataframe(subject_stats)
    
    # Download options
    col1, col2 = st.columns(2)
    
    with col1:
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("Download Results CSV", csv, "omr_results.csv", "text/csv")
    
    with col2:
        # Create detailed analysis
        analysis = {
            "Metric": ["Total Sheets", "Average Score", "Max Score", "Min Score", "Sheets with 0 Score"],
            "Value": [
                len(results),
                f"{df['Total'].mean():.2f}",
                df["Total"].max(),
                df["Total"].min(),
                len(df[df["Total"] == 0])
            ]
        }
        analysis_df = pd.DataFrame(analysis)
        analysis_csv = analysis_df.to_csv(index=False).encode('utf-8')
        st.download_button("Download Analysis CSV", analysis_csv, "omr_analysis.csv", "text/csv")

# Add calibration section
st.sidebar.subheader("Calibration Tools")
if st.sidebar.button("Generate Debug Image"):
    from omr_eval import calibrate_omr_coordinates
    calibrate_omr_coordinates("sheets/Set A/Img1.jpeg")
    st.sidebar.success("Debug image saved as 'debug_omr_coordinates.jpg'")
    st.sidebar.info("Check the image to verify bubble alignment")

st.sidebar.subheader("Detection Info")
st.sidebar.info("""
**Detection Features:**
- Multi-method bubble detection
- Adaptive thresholding
- Circular mask analysis
- Contour detection
- Auto-coordinate optimization
""")

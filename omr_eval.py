# import cv2
# import numpy as np
# import json
# import os

# def load_answer_keys(excel_path="key.xlsx"):
#     df = pd.read_excel(excel_path)
#     keys = {}
#     for _, row in df.iterrows():
#         version = row['Version']
#         answers = row[1:].tolist()  # skip 'Version' column
#         keys[version] = answers
#     return keys
    
# def create_circular_mask(h, w):
#     Y, X = np.ogrid[:h, :w]
#     center = (int(h/2), int(w/2))
#     radius = min(h,w)//2
#     dist_from_center = (X - center[1])**2 + (Y - center[0])**2
#     mask = dist_from_center <= radius**2
#     return mask

# def rectify_image(img):
#     gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
#     _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)
#     contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
#     contours = sorted(contours, key=cv2.contourArea, reverse=True)
#     if len(contours)==0:
#         return img
#     sheet_cnt = contours[0]
#     peri = cv2.arcLength(sheet_cnt, True)
#     approx = cv2.approxPolyDP(sheet_cnt, 0.02 * peri, True)
#     if len(approx) == 4:
#         pts = approx.reshape(4,2)
#         rect = np.zeros((4,2), dtype="float32")
#         s = pts.sum(axis=1)
#         rect[0] = pts[np.argmin(s)]
#         rect[2] = pts[np.argmax(s)]
#         diff = np.diff(pts, axis=1)
#         rect[1] = pts[np.argmin(diff)]
#         rect[3] = pts[np.argmax(diff)]
#         dst = np.array([[0,0],[1000,0],[1000,1400],[0,1400]], dtype="float32")
#         M = cv2.getPerspectiveTransform(rect, dst)
#         warp = cv2.warpPerspective(img, M, (1000,1400))
#         return warp
#     return img

# def extract_answers(img, version="A"):
#     gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
#     answers = []
#     # assume 5 subjects x 20 questions
#     rows, cols = 20, 5
#     start_x, start_y = 100, 200  # adjust per template
#     bubble_w, bubble_h = 40, 40
#     spacing_x, spacing_y = 50, 50
#     for q in range(100):
#         col_idx = q % cols
#         row_idx = q // cols
#         x = start_x + col_idx*spacing_x
#         y = start_y + row_idx*spacing_y
#         roi = gray[y:y+bubble_h, x:x+bubble_w]
#         mask = create_circular_mask(bubble_h, bubble_w)
#         _, th = cv2.threshold(roi, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
#         score = np.sum((th==0)&mask)/np.sum(mask)
#         marked = score>0.3
#         # simple mapping: A/B/C/D based on column in row
#         choice = "ABCD"[col_idx] if marked else ""
#         answers.append(choice)
#     return answers

# def evaluate_sheet(image_path, answer_keys, version):
#     img = cv2.imread(image_path)
#     warp = rectify_image(img)
#     extracted = extract_answers(warp, version)
#     key = answer_keys[version]
#     subject_scores = {f"S{i+1}":0 for i in range(5)}
#     total = 0
#     for i, ans in enumerate(extracted):
#         subj = f"S{i//20+1}"
#         if i < len(key) and ans==key[i]:
#             subject_scores[subj] +=1
#             total +=1
#     return {
#         "file": os.path.basename(image_path),
#         "version": version,
#         "answers": extracted,
#         "subject_scores": subject_scores,
#         "total": total
#     }

# def evaluate_batch(folder="sheets"):
#     keys = generate_answer_key(folder)
#     results = []

#     # Loop through subfolders (setA, setB)
#     for set_folder in os.listdir(folder):
#         set_path = os.path.join(folder, set_folder)
#         if os.path.isdir(set_path):
#             version = "A" if "A" in set_folder.upper() else "B"
#             for fname in os.listdir(set_path):
#                 if fname.lower().endswith((".jpg",".png")):
#                     res = evaluate_sheet(os.path.join(set_path,fname), keys, version)
#                     results.append(res)
#     return results


# def generate_answer_key(folder="sheets"):
#     import cv2
#     import numpy as np
#     import os
#     import pandas as pd
#     """
#     Generate answer key XLSX from training images in setA/setB folders.
#     """
#     key_dict = {}
#     for set_folder in os.listdir(folder):
#         set_path = os.path.join(folder, set_folder)
#         if os.path.isdir(set_path):
#             version = "A" if "A" in set_folder.upper() else "B"
#             all_answers = []

#             for fname in os.listdir(set_path):
#                 if fname.lower().endswith((".jpg",".png")):
#                     img_path = os.path.join(set_path, fname)
#                     img = cv2.imread(img_path)
#                     warp = rectify_image(img)
#                     answers = extract_answers(warp, version)
#                     all_answers.append(answers)

#             all_answers = np.array(all_answers)
#             consensus = []
#             for q_answers in all_answers.T:
#                 vals, counts = np.unique(q_answers[q_answers != ""], return_counts=True)
#                 if len(vals) == 0:
#                     consensus.append("")  # no mark detected
#                 else:
#                     consensus.append(vals[np.argmax(counts)])
#             key_dict[version] = consensus

#     df_data = []
#     for version, answers in key_dict.items():
#         df_data.append([version]+answers)
#     df = pd.DataFrame(df_data, columns=["Version"] + [f"Q{i+1}" for i in range(100)])
#     df.to_excel("generated_answer_key.xlsx", index=False)
#     print("Answer key saved as 'generated_answer_key.xlsx'")
#     return key_dict

import cv2
import numpy as np
import pandas as pd
import os

SUBJECTS = ["Python", "EDA", "SQL", "Power BI", "Statistics"]
QUESTIONS_PER_SUBJECT = 20

# ------------------- Load Keys -------------------
import pandas as pd

import pandas as pd

def load_keys():
    """
    Load Set A and Set B keys from CSV files.
    """
    keyA_df = pd.read_csv("sheets/Keys/KeySetA.csv")
    keyB_df = pd.read_csv("sheets/Keys/KeySetB.csv")

    SUBJECTS = ["Python", "EDA", "SQL", "Power BI", "Statistics"]
    CSV_COLUMNS = ["Python", "EDA", "SQL", "POWER BI", "Statistics"]  # Actual column names in CSV

    def extract_answer(x):
        """Extract answer from format like '1 - a' or '81. a'"""
        if pd.isna(x) or str(x).strip() == '':
            return ''
        x_str = str(x).strip()
        if '-' in x_str:
            return x_str.split('-')[-1].strip().lower()
        elif '.' in x_str:
            return x_str.split('.')[-1].strip().lower()
        else:
            return x_str.lower()

    keyA = {subj: keyA_df[csv_col].apply(extract_answer).tolist() 
            for subj, csv_col in zip(SUBJECTS, CSV_COLUMNS)}
    
    keyB = {subj: keyB_df[csv_col].apply(extract_answer).tolist() 
            for subj, csv_col in zip(SUBJECTS, CSV_COLUMNS)}
    
    return keyA, keyB



# ------------------- Image Processing -------------------
def create_circular_mask(h, w):
    Y, X = np.ogrid[:h, :w]
    center = (int(h/2), int(w/2))
    radius = min(h,w)//2
    dist_from_center = (X - center[1])**2 + (Y - center[0])**2
    return dist_from_center <= radius**2

def rectify_image(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return img
    sheet_cnt = max(contours, key=cv2.contourArea)
    peri = cv2.arcLength(sheet_cnt, True)
    approx = cv2.approxPolyDP(sheet_cnt, 0.02 * peri, True)
    if len(approx) == 4:
        pts = approx.reshape(4,2)
        rect = np.zeros((4,2), dtype="float32")
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]
        rect[2] = pts[np.argmax(s)]
        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]
        rect[3] = pts[np.argmax(diff)]
        dst = np.array([[0,0],[1000,0],[1000,1400],[0,1400]], dtype="float32")
        M = cv2.getPerspectiveTransform(rect, dst)
        warp = cv2.warpPerspective(img, M, (1000,1400))
        return warp
    return img

# ------------------- Answer Extraction -------------------
def extract_answers(img):
    """
    Extract answers per subject.
    Returns: {'Python': [...], 'EDA': [...], ...}
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    answers = {subj: [] for subj in SUBJECTS}

    # Adjust these coordinates based on your OMR template
    # Assuming 5 subjects in columns, 20 questions in rows
    start_x, start_y = 100, 200  # Starting position
    bubble_w, bubble_h = 30, 30  # Bubble size
    spacing_x, spacing_y = 200, 30  # Spacing between subjects and questions
    choice_spacing = 50  # Spacing between A/B/C/D choices

    for s_idx, subj in enumerate(SUBJECTS):
        for q_idx in range(QUESTIONS_PER_SUBJECT):
            # Calculate position for this question
            x = start_x + s_idx * spacing_x
            y = start_y + q_idx * spacing_y
            
            # Check all 4 choices (A, B, C, D)
            choice_scores = []
            for choice_idx in range(4):  # A, B, C, D
                choice_x = x + choice_idx * choice_spacing
                roi = gray[y:y+bubble_h, choice_x:choice_x+bubble_w]
                
                if roi.size == 0 or roi.shape[0] != bubble_h or roi.shape[1] != bubble_w:  # Skip if ROI is empty or wrong size
                    choice_scores.append(0)
                    continue
                    
                mask = create_circular_mask(roi.shape[0], roi.shape[1])
                _, th = cv2.threshold(roi, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                score = np.sum((th==0) & mask) / np.sum(mask) if np.sum(mask) > 0 else 0
                choice_scores.append(score)
            
            # Find the choice with highest score (most marked)
            if max(choice_scores) > 0.3:  # Threshold for detection
                choice_idx = np.argmax(choice_scores)
                choice = chr(ord('a') + choice_idx)  # Convert to a, b, c, d
            else:
                choice = ""  # No clear marking detected
            
            answers[subj].append(choice)
    return answers

# ------------------- Evaluate Single Sheet -------------------
def evaluate_sheet(image_path, answer_key):
    img = cv2.imread(image_path)
    warp = rectify_image(img)
    extracted = extract_answers(warp)
    subject_scores = {}
    total = 0
    for subj in SUBJECTS:
        correct = sum([1 for a,b in zip(extracted[subj], answer_key[subj]) if a==b])
        subject_scores[subj] = correct
        total += correct
    return {
        "file": os.path.basename(image_path),
        "answers": extracted,
        "subject_scores": subject_scores,
        "total": total
    }

# ------------------- Batch Evaluation -------------------
def evaluate_batch(folder="sheets"):
    keyA, keyB = load_keys()
    results = []

    for set_folder in os.listdir(folder):
        set_path = os.path.join(folder, set_folder)
        if os.path.isdir(set_path):
            key = keyA if "A" in set_folder.upper() else keyB
            for fname in os.listdir(set_path):
                if fname.lower().endswith((".jpg", ".png", ".jpeg")):
                    res = evaluate_sheet(os.path.join(set_path,fname), key)
                    results.append(res)
    return results

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
    Extract answers per subject with improved detection.
    Returns: {'Python': [...], 'EDA': [...], ...}
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    answers = {subj: [] for subj in SUBJECTS}

    # Enhanced parameters based on typical OMR layout
    # These coordinates need to be adjusted based on your specific OMR template
    start_x, start_y = 150, 250  # Starting position
    bubble_w, bubble_h = 25, 25  # Bubble size
    spacing_x, spacing_y = 180, 35  # Spacing between subjects and questions
    choice_spacing = 40  # Spacing between A/B/C/D choices

    for s_idx, subj in enumerate(SUBJECTS):
        for q_idx in range(QUESTIONS_PER_SUBJECT):
            # Calculate position for this question
            x = start_x + s_idx * spacing_x
            y = start_y + q_idx * spacing_y
            
            # Check all 4 choices (A, B, C, D)
            choice_scores = []
            for choice_idx in range(4):  # A, B, C, D
                choice_x = x + choice_idx * choice_spacing
                
                # Ensure we don't go out of bounds
                if choice_x + bubble_w > gray.shape[1] or y + bubble_h > gray.shape[0]:
                    choice_scores.append(0)
                    continue
                    
                roi = gray[y:y+bubble_h, choice_x:choice_x+bubble_w]
                
                if roi.size == 0 or roi.shape[0] != bubble_h or roi.shape[1] != bubble_w:
                    choice_scores.append(0)
                    continue
                
                # Enhanced bubble detection
                score = detect_bubble_marking(roi)
                choice_scores.append(score)
            
            # Find the choice with highest score (most marked)
            if max(choice_scores) > 0.15:  # Lowered threshold for better detection
                choice_idx = np.argmax(choice_scores)
                choice = chr(ord('a') + choice_idx)  # Convert to a, b, c, d
            else:
                choice = ""  # No clear marking detected
            
            answers[subj].append(choice)
    return answers

def detect_bubble_marking(roi):
    """
    Enhanced bubble detection using multiple techniques.
    """
    if roi.size == 0:
        return 0
    
    # Method 1: Circular mask with adaptive thresholding
    mask = create_circular_mask(roi.shape[0], roi.shape[1])
    
    # Use adaptive thresholding for better detection
    adaptive_thresh = cv2.adaptiveThreshold(roi, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                          cv2.THRESH_BINARY_INV, 11, 2)
    
    # Count dark pixels within the circular mask
    dark_pixels = np.sum((adaptive_thresh == 255) & mask)
    total_pixels = np.sum(mask)
    
    if total_pixels == 0:
        return 0
    
    score1 = dark_pixels / total_pixels
    
    # Method 2: Otsu thresholding
    _, otsu_thresh = cv2.threshold(roi, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    dark_pixels_otsu = np.sum((otsu_thresh == 255) & mask)
    score2 = dark_pixels_otsu / total_pixels if total_pixels > 0 else 0
    
    # Method 3: Mean intensity (darker = more marked)
    mean_intensity = np.mean(roi[mask])
    score3 = (255 - mean_intensity) / 255
    
    # Method 4: Contour detection
    contours, _ = cv2.findContours(otsu_thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contour_area = 0
    for contour in contours:
        if cv2.contourArea(contour) > 10:  # Filter small noise
            contour_area += cv2.contourArea(contour)
    score4 = min(contour_area / (roi.shape[0] * roi.shape[1]), 1.0)
    
    # Combine all methods with weights
    final_score = (score1 * 0.4 + score2 * 0.3 + score3 * 0.2 + score4 * 0.1)
    
    return final_score

# ------------------- Auto-detect OMR Layout -------------------
def detect_omr_layout(img):
    """
    Automatically detect OMR bubble positions using computer vision.
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Use HoughCircles to detect circular bubbles
    circles = cv2.HoughCircles(gray, cv2.HOUGH_GRADIENT, 1, 20,
                              param1=50, param2=30, minRadius=8, maxRadius=20)
    
    if circles is not None:
        circles = np.round(circles[0, :]).astype("int")
        
        # Group circles by rows and columns
        # Sort by y-coordinate first (rows), then by x-coordinate (columns)
        circles = sorted(circles, key=lambda x: (x[1], x[0]))
        
        # Find the pattern - assuming 5 subjects x 20 questions x 4 choices
        bubble_positions = []
        current_row = []
        last_y = circles[0][1] if len(circles) > 0 else 0
        
        for (x, y, r) in circles:
            if abs(y - last_y) > 20:  # New row
                if current_row:
                    bubble_positions.append(current_row)
                current_row = [(x, y, r)]
            else:
                current_row.append((x, y, r))
            last_y = y
        
        if current_row:
            bubble_positions.append(current_row)
        
        return bubble_positions
    
    return None

def extract_answers_auto(img):
    """
    Extract answers using auto-detected bubble positions.
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    answers = {subj: [] for subj in SUBJECTS}
    
    # Auto-detect bubble positions
    bubble_positions = detect_omr_layout(img)
    
    if bubble_positions is None or len(bubble_positions) < 20:
        print("Could not auto-detect OMR layout, falling back to manual coordinates")
        return extract_answers(img)
    
    # Process detected bubbles
    for q_idx in range(min(20, len(bubble_positions))):
        row_bubbles = bubble_positions[q_idx]
        
        # Sort bubbles in this row by x-coordinate
        row_bubbles = sorted(row_bubbles, key=lambda x: x[0])
        
        # Group bubbles by subject (assuming 4 bubbles per subject)
        for s_idx in range(5):  # 5 subjects
            if s_idx * 4 + 3 < len(row_bubbles):
                # Get 4 bubbles for this subject
                subject_bubbles = row_bubbles[s_idx * 4:(s_idx + 1) * 4]
                
                # Check which bubble is marked
                choice_scores = []
                for choice_idx, (x, y, r) in enumerate(subject_bubbles):
                    # Extract ROI around the bubble
                    roi = gray[y-r:y+r, x-r:x+r]
                    if roi.size > 0:
                        score = detect_bubble_marking(roi)
                        choice_scores.append(score)
                    else:
                        choice_scores.append(0)
                
                # Find the most marked choice
                if max(choice_scores) > 0.15:
                    choice_idx = np.argmax(choice_scores)
                    choice = chr(ord('a') + choice_idx)
                else:
                    choice = ""
                
                answers[SUBJECTS[s_idx]].append(choice)
            else:
                # Not enough bubbles for this subject
                answers[SUBJECTS[s_idx]].append("")
    
    return answers

# ------------------- Calibration Helper -------------------
def calibrate_omr_coordinates(image_path, save_debug_image=True):
    """
    Helper function to visualize and calibrate OMR coordinates.
    This will help find the correct positions for bubbles.
    """
    img = cv2.imread(image_path)
    if img is None:
        print(f"Could not load image: {image_path}")
        return
    
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    debug_img = img.copy()
    
    # Multiple coordinate sets to try
    coordinate_sets = [
        # Set 1: Original coordinates
        {"start_x": 150, "start_y": 250, "bubble_w": 25, "bubble_h": 25, 
         "spacing_x": 180, "spacing_y": 35, "choice_spacing": 40, "color": (0, 255, 0)},
        
        # Set 2: Adjusted coordinates
        {"start_x": 200, "start_y": 300, "bubble_w": 30, "bubble_h": 30, 
         "spacing_x": 200, "spacing_y": 40, "choice_spacing": 45, "color": (255, 0, 0)},
        
        # Set 3: Alternative layout
        {"start_x": 100, "start_y": 200, "bubble_w": 20, "bubble_h": 20, 
         "spacing_x": 160, "spacing_y": 30, "choice_spacing": 35, "color": (0, 0, 255)},
    ]
    
    for coord_set in coordinate_sets:
        start_x = coord_set["start_x"]
        start_y = coord_set["start_y"]
        bubble_w = coord_set["bubble_w"]
        bubble_h = coord_set["bubble_h"]
        spacing_x = coord_set["spacing_x"]
        spacing_y = coord_set["spacing_y"]
        choice_spacing = coord_set["choice_spacing"]
        color = coord_set["color"]
        
        # Draw rectangles to show where we're looking for bubbles
        for s_idx in range(5):  # 5 subjects
            for q_idx in range(20):  # 20 questions per subject
                x = start_x + s_idx * spacing_x
                y = start_y + q_idx * spacing_y
                
                for choice_idx in range(4):  # A, B, C, D
                    choice_x = x + choice_idx * choice_spacing
                    
                    if (choice_x + bubble_w < gray.shape[1] and 
                        y + bubble_h < gray.shape[0]):
                        
                        # Draw rectangle around bubble area
                        cv2.rectangle(debug_img, 
                                    (choice_x, y), 
                                    (choice_x + bubble_w, y + bubble_h), 
                                    color, 1)
                        
                        # Add text label for first few questions only
                        if q_idx < 3 and s_idx < 2:
                            cv2.putText(debug_img, f"{chr(ord('A') + choice_idx)}", 
                                      (choice_x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 
                                      0.3, color, 1)
    
    if save_debug_image:
        cv2.imwrite("debug_omr_coordinates.jpg", debug_img)
        print("Debug image saved as 'debug_omr_coordinates.jpg'")
        print("Check the image to see if any colored rectangles align with the bubbles")
        print("Green = Set 1, Red = Set 2, Blue = Set 3")
    
    return debug_img

def test_coordinate_sets(image_path):
    """
    Test different coordinate sets to find the best one.
    """
    img = cv2.imread(image_path)
    if img is None:
        print(f"Could not load image: {image_path}")
        return
    
    warp = rectify_image(img)
    keyA, keyB = load_keys()
    
    # Test different coordinate sets
    coordinate_sets = [
        {"start_x": 150, "start_y": 250, "bubble_w": 25, "bubble_h": 25, 
         "spacing_x": 180, "spacing_y": 35, "choice_spacing": 40},
        {"start_x": 200, "start_y": 300, "bubble_w": 30, "bubble_h": 30, 
         "spacing_x": 200, "spacing_y": 40, "choice_spacing": 45},
        {"start_x": 100, "start_y": 200, "bubble_w": 20, "bubble_h": 20, 
         "spacing_x": 160, "spacing_y": 30, "choice_spacing": 35},
    ]
    
    best_score = 0
    best_coords = None
    
    for i, coords in enumerate(coordinate_sets):
        # Temporarily update global coordinates
        global start_x, start_y, bubble_w, bubble_h, spacing_x, spacing_y, choice_spacing
        start_x, start_y = coords["start_x"], coords["start_y"]
        bubble_w, bubble_h = coords["bubble_w"], coords["bubble_h"]
        spacing_x, spacing_y = coords["spacing_x"], coords["spacing_y"]
        choice_spacing = coords["choice_spacing"]
        
        # Test extraction
        extracted = extract_answers(warp)
        total_correct = 0
        for subj in SUBJECTS:
            correct = sum([1 for a,b in zip(extracted[subj], keyA[subj]) if a==b])
            total_correct += correct
        
        print(f"Coordinate Set {i+1}: {total_correct} correct answers")
        if total_correct > best_score:
            best_score = total_correct
            best_coords = coords
    
    print(f"Best coordinate set: {best_coords} with {best_score} correct answers")
    return best_coords

# ------------------- Evaluate Single Sheet -------------------
def evaluate_sheet(image_path, answer_key):
    img = cv2.imread(image_path)
    warp = rectify_image(img)
    
    # Try auto-detection first, fall back to manual if it fails
    try:
        extracted = extract_answers_auto(warp)
    except Exception as e:
        print(f"Auto-detection failed for {image_path}: {e}")
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

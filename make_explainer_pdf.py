"""Builds Project_Explanation.pdf: a short explainer for the teacher, organised by the marking scheme.

    python make_explainer_pdf.py
"""
from pathlib import Path

from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate,
                                Spacer, Table, TableStyle)

from report_content import GUIDE, TEAM

proj = Path(__file__).parent
out = proj / "Project_Explanation.pdf"
W = A4[0] - 36 * mm

ss = getSampleStyleSheet()
BLUE, GREY, LIGHT = colors.HexColor("#1F5FBF"), colors.HexColor("#5A5A5A"), colors.HexColor("#EEF3FB")
body = ParagraphStyle("body", parent=ss["Normal"], fontName="Helvetica", fontSize=10, leading=14, spaceAfter=5)
small = ParagraphStyle("small", parent=body, fontSize=8.5, leading=11, textColor=GREY)
cell = ParagraphStyle("cell", parent=body, fontSize=8.8, leading=11.5, spaceAfter=0)
cellb = ParagraphStyle("cellb", parent=cell, fontName="Helvetica-Bold")
h1 = ParagraphStyle("h1", parent=ss["Heading1"], fontName="Helvetica-Bold", fontSize=16, leading=20,
                    textColor=BLUE, spaceBefore=6, spaceAfter=8, keepWithNext=1)
h2 = ParagraphStyle("h2", parent=ss["Heading2"], fontName="Helvetica-Bold", fontSize=12, leading=15,
                    spaceBefore=8, spaceAfter=5, keepWithNext=1)
title = ParagraphStyle("title", parent=h1, fontSize=24, leading=29, alignment=TA_CENTER, textColor=colors.black)
sub = ParagraphStyle("sub", parent=body, fontSize=12, leading=16, alignment=TA_CENTER, textColor=GREY)
key = ParagraphStyle("key", parent=body, backColor=LIGHT, borderColor=BLUE, borderWidth=0.8,
                     borderPadding=7, leftIndent=7, rightIndent=7, spaceBefore=12, spaceAfter=12)

story = []


def P(t, s=body):
    story.append(Paragraph(t, s))


def table(rows, widths, center=False):
    data = [[Paragraph(str(c), cellb if i == 0 else cell) for c in r] for i, r in enumerate(rows)]
    t = Table(data, colWidths=[w * W for w in widths], repeatRows=1)
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#BBBBBB")),
                           ("BACKGROUND", (0, 0), (-1, 0), LIGHT), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                           ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
    if center:
        t.hAlign = "CENTER"
    story.append(t)
    story.append(Spacer(1, 8))


def figure(path, caption, width=1.0):
    p = proj / path
    w, h = PILImage.open(p).size
    iw = W * width
    story.append(KeepTogether([Image(str(p), width=iw, height=iw * h / w), Paragraph(caption, small), Spacer(1, 6)]))


def on_page(c, doc):
    c.saveState()
    c.setFont("Helvetica", 8)
    c.setFillColor(GREY)
    c.drawString(18 * mm, 10 * mm, "Real-Time PPE Detection - project explanation")
    c.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {doc.page}")
    c.restoreState()


# ---------------- cover ----------------
story.append(Spacer(1, 25 * mm))
P("Real-Time PPE Detection", title)
P("A computer vision system for construction site safety", sub)
P("Mini Project: Real-Time Computer Vision System", sub)
story.append(Spacer(1, 8 * mm))
table([["Name", "Roll No."]] + [list(m) for m in TEAM], [0.45, 0.2], center=True)
P(f"Guide: {GUIDE}", sub)
P("<b>In one paragraph.</b> The system looks at images, videos and live camera feeds and detects workers, their "
  "safety gear (hardhat, vest, mask) and <b>missing</b> gear. When gear is missing it shows a red warning. We cleaned "
  "a public dataset, trained a YOLOv8n model (0.600 mAP@0.5, about 25 FPS on a laptop CPU), compared it with four "
  "state-of-the-art YOLO models and with published results, and built a web app that runs on laptops and phones.", key)
P("<b>How this document maps to the marking scheme</b>", h2)
table([["Criterion", "Marks", "Section", "Evidence"],
       ["Data cleaning and splitting", "3", "2", "Quality checks, train/valid/test split, class balance chart"],
       ["State-of-the-art model comparison and performance analytics", "4", "3", "YOLOv8n results, per-class chart, comparison with 4 YOLO models and published work"],
       ["UI deployment and cross-platform accessibility", "4", "4", "Streamlit app with 4 input modes; laptop, phone and online access"],
       ["Code quality, GitHub repo, report", "4", "5", "One script per step, 10-page report"]],
      [0.32, 0.08, 0.1, 0.5])
story.append(PageBreak())

# ---------------- 1 ----------------
P("1. Problem and approach", h1)
P("<b>Problem.</b> On construction sites, supervisors check hardhats, vests and masks by walking around, which is "
  "slow and cannot be done all the time.")
P("<b>Goal.</b> Detect people, their PPE and missing PPE in real time from images, videos and cameras, show a warning "
  "when PPE is missing, and measure accuracy with precision, recall and mAP.")
P("<b>Why YOLO.</b> YOLO (You Only Look Once) looks at the whole image once and predicts all boxes and classes "
  "together, which makes it fast enough for live video.")
figure("figures/report/pipeline.png", "Figure 1. Project pipeline: six steps, one Python script each.")
P("<b>Dataset.</b> Construction Site Safety (Roboflow, Kaggle copy): 2,801 images with 10 classes: Hardhat, Mask, "
  "NO-Hardhat, NO-Mask, NO-Safety Vest, Person, Safety Cone, Safety Vest, machinery, vehicle. The NO-* classes mean "
  "the item is missing and trigger the warning.")
story.append(PageBreak())

# ---------------- 2 ----------------
P("2. Data cleaning and splitting (3 marks)", h1)
P("2.1 Cleaning (data_cleaning.py)", h2)
table([["Check", "Result"],
       ["Corrupt or unreadable images", "0 of 2,801"],
       ["Images without labels / labels without images", "0"],
       ["Invalid class numbers or box coordinates", "0"],
       ["Duplicate boxes in one file", "2 (removed)"],
       ["Images with no objects", "24 (kept as background examples)"]], [0.6, 0.4])
P("2.2 Splitting", h2)
P("The model learns from the training set, the validation set picks the best epoch, and the test set is used only "
  "for the final results.")
table([["Split", "Images", "Share", "Boxes"],
       ["Train", "2,605", "93%", "36,893"], ["Validation", "114", "4%", "697"], ["Test", "82", "3%", "760"]],
      [0.25, 0.25, 0.25, 0.25])
P("2.3 Class balance and preprocessing", h2)
figure("figures/report/class_balance.png", "Figure 2. Boxes per class: Person (9,872) outnumbers vehicle (1,628) about six to one.", 0.9)
P("Rare classes have fewer examples, so they are harder to detect. <b>Preprocessing:</b> images are 640 x 640; during "
  "training YOLO scales pixels to 0-1 and applies augmentation (mosaic, flips, colour changes, scaling).")
figure("figures/data_raw/sample_annotations.png", "Figure 3. Sample images with labelled boxes (red = missing PPE class).", 0.85)

# ---------------- 3 ----------------
P("3. State-of-the-art model comparison (4 marks)", h1)
P("3.1 Our model", h2)
table([["Setting", "Value"],
       ["Model", "YOLOv8n (nano), COCO pre-trained, fine-tuned on PPE images"],
       ["Epochs / image size / batch", "10 / 416 x 416 px / 16"],
       ["Hardware / training time", "Laptop CPU (AMD Ryzen 7 7840HS), 0.77 hours"]], [0.3, 0.7])
P("3.2 Metrics", h2)
table([["Metric", "Meaning"],
       ["Precision = TP / (TP + FP)", "Of the detections, how many are correct"],
       ["Recall = TP / (TP + FN)", "Of the real objects, how many were found"],
       ["IoU", "Overlap between predicted and true box; correct if at least 0.5"],
       ["mAP@0.5", "Average precision over the 10 classes at IoU 0.5 (main accuracy score)"],
       ["mAP@0.5:0.95", "Same, averaged over stricter overlap levels"],
       ["FPS", "Images processed per second (speed)"]], [0.3, 0.7])
P("3.3 Results on the 82 test images", h2)
table([["Precision", "Recall", "mAP@0.5", "mAP@0.5:0.95", "Speed (CPU)"],
       ["0.786", "0.530", "0.600", "0.299", "~25 FPS"]], [0.2] * 5)
figure("figures/report/baseline_per_class.png", "Figure 4. mAP@0.5 per class: two of the three missing-PPE classes score below 0.5.", 0.92)
P("Hardhat, machinery, Person and Safety Vest are detected well. NO-Mask, NO-Hardhat, Safety Cone and vehicle are "
  "harder: missing items are harder to see, and cones and vehicles are small or rare. Precision is higher than recall, "
  "so the model is usually right but misses some objects.")
P("3.4 Comparison with 4 state-of-the-art models (COCO benchmark)", h2)
table([["Model", "Released", "Params (M)", "FLOPs (B)", "COCO mAP@0.5:0.95"],
       ["YOLOv5s (yolov5su)", "2020", "9.1", "24.0", "43.0"],
       ["YOLOv8n (used here)", "2023", "3.2", "8.7", "37.3"],
       ["YOLOv8s", "2023", "11.2", "28.6", "44.9"],
       ["YOLO11n", "2024", "2.6", "6.5", "39.5"]], [0.28, 0.14, 0.16, 0.16, 0.26])
P("Larger models are more accurate but slower. YOLO11n is smaller and more accurate than YOLOv8n, so it is the next "
  "model to try. We chose YOLOv8n because it is fast. (Numbers from the Ultralytics documentation.)")
P("3.5 Comparison with published PPE results", h2)
table([["Study", "Model", "Dataset", "Training", "Precision", "Recall", "mAP@0.5"],
       ["Ciftci et al. (2024)", "YOLOv5n", "Same dataset", "20 epochs, 640 px, GPU", "0.759", "0.592", "0.660"],
       ["Ciftci et al. (2024)", "YOLOv8n", "Same dataset", "20 epochs, 640 px, GPU", "0.871", "0.654", "0.727"],
       ["Feng et al. (2024)", "YOLOv8s", "103,500 images", "200 iterations, GPU", "0.850", "0.605", "0.840"],
       ["This project", "YOLOv8n", "Same dataset", "10 epochs, 416 px, CPU", "0.786", "0.530", "0.600"]],
      [0.17, 0.11, 0.17, 0.22, 0.11, 0.1, 0.12])
P("<b>Why 0.600 vs 0.727 for the same model:</b> we trained for half the epochs (10 vs 20), with smaller images "
  "(416 vs 640 px) and on a CPU instead of a GPU.")

# ---------------- 4 ----------------
P("4. UI deployment and cross-platform accessibility (4 marks)", h1)
P("The interface is a <b>Streamlit web app</b> (app.py). Users open it in a web browser, so it works on any device "
  "without installing anything.")
table([["Part", "What it does"],
       ["Image tab", "Upload a photo; original and detected image side by side"],
       ["Camera tab", "Takes a photo with the device camera - works on phones"],
       ["Video tab", "Detection on an uploaded video, frame by frame"],
       ["Live webcam tab", "Live detection from the laptop webcam with FPS"],
       ["Warning banner", "Red warning naming the missing PPE; green when everyone is safe"],
       ["Sidebar", "Model selection, confidence slider, class filter"]], [0.25, 0.75])
figure("figures/report/access_paths.png", "Figure 5. Ways to open the app; the live webcam works only when the app runs on the laptop.", 0.85)
table([["Access", "How"],
       ["Same computer", "python -m streamlit run app.py, then open localhost:8501"],
       ["Phone / tablet on same Wi-Fi", "python -m streamlit run app.py --server.address 0.0.0.0, open the printed Network URL"],
       ["Anywhere online", "Deploy the GitHub repo on Streamlit Community Cloud (requirements.txt and packages.txt are ready)"]],
      [0.28, 0.72])

# ---------------- 5 ----------------
P("5. Code quality, GitHub repository and report (4 marks)", h1)
table([["File", "Purpose"],
       ["data_cleaning.py", "Checks images and labels, draws dataset figures"],
       ["train.py", "Trains the YOLO model"],
       ["evaluate.py", "Computes precision, recall, mAP and FPS on the test set"],
       ["app.py", "Streamlit web app (image, camera, video, live webcam)"],
       ["requirements.txt, packages.txt", "Packages needed to run locally and online"]], [0.3, 0.7])
P("<b>Report (10 pages):</b> Introduction, Literature review (6 papers from 2024), Methodology, Data cleaning and "
  "preprocessing, Results and discussion, State-of-the-art comparison, UI development and deployment, Conclusion, "
  "References.")

# ---------------- 6 ----------------
P("6. Literature review summary", h1)
table([["Paper", "Year", "Focus", "Key result"],
       ["Wang, Yeh, Liao - YOLOv9", "2024", "General detection", "PGI + GELAN: better parameter use"],
       ["Zhao et al. - RT-DETR (CVPR)", "2024", "Transformer detector", "53.1% AP at 108 FPS on T4, no NMS"],
       ["Wang et al. - YOLOv10 (NeurIPS)", "2024", "NMS-free YOLO", "1.8x faster than RT-DETR-R18 at similar AP"],
       ["Khanam, Hussain - YOLO11", "2024", "Architecture review", "C3k2, SPPF, C2PSA blocks"],
       ["Ciftci, Turkdamar, Ozturk", "2024", "PPE, same dataset", "YOLOv8n 0.727 mAP@0.5"],
       ["Feng, Miao, Zheng", "2024", "PPE, 103,500 images", "YOLOv8s 84.0% mAP@0.5, recall 60.5%"]],
      [0.32, 0.08, 0.25, 0.35])

# ---------------- 7 ----------------
P("7. Limitations and future work", h1)
table([["Limitation", "Planned improvement"],
       ["A normal cap is sometimes detected as a Hardhat", "Add photos of normal caps to the training data"],
       ["Short training (10 epochs on a CPU)", "Train longer on a GPU; try YOLO11n and YOLOv8s"],
       ["Small objects (cones, far-away workers) are missed", "Use larger image sizes"],
       ["Checks that PPE is present, not worn correctly", "Check that the hardhat is on the head"]], [0.5, 0.5])

doc = SimpleDocTemplate(str(out), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
                        topMargin=16 * mm, bottomMargin=18 * mm, title="Real-Time PPE Detection - Project Explanation")
doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
print("wrote", out)

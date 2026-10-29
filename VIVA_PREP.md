# Viva and demo prep: Real-Time PPE Detection

Team: Shantanu Vaidya (B2-20), Vineet Shah (B2-28), Mohammad Ejaz Mehendi (B2-25). Guide: Sweta Jain.

**One-line summary:** our app detects workers, hardhats, vests and masks in images, videos and live camera, and shows a
red warning when PPE is missing. We trained YOLOv8n and got 0.600 mAP@0.5 at about 25 FPS on a laptop CPU.

---

## 1. Data Cleaning & Splitting (3 marks)

**Dataset:** Construction Site Safety (Roboflow, from Kaggle), 2,801 images, 10 classes:
Hardhat, Mask, NO-Hardhat, NO-Mask, NO-Safety Vest, Person, Safety Cone, Safety Vest, machinery, vehicle.

**Cleaning (`data_cleaning.py`):**

| Check | Result |
|---|---|
| Corrupt images | 0 of 2,801 |
| Missing labels / labels without images | 0 |
| Wrong class numbers or box coordinates | 0 |
| Duplicate boxes | 2 (removed) |
| Images with no objects | 24 (kept as background examples) |

**Splitting:**

| Split | Images | Share | Used for |
|---|---|---|---|
| Train | 2,605 | 93% | Learning |
| Validation | 114 | 4% | Picking the best epoch |
| Test | 82 | 3% | Final results only |

**Likely questions:**
- *Class imbalance?* Yes. Person has 9,872 boxes, vehicle only 1,628 (about 6 to 1). Rare classes are harder to detect.
- *Preprocessing?* Images are 640x640. YOLO scales pixels to 0-1 and uses augmentation: mosaic (4 images in one), flips, colour changes, scaling.

---

## 2. Models Comparison & Performance Analytics (4 marks)

**Our model:** YOLOv8n (smallest, fastest YOLOv8), pre-trained on COCO, fine-tuned for 10 epochs at 416 px,
batch 16, on a laptop CPU (Ryzen 7 7840HS), 0.77 hours.

**Results on the 82 test images:**

| Precision | Recall | mAP@0.5 | mAP@0.5:0.95 | Speed (CPU) |
|---|---|---|---|---|
| 0.786 | 0.530 | 0.600 | 0.299 | ~25 FPS |

Best classes: Hardhat 0.78, machinery 0.77, Person 0.73, Safety Vest 0.73.
Weakest: NO-Mask 0.36, Safety Cone 0.34, vehicle 0.44, NO-Hardhat 0.47.

**4 state-of-the-art models (COCO benchmark, Ultralytics docs):**

| Model | Params (M) | COCO mAP@0.5:0.95 |
|---|---|---|
| YOLOv5s | 9.1 | 43.0 |
| YOLOv8n (ours) | 3.2 | 37.3 |
| YOLOv8s | 11.2 | 44.9 |
| YOLO11n | 2.6 | 39.5 |

**Published PPE results:**

| Study | Model | mAP@0.5 |
|---|---|---|
| Ciftci et al. 2024 (same dataset) | YOLOv5n | 0.660 |
| Ciftci et al. 2024 (same dataset) | YOLOv8n | 0.727 |
| Feng et al. 2024 (103,500 images) | YOLOv8s | 0.840 |
| **Ours** | YOLOv8n | **0.600** |

**Metrics in one line each:**
- **Precision:** of our detections, how many are correct.
- **Recall:** of the real objects, how many we found.
- **IoU:** box overlap; a detection is correct if IoU is at least 0.5.
- **mAP@0.5:** average precision over all 10 classes (main accuracy score).
- **FPS:** images per second (speed).

**Likely questions:**
- *Why YOLOv8n?* It is the fastest, so it runs live on a laptop without a GPU.
- *Why 0.600 when Ciftci et al. got 0.727 with the same model?* We trained half the epochs (10 vs 20), with smaller images (416 vs 640) and on a CPU, not a GPU.
- *Why is recall lower than precision?* The model is usually right when it detects something but misses some objects, mostly small ones. Lowering the confidence slider finds more.
- *Why are NO-Mask and NO-Hardhat weak?* A missing item (a bare head) is harder to see than a present one.

**Known failure:** a normal cap is sometimes detected as a Hardhat. Fix: add photos of normal caps to the training data.

---

## 3. UI Deployment & Cross-Platform Accessibility (4 marks)

**Demo order (about 3 minutes):**
1. `python -m streamlit run app.py`
2. Sidebar: move the confidence slider.
3. **Image** tab: pick a sample from `test_samples/violation/`. Show the red warning.
4. Pick a `compliant` sample. Show the green banner.
5. **Live webcam** tab: show live detection and FPS.
6. **Phone:** run with `--server.address 0.0.0.0`, open the Network URL on your phone, use the **Camera** tab.

**Cross-platform:** it runs in a web browser, so it works on Windows, Mac, Linux, Android and iOS with nothing to install.
Online deployment: GitHub repo + Streamlit Community Cloud.

---

## 4. Code Quality, GitHub, Report (4 marks)

- Files: `data_cleaning.py` (checks data), `train.py` (trains), `evaluate.py` (metrics), `app.py` (web app), `requirements.txt` (packages).
- Report: `Project_Report.pdf` / `.docx`, following the structure from Google Classroom.

**Push to GitHub:**
```bash
git init
git add .
git commit -m "PPE detection: YOLOv8n model and Streamlit app"
git branch -M main
git remote add origin https://github.com/<your-username>/ppe-vision.git
git push -u origin main
```

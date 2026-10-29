# Real-Time PPE Detection

Detects safety gear (hardhats, vests, masks) and its absence on construction sites from
images, video and a live camera, with YOLO models and a Streamlit web UI. Four state-of-the-art
YOLO models are compared on a cleaned, leakage-free split of the Construction Site Safety dataset.

## Pipeline

```
raw Roboflow export ──► data_cleaning.py ──► split_dataset.py ──► train.py ──► evaluate.py ──► app.py
 (2,801 images)         validate + plots      group-aware 70/15/15   4 models     metrics,      Streamlit UI
                                              split, fix labels                   figures
```

## Project structure

| Path | Purpose |
|---|---|
| `data_cleaning.py` | Validates images and labels (corrupt files, malformed/duplicate boxes, missing labels, leakage) and draws dataset figures |
| `split_dataset.py` | Groups augmented copies and video frames by source, then splits groups 70/15/15 so no source appears in two splits |
| `train.py` | Trains any list of YOLO models with identical settings |
| `evaluate.py` | Test-set precision, recall, mAP, size, FPS and violation-alarm metrics; comparison figures |
| `app.py` | Streamlit UI: image upload, phone/browser camera, video file, live webcam |
| `train_colab.ipynb` | Runs the whole pipeline on a free Colab GPU |
| `figures/` | Dataset and model-comparison figures used in the report |
| `test_samples/` | Held-out test images (compliant / violation / no people) for the demo |
| `baseline/` | First CPU-trained YOLOv8n (original split), kept only as a demo fallback |

## Dataset

Construction Site Safety (Roboflow), Kaggle copy:
https://www.kaggle.com/datasets/snehilsanyal/construction-site-safety-image-dataset-roboflow

Unzip it to `dataset/` (so that `dataset/train`, `dataset/valid`, `dataset/test` exist). Check the
dataset licence on the Kaggle/Roboflow page before redistributing it.

## Run it

```bash
pip install -r requirements.txt
python data_cleaning.py --data dataset/data.yaml --out figures/data_raw     # needs a data.yaml; see split_dataset.py for class names
python split_dataset.py --src dataset --dst dataset_clean
python data_cleaning.py --data dataset_clean/data.yaml --out figures/data_clean
python train.py --data dataset_clean/data.yaml --models yolov5su.pt yolov8n.pt yolov8s.pt yolo11n.pt --epochs 30 --imgsz 640
python evaluate.py --data dataset_clean/data.yaml
python -m streamlit run app.py
```

Training on CPU is slow; `train_colab.ipynb` does the same steps on a free GPU.

## Cross-platform access

- **Same Wi-Fi (phone, tablet, other laptop):** `python -m streamlit run app.py --server.address 0.0.0.0`,
  then open the "Network URL" it prints on the other device. Use the **Camera** tab on a phone.
- **Public URL:** push this repo to GitHub and deploy `app.py` on Streamlit Community Cloud
  (share.streamlit.io). `requirements.txt` and `packages.txt` are already set up. The trained
  `best.pt` files are small enough (6-20 MB) to commit. The **Live webcam** tab only works when the
  app runs locally; online, the **Camera** tab uses the visitor's own camera.

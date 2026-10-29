"""Train several YOLO models on the same dataset so they can be compared.

    python train.py --data dataset/data.yaml --models yolov8n.pt yolov8s.pt yolov5su.pt
"""
import argparse
from pathlib import Path

from ultralytics import YOLO


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--data", required=True, help="path to data.yaml (YOLO format)")
    p.add_argument("--models", nargs="+", default=["yolov8n.pt", "yolov8s.pt"])
    p.add_argument("--epochs", type=int, default=50)
    p.add_argument("--imgsz", type=int, default=640)
    p.add_argument("--batch", type=int, default=16)
    args = p.parse_args()

    for weights in args.models:
        name = Path(weights).stem
        print(f"\n=== Training {name} ===")
        YOLO(weights).train(
            data=args.data,
            epochs=args.epochs,
            imgsz=args.imgsz,
            batch=args.batch,
            project=str(Path("runs").resolve()),  # absolute, else Ultralytics nests it under runs/detect/
            name=name,
            exist_ok=True,
            patience=15,
        )


if __name__ == "__main__":
    main()

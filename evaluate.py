"""Compare every trained model in runs/ on the test split.

    python evaluate.py --data dataset_clean/data.yaml

Writes:
  results.csv            precision, recall, mAP, size, FPS, violation-alarm metrics
  results_per_class.csv  mAP@0.5 per class per model
  figures/comparison/    bar chart, accuracy-vs-speed plot, per-class heatmap
"""
import argparse
import time
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import torch
import yaml
from ultralytics import YOLO
from ultralytics.utils.torch_utils import get_flops

IMG_EXT = {".jpg", ".jpeg", ".png", ".bmp"}
VIOLATION_PREFIX = "NO-"


def split_images(data_yaml, split):
    cfg = yaml.safe_load(Path(data_yaml).read_text(encoding="utf-8"))
    root = Path(cfg.get("path", Path(data_yaml).parent))
    folder = root / cfg[split]
    return sorted(f for f in folder.rglob("*") if f.suffix.lower() in IMG_EXT)


def measure_fps(model, imgs, imgsz, n=50):
    imgs = imgs[:n]
    model.predict(str(imgs[0]), imgsz=imgsz, verbose=False)  # warm-up
    start = time.perf_counter()
    for im in imgs:
        model.predict(str(im), imgsz=imgsz, verbose=False)
    return len(imgs) / (time.perf_counter() - start)


def violation_alarm(model, imgs, imgsz, conf=0.5):
    """Image-level check: does the model raise an alarm exactly when a NO-* object is present?"""
    viol_ids = {i for i, n in model.names.items() if n.startswith(VIOLATION_PREFIX)}
    tp = fp = fn = tn = 0
    for img in imgs:
        lbl = img.parent.parent / "labels" / f"{img.stem}.txt"
        lines = lbl.read_text().split("\n") if lbl.exists() else []
        truth = any(l.split() and int(l.split()[0]) in viol_ids for l in lines)
        boxes = model.predict(str(img), imgsz=imgsz, conf=conf, verbose=False)[0].boxes
        pred = any(int(c) in viol_ids for c in boxes.cls)
        tp += truth and pred
        fp += pred and not truth
        fn += truth and not pred
        tn += not truth and not pred
    return {"alarm_precision": round(tp / max(tp + fp, 1), 3),
            "alarm_recall": round(tp / max(tp + fn, 1), 3),
            "alarm_accuracy": round((tp + tn) / max(len(imgs), 1), 3)}


def plot(df, per_class, out):
    out.mkdir(parents=True, exist_ok=True)
    models = df["model"]

    fig, ax = plt.subplots(figsize=(8, 4))
    x = range(len(df))
    for i, col in enumerate(["precision", "recall", "mAP@0.5", "mAP@0.5:0.95"]):
        bars = ax.bar([j + (i - 1.5) * 0.2 for j in x], df[col], 0.2, label=col)
        ax.bar_label(bars, fmt="%.2f", fontsize=7, padding=1)
    ax.set_xticks(list(x), models)
    ax.set_ylim(0, 1)
    ax.set_title("Detection metrics on the test split")
    ax.legend(frameon=False, ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.1))
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(out / "metrics_bar.png", dpi=150)

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.scatter(df["FPS"], df["mAP@0.5"], s=df["params_M"] * 25 + 20, alpha=0.7)
    for _, r in df.iterrows():
        ax.annotate(r["model"], (r["FPS"], r["mAP@0.5"]), xytext=(6, 4), textcoords="offset points", fontsize=9)
    ax.set(xlabel=f"FPS ({df['device'].iloc[0]})", ylabel="mAP@0.5",
           title="Accuracy vs speed (marker size = parameters)")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(out / "accuracy_vs_speed.png", dpi=150)

    fig, ax = plt.subplots(figsize=(1.6 * len(per_class.columns) + 3, 5))
    im = ax.imshow(per_class.values, cmap="viridis", vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(range(len(per_class.columns)), per_class.columns)
    ax.set_yticks(range(len(per_class.index)), per_class.index)
    for i in range(per_class.shape[0]):
        for j in range(per_class.shape[1]):
            v = per_class.values[i, j]
            ax.text(j, i, f"{v:.2f}", ha="center", va="center", color="white" if v < 0.6 else "black", fontsize=8)
    fig.colorbar(im, ax=ax, label="mAP@0.5")
    ax.set_title("Per-class mAP@0.5")
    fig.tight_layout()
    fig.savefig(out / "per_class_heatmap.png", dpi=150)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--data", required=True)
    p.add_argument("--imgsz", type=int, default=None, help="default: the size each model was trained at")
    args = p.parse_args()

    cfg = yaml.safe_load(Path(args.data).read_text(encoding="utf-8"))
    split = "test" if cfg.get("test") else "val"
    imgs = split_images(args.data, split)
    device = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU"

    rows, per_class = [], {}
    for best in sorted(Path("runs").glob("*/weights/best.pt")):
        name = best.parent.parent.name
        print(f"Evaluating {name} on '{split}' split ({len(imgs)} images)")
        model = YOLO(str(best))
        imgsz = args.imgsz or model.overrides.get("imgsz", 640)
        m = model.val(data=args.data, split=split, imgsz=imgsz, verbose=False, plots=False)
        params = sum(p.numel() for p in model.model.parameters())
        gflops = get_flops(model.model, imgsz)
        rows.append({
            "model": name,
            "precision": round(m.box.mp, 3),
            "recall": round(m.box.mr, 3),
            "mAP@0.5": round(m.box.map50, 3),
            "mAP@0.5:0.95": round(m.box.map, 3),
            "params_M": round(params / 1e6, 2),
            "GFLOPs": round(gflops, 1),
            "imgsz": imgsz,
            "device": device,
            "FPS": round(measure_fps(model, imgs, imgsz), 1),
            **violation_alarm(model, imgs, imgsz),
        })
        per_class[name] = {model.names[int(c)]: round(m.box.class_result(i)[2], 3)
                           for i, c in enumerate(m.box.ap_class_index)}

    if not rows:
        print("No trained models found in runs/*/weights/best.pt")
        return
    df = pd.DataFrame(rows)
    pc = pd.DataFrame(per_class)
    df.to_csv("results.csv", index=False)
    pc.to_csv("results_per_class.csv")
    plot(df, pc, Path("figures/comparison"))
    print("\n", df.to_string(index=False))
    print("\nPer-class mAP@0.5:\n", pc.to_string())
    print("\nSaved results.csv, results_per_class.csv and figures/comparison/")


if __name__ == "__main__":
    main()

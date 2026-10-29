"""Data cleaning, validation and analysis for a YOLO-format dataset.

    python data_cleaning.py --data dataset/data.yaml --out figures/data_raw
    python data_cleaning.py --data dataset_clean/data.yaml --out figures/data_clean
    (--fix also repairs labels in place)

Checks: corrupt images, images without labels, labels without images, malformed
label lines, out-of-range class IDs and coordinates, zero-size boxes, duplicate
boxes, and duplicate images across splits (data leakage).
Writes figures (class distribution, split sizes, box statistics, sample grid)
and cleaning_report.json to --out.
"""
import argparse
import hashlib
import json
import random
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import yaml
from PIL import Image, ImageDraw

IMG_EXT = {".jpg", ".jpeg", ".png", ".bmp"}
SPLITS = {"train": "train", "val": "valid", "test": "test"}


def check_label_file(path, nc):
    """Return (valid_boxes, list of problems) for one label file."""
    boxes, problems, seen = [], [], set()
    for n, line in enumerate(path.read_text().splitlines(), 1):
        parts = line.split()
        if not parts:
            continue
        if len(parts) != 5:
            problems.append(f"line {n}: expected 5 values, got {len(parts)}")
            continue
        try:
            cls, x, y, w, h = int(parts[0]), *map(float, parts[1:])
        except ValueError:
            problems.append(f"line {n}: not numeric")
            continue
        if not 0 <= cls < nc:
            problems.append(f"line {n}: class {cls} out of range")
        elif not all(0 <= v <= 1 for v in (x, y, w, h)):
            problems.append(f"line {n}: coordinates outside [0,1]")
        elif w <= 0 or h <= 0:
            problems.append(f"line {n}: zero-size box")
        elif (cls, x, y, w, h) in seen:
            problems.append(f"line {n}: duplicate box")
        else:
            seen.add((cls, x, y, w, h))
            boxes.append((cls, x, y, w, h))
    return boxes, problems


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--data", required=True)
    p.add_argument("--fix", action="store_true", help="rewrite labels without bad lines, drop corrupt images")
    p.add_argument("--out", default="figures/data", help="folder for figures and cleaning_report.json")
    args = p.parse_args()

    cfg = yaml.safe_load(Path(args.data).read_text(encoding="utf-8"))
    root, names = Path(args.data).parent, cfg["names"]
    nc = len(names)
    figs = Path(args.out)
    figs.mkdir(parents=True, exist_ok=True)

    report = {"splits": {}, "issues": defaultdict(list), "fixed": args.fix}
    class_counts = {s: Counter() for s in SPLITS}
    boxes_per_img, box_areas, hashes = [], [], defaultdict(list)
    all_boxes = {}

    for split, folder in SPLITS.items():
        img_dir, lbl_dir = root / folder / "images", root / folder / "labels"
        imgs = {f.stem: f for f in img_dir.iterdir() if f.suffix.lower() in IMG_EXT}
        lbls = {f.stem: f for f in lbl_dir.glob("*.txt")}

        for stem in sorted(set(lbls) - set(imgs)):
            report["issues"]["label_without_image"].append(f"{split}/{stem}")
        for stem, img in sorted(imgs.items()):
            try:
                with Image.open(img) as im:
                    im.verify()
            except Exception as e:
                report["issues"]["corrupt_image"].append(f"{split}/{img.name}: {e}")
                if args.fix:
                    img.unlink()
                continue
            hashes[hashlib.md5(img.read_bytes()).hexdigest()].append(f"{split}/{img.name}")

            if stem not in lbls:
                report["issues"]["image_without_label"].append(f"{split}/{img.name}")
                boxes = []
            else:
                boxes, problems = check_label_file(lbls[stem], nc)
                for pr in problems:
                    report["issues"]["bad_label_line"].append(f"{split}/{stem}.txt {pr}")
                if problems and args.fix:
                    lbls[stem].write_text("".join(f"{c} {x:.6f} {y:.6f} {w:.6f} {h:.6f}\n"
                                                  for c, x, y, w, h in boxes))
                if not boxes:
                    report["issues"]["empty_label (background image)"].append(f"{split}/{img.name}")

            all_boxes[img] = boxes
            boxes_per_img.append(len(boxes))
            for c, _, _, w, h in boxes:
                class_counts[split][names[c]] += 1
                box_areas.append(w * h)
        report["splits"][split] = {"images": len(imgs), "instances": sum(class_counts[split].values())}

    dupes = [v for v in hashes.values() if len(v) > 1]
    cross = [v for v in dupes if len({x.split("/")[0] for x in v}) > 1]
    report["issues"]["duplicate_images"] = dupes
    report["issues"]["duplicates_across_splits (leakage)"] = cross

    total = sum(r["images"] for r in report["splits"].values())
    for r in report["splits"].values():
        r["percent"] = round(100 * r["images"] / total, 1)
    report["class_counts"] = {s: dict(c) for s, c in class_counts.items()}
    report["summary"] = {k: len(v) for k, v in report["issues"].items()}

    # ---- figures ----
    fig, ax = plt.subplots(figsize=(10, 4.5))
    width = 0.27
    for i, split in enumerate(SPLITS):
        ax.bar([j + (i - 1) * width for j in range(nc)], [class_counts[split][n] for n in names],
               width, label=split)
    ax.set_xticks(range(nc), names, rotation=35, ha="right")
    ax.set_ylabel("Instances")
    ax.set_title("Class distribution per split")
    ax.legend(frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(figs / "class_distribution.png", dpi=150)

    fig, axes = plt.subplots(1, 2, figsize=(10, 3.8))
    axes[0].hist(boxes_per_img, bins=30, color="#4C72B0")
    axes[0].set(title="Boxes per image", xlabel="Boxes", ylabel="Images")
    axes[1].hist([a * 100 for a in box_areas], bins=50, color="#55A868")
    axes[1].set(title="Box size (% of image area)", xlabel="% of image", ylabel="Boxes", yscale="log")
    for a in axes:
        a.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(figs / "box_statistics.png", dpi=150)

    fig, ax = plt.subplots(figsize=(5, 3))
    ax.bar(list(report["splits"]), [r["images"] for r in report["splits"].values()], color="#8172B2")
    for i, r in enumerate(report["splits"].values()):
        ax.text(i, r["images"], f'{r["images"]} ({r["percent"]}%)', ha="center", va="bottom")
    ax.set(title="Dataset split", ylabel="Images")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(figs / "split_sizes.png", dpi=150)

    random.seed(0)
    picks = random.sample([k for k, v in all_boxes.items() if v], 6)
    fig, axes = plt.subplots(2, 3, figsize=(12, 8))
    for ax, img_path in zip(axes.flat, picks):
        im = Image.open(img_path).convert("RGB")
        d, (W, H) = ImageDraw.Draw(im), im.size
        for c, x, y, w, h in all_boxes[img_path]:
            col = "red" if names[c].startswith("NO-") else "lime"
            d.rectangle([(x - w / 2) * W, (y - h / 2) * H, (x + w / 2) * W, (y + h / 2) * H], outline=col, width=3)
            d.text(((x - w / 2) * W + 3, (y - h / 2) * H + 2), names[c], fill=col)
        ax.imshow(im)
        ax.axis("off")
    fig.suptitle("Sample ground-truth annotations (red = violation class)")
    fig.tight_layout()
    fig.savefig(figs / "sample_annotations.png", dpi=120)

    (figs / "cleaning_report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps({"splits": report["splits"], "issues": report["summary"]}, indent=2))
    print(f"Figures and cleaning_report.json saved to {figs}/")


if __name__ == "__main__":
    main()

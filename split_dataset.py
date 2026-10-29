"""Clean the raw dataset and re-split it without leakage.

    python split_dataset.py --src dataset --dst dataset_clean

Why: the Roboflow export has 2,801 images but only ~700 source photos. Each source
appears up to 10 times as augmented copies (same name before ".rf."), and video
frames (names like "construction-4-_mp4-19_jpg") are near-identical. The original
93/4/3 split puts copies of the same photo/video in both train and test, which
inflates test scores.

What it does:
  1. Groups images by source photo, and video frames by source video.
  2. Splits the GROUPS 70/15/15 (seeded), so no source appears in two splits.
  3. Keeps all augmented copies in train (free augmentation), but only one copy
     per source photo in val/test, so every evaluation image is independent.
  4. Drops corrupt images and rewrites labels without malformed/duplicate lines.
"""
import argparse
import random
import re
import shutil
from collections import defaultdict
from pathlib import Path

from PIL import Image

from data_cleaning import IMG_EXT, check_label_file

NAMES = ['Hardhat', 'Mask', 'NO-Hardhat', 'NO-Mask', 'NO-Safety Vest', 'Person',
         'Safety Cone', 'Safety Vest', 'machinery', 'vehicle']
RATIOS = {"train": 0.70, "valid": 0.15, "test": 0.15}


def source_of(name):
    """Original photo name, i.e. the part before Roboflow's '.rf.<hash>'."""
    return name.split(".rf.")[0]


def group_of(name):
    """Video frames share their video as a group; other images group by source photo."""
    m = re.match(r"(.+_mp4)-\d+_jpg$", source_of(name))
    return m.group(1) if m else source_of(name)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--src", default="dataset")
    p.add_argument("--dst", default="dataset_clean")
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args()
    src, dst = Path(args.src), Path(args.dst)

    groups = defaultdict(list)  # group -> [(image, label)]
    dropped = 0
    for split in ["train", "valid", "test"]:
        for img in sorted((src / split / "images").iterdir()):
            if img.suffix.lower() not in IMG_EXT:
                continue
            try:
                with Image.open(img) as im:
                    im.verify()
            except Exception:
                dropped += 1
                continue
            groups[group_of(img.name)].append((img, src / split / "labels" / f"{img.stem}.txt"))

    keys = sorted(groups)
    random.Random(args.seed).shuffle(keys)
    n_imgs = sum(len(v) for v in groups.values())
    assign, filled = {}, {"train": 0, "valid": 0, "test": 0}
    for k in keys:  # fill test, then valid, then train, by image count
        target = next((s for s in ["test", "valid"] if filled[s] < RATIOS[s] * n_imgs), "train")
        assign[k] = target
        filled[target] += len(groups[k])

    if dst.exists():
        shutil.rmtree(dst)
    stats = {s: {"images": 0, "groups": 0, "fixed_labels": 0} for s in RATIOS}
    for k, items in groups.items():
        split = assign[k]
        if split != "train":  # one copy per source photo in val/test
            seen, kept = set(), []
            for img, lbl in items:
                if source_of(img.name) not in seen:
                    seen.add(source_of(img.name))
                    kept.append((img, lbl))
            items = kept
        stats[split]["groups"] += 1
        for img, lbl in items:
            (dst / split / "images").mkdir(parents=True, exist_ok=True)
            (dst / split / "labels").mkdir(parents=True, exist_ok=True)
            shutil.copy2(img, dst / split / "images" / img.name)
            boxes, problems = check_label_file(lbl, len(NAMES)) if lbl.exists() else ([], [])
            stats[split]["fixed_labels"] += bool(problems)
            (dst / split / "labels" / lbl.name).write_text(
                "".join(f"{c} {x:.6f} {y:.6f} {w:.6f} {h:.6f}\n" for c, x, y, w, h in boxes))
            stats[split]["images"] += 1

    (dst / "data.yaml").write_text(
        "train: train/images\nval: valid/images\ntest: test/images\n\n"
        f"nc: {len(NAMES)}\nnames: {NAMES}\n")
    print(f"{len(groups)} source groups, {dropped} corrupt images dropped")
    for s, v in stats.items():
        print(f"  {s:5s}: {v['images']:5d} images from {v['groups']:4d} groups, {v['fixed_labels']} labels repaired")
    print(f"Wrote {dst}/ with data.yaml")


if __name__ == "__main__":
    main()

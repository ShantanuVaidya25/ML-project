"""Streamlit UI: image, video and webcam PPE detection.

    python -m streamlit run app.py
"""
import os
import tempfile
import time
from collections import Counter
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
import streamlit as st
from PIL import Image
from ultralytics import YOLO

st.set_page_config(page_title="PPE Detection", page_icon=":material/health_and_safety:", layout="wide")


@st.cache_resource
def load(path):
    return YOLO(path)


def is_violation(name):
    return name.upper().startswith("NO-")


# ---------- sidebar ----------
weights = (sorted(str(p) for p in Path("runs").glob("*/weights/best.pt"))
           + sorted(str(p) for p in Path("baseline").glob("*/weights/best.pt")))
with st.sidebar:
    st.header("Settings")
    model_path = st.selectbox("Model", weights) if weights else st.text_input("Model path", "yolov8n.pt")
    model = load(model_path)
    conf = st.slider("Confidence threshold", 0.1, 0.9, 0.5, 0.05,
                     help="Raise it to cut false alarms (e.g. a cap read as a hardhat).")
    shown = st.multiselect("Classes to show", list(model.names.values()), default=list(model.names.values()))
    class_ids = [i for i, n in model.names.items() if n in shown]

    results_csv = Path("results.csv")
    if results_csv.exists():
        st.divider()
        st.subheader("Model comparison")
        st.dataframe(pd.read_csv(results_csv).set_index("model"), width="stretch")


# ---------- detection helpers ----------
def detect(frame_bgr):
    """Return annotated RGB frame and list of detected class names."""
    res = model.predict(frame_bgr, conf=conf, classes=class_ids or None, verbose=False)[0]
    names = [res.names[int(c)] for c in res.boxes.cls]
    return cv2.cvtColor(res.plot(), cv2.COLOR_BGR2RGB), names


def status(names, fps=None):
    """Safety banner, metric row and per-class counts for one frame."""
    counts = Counter(names)
    violations = sorted({n for n in counts if is_violation(n)})
    if violations:
        st.error("VIOLATION: " + ", ".join(violations), icon=":material/warning:")
    elif counts.get("Person"):
        st.success("No violations detected", icon=":material/check_circle:")
    else:
        st.info("No people detected", icon=":material/info:")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Detections", len(names))
    c2.metric("People", counts.get("Person", 0))
    c3.metric("Violations", sum(v for n, v in counts.items() if is_violation(n)))
    c4.metric("Inference FPS", f"{fps:.1f}" if fps else "-")
    if counts:
        st.bar_chart(pd.Series(counts, name="count"), height=160)


def stream(cap):
    """Run detection frame by frame, updating the view in place."""
    view, panel = st.empty(), st.empty()
    try:
        while cap.isOpened():
            ok, frame = cap.read()
            if not ok:
                break
            t0 = time.perf_counter()
            img, names = detect(frame)
            fps = 1 / (time.perf_counter() - t0)
            view.image(img, channels="RGB", width="stretch")
            with panel.container():
                status(names, fps)
    finally:
        cap.release()


# ---------- page ----------
st.title(":material/health_and_safety: Real-Time PPE Detection")
st.caption(f"Model: `{model_path}` | confidence >= {conf:.2f}")

tab_img, tab_snap, tab_vid, tab_cam = st.tabs([":material/image: Image", ":material/photo_camera: Camera",
                                              ":material/movie: Video", ":material/videocam: Live webcam"])

with tab_img:
    samples = sorted(Path("test_samples").rglob("*.jp*g"))
    left, right = st.columns([2, 1])
    up = left.file_uploader("Upload an image", type=["jpg", "jpeg", "png"], key="img")
    pick = right.selectbox("...or pick a sample", [None] + samples,
                           format_func=lambda p: "-" if p is None else f"{p.parent.name}/{p.name[:18]}")
    src = up or pick
    if src:
        pil = Image.open(src).convert("RGB")
        img, names = detect(cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR))
        a, b = st.columns(2)
        a.image(pil, caption="Original", width="stretch")
        b.image(img, caption="Detected", width="stretch")
        status(names)

with tab_snap:
    st.caption("Takes a photo with the camera of whatever device opened this page (works on phones too).")
    shot = st.camera_input("Take a photo")
    if shot:
        img, names = detect(cv2.cvtColor(np.array(Image.open(shot).convert("RGB")), cv2.COLOR_RGB2BGR))
        st.image(img, caption="Detected", width="stretch")
        status(names)

with tab_vid:
    up = st.file_uploader("Upload a video", type=["mp4", "avi", "mov"], key="vid")
    if up and st.button("Run on video", type="primary", icon=":material/play_arrow:"):
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=Path(up.name).suffix)
        tmp.write(up.read())
        tmp.close()
        try:
            stream(cv2.VideoCapture(tmp.name))
        finally:
            os.unlink(tmp.name)

with tab_cam:
    st.caption("Continuous detection from the camera of the computer running the app. "
               "When the app is hosted online, use the Camera tab instead.")
    if st.toggle("Start webcam"):
        cap = cv2.VideoCapture(0)
        if cap.isOpened():
            stream(cap)
        else:
            st.error("Could not open webcam.")

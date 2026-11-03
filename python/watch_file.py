#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""watch_file.py -- watch a local video file (cross-platform, OpenCV).

Same pipeline as watch_screen.py, but sampled from a decoded file:
  decode -> sample at N fps -> state track -> key frames -> optional OCR -> residual.

Options:
  --fps 4               sampling rate (frames per second of video time)
  --states-per-sec 1    state track rate
  --keys 8              max key frames
  --gap 20              min seconds between key frames
  --no-ocr
  --dir <path>
"""
import argparse
import json
import os
import sys
import tempfile

try:
    import cv2
    import numpy as np
except Exception:
    print(json.dumps({"ok": False, "error": "opencv-python and numpy are required: pip install opencv-python numpy"}))
    sys.exit(0)

W, H = 320, 180


def try_ocr(path):
    try:
        from ocr_win import ocr
        r = ocr(path)
        return (r.get("text") or "")[:120]
    except Exception:
        return ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--fps", type=float, default=4)
    ap.add_argument("--states-per-sec", type=float, default=1)
    ap.add_argument("--keys", type=int, default=8)
    ap.add_argument("--gap", type=float, default=20)
    ap.add_argument("--threshold", type=float, default=1.0)
    ap.add_argument("--no-ocr", action="store_true")
    ap.add_argument("--dir", default=None)
    a = ap.parse_args()

    cap = cv2.VideoCapture(a.path)
    if not cap.isOpened():
        print(json.dumps({"ok": False, "error": "cannot open: %s" % a.path}))
        return
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    dur = total / fps
    step = max(int(round(fps / max(a.fps, 0.1))), 1)
    out_dir = a.dir or os.path.join(tempfile.gettempdir(), "dsh-njs-watch")
    os.makedirs(out_dir, exist_ok=True)

    prev = None
    buf = np.zeros((H, W), dtype=np.float32)
    states, cand = [], []
    next_state = 0.0
    last_bottom = None
    last_ocr_t = -1e9
    idx = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if idx % step == 0:
            g = cv2.cvtColor(cv2.resize(frame, (W, H)), cv2.COLOR_BGR2GRAY).astype(np.float32)
            t = idx / fps
            if prev is not None:
                d = np.abs(g - prev)
                energy = float(d.mean())
                buf = np.maximum(buf * 0.85, d)
                if t >= next_state:
                    bottom = float(g[int(H * 0.72):].mean())
                    st = {"t": round(t, 2), "energy": round(energy, 2),
                          "lum": round(float(g.mean()), 1), "bottom": round(bottom, 1)}
                    if (not a.no_ocr and last_bottom is not None and abs(bottom - last_bottom) > 2.0
                            and t - last_ocr_t > 0.6):
                        tp = os.path.join(out_dir, "t_%06.2f.png" % t)
                        ok2, b2 = cv2.imencode(".png", frame)
                        if ok2:
                            open(tp, "wb").write(b2.tobytes())
                            txt = try_ocr(tp)
                            try:
                                os.remove(tp)
                            except Exception:
                                pass
                            if txt:
                                st["text"] = txt
                        last_ocr_t = t
                    last_bottom = bottom
                    states.append(st)
                    next_state = t + 1.0 / max(a.states_per_sec, 0.1)
                if energy >= a.threshold:
                    cand.append((t, energy, frame.copy()))
            prev = g
        idx += 1
    cap.release()

    eff_gap = a.gap
    if dur > 0 and a.keys > 0 and eff_gap * a.keys > dur:
        eff_gap = max(0.5, dur / float(a.keys + 1))
    cand.sort(key=lambda x: -x[1])
    picked = []
    for t, e, fr in cand:
        if all(abs(t - p[0]) >= eff_gap for p in picked):
            picked.append((t, e, fr))
        if len(picked) >= a.keys:
            break
    picked.sort(key=lambda x: x[0])
    keys = []
    for i, (t, e, fr) in enumerate(picked):
        kp = os.path.join(out_dir, "key_%02d_%06.1f.png" % (i, t))
        ok2, b2 = cv2.imencode(".png", fr)
        if ok2:
            open(kp, "wb").write(b2.tobytes())
        keys.append({"t": round(t, 1), "energy": round(e, 2), "png": kp})

    peak = float(buf.max()) or 1.0
    residue = os.path.join(out_dir, "residue.png")
    ok2, b3 = cv2.imencode(".png", np.clip(buf / peak * 255.0, 0, 255).astype(np.uint8))
    if ok2:
        open(residue, "wb").write(b3.tobytes())

    res = {
        "ok": True,
        "mode": "file-sampled",
        "how": "one sample every %.2f s; state track %.1f/s" % (1.0 / max(a.fps, 0.1), a.states_per_sec),
        "coverage_pct": round(min(100.0, 100.0 * len(states) / max(dur * max(a.states_per_sec, 0.1), 1)), 1),
        "ocr": "off" if a.no_ocr else "on",
        "ocr_hits": sum(1 for s in states if s.get("text")),
        "file": a.path,
        "duration": round(dur, 1),
        "frames": total,
        "key_count": len(keys),
        "gap": round(eff_gap, 2),
        "keys": keys,
        "states": states,
        "residue": residue,
        "dir": out_dir,
    }
    print(json.dumps(res, ensure_ascii=False))


if __name__ == "__main__":
    main()

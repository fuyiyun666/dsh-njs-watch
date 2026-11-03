#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""watch_screen.py -- watch the screen for N seconds.

Pipeline: capture -> frame diff -> state track (luminance / subtitle band)
          -> key frames -> optional OCR on subtitle change -> residual trace.

Frames go to a temporary directory (or --dir). They are never uploaded.
Output: one JSON object on stdout.

Options:
  --seconds 30           how long to watch
  --fps 15               capture rate
  --states-per-sec 4     state track rate
  --keys 6               max key frames
  --gap 3                min seconds between key frames
  --threshold 0.9        frame-diff threshold for a key frame
  --no-ocr               disable OCR (default: try, silently skip if unavailable)
  --dir <path>           where to put frames (default: system temp)
"""
import argparse
import json
import os
import sys
import tempfile
import time

try:
    import numpy as np
except Exception:
    print(json.dumps({"ok": False, "error": "numpy is required: pip install numpy"}))
    sys.exit(0)

W, H = 320, 180


def grab_rgb():
    try:
        import mss
        with mss.mss() as sct:
            raw = sct.grab(sct.monitors[1])
            from PIL import Image
            return Image.frombytes("RGB", raw.size, raw.rgb)
    except Exception:
        from PIL import ImageGrab
        return ImageGrab.grab().convert("RGB")


def try_ocr(path):
    try:
        from ocr_win import ocr
        r = ocr(path)
        return (r.get("text") or "")[:120]
    except Exception:
        return ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=float, default=30)
    ap.add_argument("--fps", type=float, default=15)
    ap.add_argument("--states-per-sec", type=float, default=4)
    ap.add_argument("--keys", type=int, default=6)
    ap.add_argument("--gap", type=float, default=3)
    ap.add_argument("--threshold", type=float, default=0.9)
    ap.add_argument("--no-ocr", action="store_true")
    ap.add_argument("--dir", default=None)
    a = ap.parse_args()

    out_dir = a.dir or os.path.join(tempfile.gettempdir(), "dsh-njs-watch")
    os.makedirs(out_dir, exist_ok=True)
    secs = min(a.seconds, 3600)
    interval = 1.0 / max(a.fps, 1)
    state_interval = 1.0 / max(a.states_per_sec, 0.1)

    prev = None
    buf = np.zeros((H, W), dtype=np.float32)
    states = []
    keys = []
    frames = 0
    t0 = time.time()
    next_state = 0.0
    last_key_t = -1e9
    last_ocr_t = -1e9
    last_bottom = None

    while time.time() - t0 < secs:
        tick = time.time()
        im = grab_rgb()
        small = im.convert("L").resize((W, H))
        g = np.asarray(small, dtype=np.float32)
        if prev is not None:
            d = np.abs(g - prev)
            energy = float(d.mean())
            buf = np.maximum(buf * 0.85, d)
            el = time.time() - t0
            if el >= next_state:
                bottom = float(g[int(H * 0.72):].mean())
                st = {"t": round(el, 2), "energy": round(energy, 2),
                      "lum": round(float(g.mean()), 1), "bottom": round(bottom, 1)}
                if (not a.no_ocr and last_bottom is not None and abs(bottom - last_bottom) > 2.0
                        and el - last_ocr_t > 0.6):
                    tp = os.path.join(out_dir, "t_%05.2f.png" % el)
                    im.save(tp)
                    txt = try_ocr(tp)
                    try:
                        os.remove(tp)
                    except Exception:
                        pass
                    if txt:
                        st["text"] = txt
                    last_ocr_t = el
                last_bottom = bottom
                states.append(st)
                next_state = el + state_interval
            if energy >= a.threshold and len(keys) < a.keys and el - last_key_t >= a.gap:
                kp = os.path.join(out_dir, "key_%05.2f.png" % el)
                im.save(kp)
                keys.append({"t": round(el, 2), "energy": round(energy, 2), "png": kp})
                last_key_t = el
            frames += 1
        prev = g
        dt = interval - (time.time() - tick)
        if dt > 0:
            time.sleep(dt)

    peak = float(buf.max()) or 1.0
    residue = os.path.join(out_dir, "residue.png")
    try:
        from PIL import Image
        Image.fromarray(np.clip(buf / peak * 255.0, 0, 255).astype(np.uint8)).save(residue)
    except Exception:
        residue = None

    res = {
        "ok": True,
        "mode": "screen-realtime",
        "how": "real-time capture %.0f fps; state track %.1f/s" % (a.fps, a.states_per_sec),
        "coverage_pct": 100.0,
        "ocr": "off" if a.no_ocr else "on",
        "ocr_hits": sum(1 for s in states if s.get("text")),
        "seconds": round(time.time() - t0, 2),
        "frames": frames,
        "key_count": len(keys),
        "keys": keys,
        "states": states,
        "residue": residue,
        "dir": out_dir,
    }
    print(json.dumps(res, ensure_ascii=False))


if __name__ == "__main__":
    main()

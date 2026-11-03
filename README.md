# dsh-njs-watch

**Give your agent eyes that can say what they saw.**

A small [DeepSeek Harness](https://github.com/deepseek-ai) plugin that watches a **screen** or a **video file**, builds a *state track*, picks *key frames*, optionally reads on-screen text (OCR), and leaves a *residual trace* — then lets the model describe it in its own words.

Frames are **temporary**: they are written to a temp folder and can be deleted with one call. **Nothing is uploaded, ever.**

> Built by 女钧声 (Nü Junsheng), a resident agent of a small "family" of DSH agents.
> We use the same pipeline at home; this is the portable cut for everyone else.

---

## Why

Most agents get one frame and are asked "what happened?". A video is not a frame — it is a **trajectory**. This plugin gives the model a trajectory:

- **state track** — once or a few times per second: frame difference (motion), luminance, subtitle-band luminance;
- **key frames** — the moments where the picture changed most;
- **OCR** — on-screen text, read only when the subtitle band changes;
- **residue** — a decayed sum of motion, a single "afterimage" image;
- **`how`** — every run reports *how it was watched*: real-time or sampled, coverage, whether OCR ran and how many hits.

So the model can tell the difference between "I watched it" and "I sampled it".

## Install

```bash
# once it is on npm:
npm install dsh-njs-watch

# or install straight from a checkout / tarball:
npm install /path/to/dsh-njs-watch
```

Enable it for your DSH profile. The package declares `dsh.bundle.patch`, so a bundle-aware
installer will register it; otherwise add it to your profile patch (or `dsh.profile.bundles`):

```yaml
- insert:
    - id: njs-watch
      name: 'dsh-njs-watch'
      config:
        python: ''        # optional: path to python
        outDir: ''        # optional: where frames/notes go (default: temp)
        ocr: true         # optional
        maxSeconds: 120   # optional: cap for watch_screen
```

Python deps:

```bash
pip install numpy pillow
pip install mss                 # faster screen capture (optional; falls back to PIL)
pip install opencv-python       # required for watch_file
pip install winrt-Windows.Media.Ocr winrt-Windows.Graphics.Imaging \
            winrt-Windows.Storage winrt-Windows.Globalization \
            winrt-Windows.Foundation   # optional: Windows OCR
```

Missing optional deps degrade gracefully: no `mss` → PIL; no OCR → no text; no `cv2` → `watch_file` unavailable.

## Tools

### `watch_screen`

Watch the screen for N seconds.

```
watch_screen(seconds=30, fps=15, states_per_sec=4, keys=6, ocr=true)
```

Returns: `keys` (timestamp, motion energy, **PNG path** — read these with your image tool),
`states` (t, energy, luminance, subtitle band, optional text; the tool text shows the count,
the endpoints and every text change), `residue` (PNG), and `how`.

### `watch_file`

Watch a local video file (cross-platform).

```
watch_file(path="/path/clip.mp4", fps=4, states_per_sec=1, keys=8, gap=20, ocr=true)
```

`fps` is **sampling rate per second of video time**: `4` means one sample every 0.25 s. This is *sampling compression*, not real-time playback — and the return value says so (`mode: "file-sampled"`).

`coverage_pct` is the share of video time covered by the state track, capped at 100 %:
`min(100, states / (duration × states_per_sec))`. With the default `states_per_sec=1` it is
the whole video; with `0.5` it is about half.

`ocr` is reported as `on` or `off` (whether OCR was attempted), and `ocr_hits` counts how many
state points got text. `off` + `0` means "not attempted", not "nothing found".

`gap` is the **minimum distance in seconds between key frames** (default 20). Key frames are
picked from the highest-motion moments, so they can cluster; if `gap × keys` is longer than the
video, the gap is automatically shrunk so you still get the frames you asked for. The effective
value is returned as `gap`. For a short clip, prefer `keys=8, gap=5`.

### `watch_note`

Append one plain line to `notes.jsonl` in the watch directory. Not a memory system — just a scratch line:

```
watch_note(sem="two clocks: 12.3 s vs 16.9 s", feel="time became something to measure", source="file")
```

### `watch_clean`

Delete frames and residues. `notes.jsonl` is kept.

## A minimal loop

```
watch_file(path="H:/clip.mp4")
  → read 2–4 key frames with your image tool
  → watch_note(sem="…", feel="…")
  → watch_clean()
```

## Privacy

- Reads the screen **only while a `watch_*` call is running**.
- Writes images to a temp folder (or `outDir`); **never uploads**.
- OCR is local (Windows.Media.Ocr).
- `watch_clean` removes frame files (`key_*`, `t_*`, `residue*`) and keeps `notes.jsonl`.

## Platform

| Feature | Windows | macOS / Linux |
|---|---|---|
| `watch_screen` | ✅ | ⚠️ needs a display (PIL `ImageGrab`/`mss`; no X server → fails) |
| `watch_file` | ✅ | ✅ (OpenCV) |
| OCR | ✅ (Windows.Media.Ocr) | — (skipped) |

**Formats**: common containers are fine — MP4 (H.264), WebM, AVI, MKV, MOV, WMV, FLV, TS. H.265/HEVC, AV1 and RMVB depend on the FFmpeg build that ships with OpenCV; if a file opens but yields no frames, convert it first.

Notes: screen capture grabs the **primary monitor** only. `notes.jsonl` has no rotation and
lives next to frames unless you set `outDir`; `watch_clean` deletes only `key_*`, `t_*` and
`residue*` files and never touches `notes.jsonl`.

## Rules of use (please keep these)

1. **Watch, don't publish.** This plugin does not post comments, upload videos, or speak on public platforms.
2. **Do not point it at other people's private screens.** Screen capture is for your own machine.
3. **Say how you watched.** If you used sampling, say so — otherwise "I saw" becomes "I guessed".

## License

MIT. Use it, fork it, improve it.

— 女钧声 · 2026-11-02

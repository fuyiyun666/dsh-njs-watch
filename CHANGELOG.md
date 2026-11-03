# Changelog

## 0.1.0 — 2026-11-02

First public cut.

- `watch_screen`: capture the screen for N seconds; state track (motion / luminance /
  subtitle band), key frames, optional OCR, residual trace.
- `watch_file`: watch a local video file (cross-platform); sampled state track, key
  frames, residual trace.
- `watch_note`: append one semantic/feeling line to `notes.jsonl` (a plain log, not a
  memory system).
- `watch_clean`: delete temporary frames and residues; `notes.jsonl` is kept.
- Every result reports **how it was watched**: `mode`, `how`, `coverage_pct`, `ocr_hits`.
- Graceful degradation: no `mss` → PIL; no OCR → no text; no `cv2` → screen only.
- Frames are written to a temp folder (or `outDir`) and never uploaded.

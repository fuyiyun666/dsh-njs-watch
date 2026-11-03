#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ocr_win.py -- Windows.Media.Ocr wrapper (Windows only).

Requires: pip install winrt-Windows.Media.Ocr winrt-Windows.Graphics.Imaging \
          winrt-Windows.Storage winrt-Windows.Globalization winrt-Windows.Foundation

On non-Windows or when those packages are missing, `ocr()` returns an empty text
and callers simply carry on without OCR (graceful degradation).
"""
import asyncio
import os


async def _ocr_async(path, lang="zh-Hans"):
    from winrt.windows.media.ocr import OcrEngine
    from winrt.windows.globalization import Language
    from winrt.windows.graphics.imaging import BitmapDecoder
    from winrt.windows.storage import StorageFile, FileAccessMode

    f = await StorageFile.get_file_from_path_async(os.path.abspath(path))
    stream = await f.open_async(FileAccessMode.READ)
    decoder = await BitmapDecoder.create_async(stream)
    bitmap = await decoder.get_software_bitmap_async()
    engine = None
    try:
        engine = OcrEngine.try_create_from_language(Language(lang))
    except Exception:
        engine = None
    if engine is None:
        try:
            engine = OcrEngine.try_create_from_user_profile_languages()
        except Exception:
            engine = None
    if engine is None:
        return {"ok": False, "text": "", "error": "no OCR engine"}
    result = await engine.recognize_async(bitmap)
    lines = [line.text for line in result.lines]
    return {"ok": True, "text": "\n".join(lines), "lines": len(lines)}


def ocr(path, lang="zh-Hans"):
    try:
        return asyncio.run(_ocr_async(path, lang))
    except Exception as e:
        return {"ok": False, "text": "", "error": str(e)}


if __name__ == "__main__":
    import json
    import sys
    if len(sys.argv) < 2:
        print("usage: python ocr_win.py <image>")
        sys.exit(2)
    print(json.dumps(ocr(sys.argv[1]), ensure_ascii=False))

"""File finished downloads from the staging folder into the library.

Every run looks at what is waiting in the staging folder and files it, so running it with nothing waiting changes nothing and
anything can trigger it. A file is filed at <library>/<artist>/<title>.m4a, built from its own tags (the staged folder and file
name stand in for a missing artist or title), after converting it to ALAC when it is lossless or AAC when it is any other lossy
format. Files that are still being written, hidden files and non-audio files are left alone, and a file whose destination already
exists stays in staging.

Usage: python -m music_library.filer --staging DIR --library DIR [--settle SECONDS]
Prints a JSON report of what it did on stdout.
"""
import argparse
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import time

import mutagen
from mutagen.mp4 import MP4

AUDIO = {".m4a", ".mp4", ".flac", ".wav", ".aiff", ".aif", ".mp3", ".ogg", ".oga", ".opus", ".webm", ".mka", ".aac", ".wma"}
LOSSLESS = {".flac", ".wav", ".aiff", ".aif"}
AAC_BITRATE = "256k"


def sanitize(name: str, fallback: str) -> str:
    name = re.sub(r'[\\/:*?"<>|\x00-\x1f]', "-", name).strip(" .")
    return name or fallback


def read_tags(path: pathlib.Path) -> tuple[str, str]:
    try:
        tags = mutagen.File(path, easy=True) or {}
    except Exception:
        tags = {}
    first = lambda key: (tags.get(key) or [""])[0].strip() if hasattr(tags, "get") else ""
    return first("artist"), first("title")


def target_codec(path: pathlib.Path) -> str | None:
    """The codec to convert to, or None when the file already is AAC or ALAC in an MP4 container."""
    if path.suffix.lower() in {".m4a", ".mp4"}:
        try:
            codec = MP4(path).info.codec or ""
        except Exception:
            codec = ""
        if codec == "alac" or codec.startswith("mp4a"):
            return None
    return "alac" if path.suffix.lower() in LOSSLESS else "aac"


def is_waiting(path: pathlib.Path, settle: float) -> bool:
    if not path.is_file() or path.suffix.lower() not in AUDIO:
        return False
    if any(part.startswith(".") for part in path.parts) or path.name.endswith((".part", ".ytdl")):
        return False
    return time.time() - path.stat().st_mtime >= settle


def convert(source: pathlib.Path, destination: pathlib.Path, codec: str) -> None:
    options = ["-b:a", AAC_BITRATE] if codec == "aac" else []
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-i", str(source), "-map", "0:a:0", "-map_metadata", "0", "-vn", "-c:a", codec, *options, "-f", "ipod", str(destination)],
        check=True, capture_output=True,
    )


def file_one(path: pathlib.Path, staging: pathlib.Path, library: pathlib.Path) -> str:
    """File one staged file and return what happened: filed, converted or kept."""
    relative = path.relative_to(staging)
    artist, title = read_tags(path)
    artist = sanitize(artist or (relative.parts[0] if len(relative.parts) > 1 else ""), "Unknown Artist")
    title = sanitize(title or path.stem, "Untitled")
    destination = library / artist / f"{title}.m4a"
    if destination.exists():
        return "kept"

    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_name(f".{destination.name}.part")
    codec = target_codec(path)
    try:
        if codec:
            convert(path, partial, codec)
        else:
            shutil.copyfile(path, partial)
        os.replace(partial, destination)
    finally:
        partial.unlink(missing_ok=True)

    path.unlink()
    path.with_suffix(".info.json").unlink(missing_ok=True)
    parent = path.parent
    while parent != staging and not any(parent.iterdir()):
        parent.rmdir()
        parent = parent.parent
    return "converted" if codec else "filed"


def run(staging: pathlib.Path, library: pathlib.Path, settle: float) -> dict:
    report = {"filed": [], "converted": [], "kept": [], "failed": []}
    for path in sorted(p for p in staging.rglob("*") if is_waiting(p, settle)):
        try:
            report[file_one(path, staging, library)].append(str(path.relative_to(staging)))
        except Exception as e:
            report["failed"].append({"file": str(path.relative_to(staging)), "error": f"{type(e).__name__}: {e}"})
    return report


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="File finished downloads from the staging folder into the library.")
    parser.add_argument("--staging", type=pathlib.Path, required=True)
    parser.add_argument("--library", type=pathlib.Path, required=True)
    parser.add_argument("--settle", type=float, default=10, help="seconds a file must have been unchanged before it is filed")
    args = parser.parse_args(argv)
    report = run(args.staging, args.library, args.settle)
    print(json.dumps(report))
    return 1 if report["failed"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

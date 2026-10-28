"""One-off batch: generate Indonesian .srt for every video in a given folder, saved alongside it."""

import argparse
import logging
import re
from pathlib import Path

from pipeline import process_video

VIDEO_EXTENSIONS = {".mp4", ".mkv", ".mov", ".avi", ".webm", ".m4v", ".ts"}


def _sort_key(path: Path):
    match = re.match(r"\s*(\d+)", path.stem)
    number = int(match.group(1)) if match else float("inf")
    return (number, path.stem.lower())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("folder")
    args = parser.parse_args()
    folder = Path(args.folder)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(folder / "subtitle_batch.log"),
            logging.StreamHandler(),
        ],
    )
    log = logging.getLogger("batch")

    videos = sorted(
        (p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in VIDEO_EXTENSIONS),
        key=_sort_key,
    )
    log.info("Found %d videos to process in %s", len(videos), folder)

    for i, video in enumerate(videos, start=1):
        srt = video.with_suffix(".srt")
        if srt.exists():
            log.info("[%d/%d] Skip (srt already exists): %s", i, len(videos), video.name)
            continue
        log.info("[%d/%d] Processing: %s", i, len(videos), video.name)
        try:
            process_video(video, srt)
            log.info("[%d/%d] Done: %s -> %s", i, len(videos), video.name, srt.name)
        except Exception:
            log.exception("[%d/%d] FAILED: %s", i, len(videos), video.name)

    log.info("Batch complete: %d videos processed from %s", len(videos), folder)


if __name__ == "__main__":
    main()

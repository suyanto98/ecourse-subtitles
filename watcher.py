"""Watches ~/Videos for new video files and generates English .srt subtitles automatically."""

import json
import logging
import time
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from pipeline import process_video

WATCH_DIR = Path.home() / "Videos"
STATE_FILE = Path(__file__).parent / "state.json"
LOG_FILE = Path(__file__).parent / "subtitle-watcher.log"
VIDEO_EXTENSIONS = {".mp4", ".mkv", ".mov", ".avi", ".webm", ".m4v"}
STABLE_CHECK_INTERVAL = 5  # seconds between size checks to detect "still copying"
POLL_INTERVAL = 3  # seconds between scans of the watch directory

LOG = logging.getLogger("subtitle_watcher")


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()],
    )


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {}


def save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, indent=2))


def file_key(path: Path) -> str:
    return path.name


def is_already_processed(path: Path, state: dict) -> bool:
    entry = state.get(file_key(path))
    if not entry:
        return False
    stat = path.stat()
    return entry.get("size") == stat.st_size and entry.get("mtime") == stat.st_mtime


def wait_until_stable(path: Path) -> bool:
    """Returns True once file size stops changing (copy/download finished)."""
    try:
        last_size = path.stat().st_size
    except FileNotFoundError:
        return False
    while True:
        time.sleep(STABLE_CHECK_INTERVAL)
        if not path.exists():
            return False
        size = path.stat().st_size
        if size == last_size:
            return True
        last_size = size


def process_new_video(path: Path, state: dict) -> None:
    srt_path = path.with_suffix(".srt")
    if srt_path.exists() and is_already_processed(path, state):
        return
    LOG.info("New video detected: %s", path.name)
    if not wait_until_stable(path):
        LOG.warning("%s disappeared before becoming stable, skipping", path.name)
        return
    try:
        process_video(path, srt_path)
        stat = path.stat()
        state[file_key(path)] = {"size": stat.st_size, "mtime": stat.st_mtime, "status": "done"}
        save_state(state)
        LOG.info("Done: %s -> %s", path.name, srt_path.name)
    except Exception:
        LOG.exception("Failed to process %s", path.name)


class VideoHandler(FileSystemEventHandler):
    def __init__(self, state: dict):
        self.state = state

    def on_created(self, event):
        if event.is_directory:
            return
        path = Path(event.src_path)
        if path.suffix.lower() in VIDEO_EXTENSIONS:
            process_new_video(path, self.state)

    def on_moved(self, event):
        if event.is_directory:
            return
        path = Path(event.dest_path)
        if path.suffix.lower() in VIDEO_EXTENSIONS:
            process_new_video(path, self.state)


def scan_existing(state: dict) -> None:
    for path in sorted(WATCH_DIR.iterdir()):
        if path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS:
            process_new_video(path, state)


def main():
    setup_logging()
    WATCH_DIR.mkdir(parents=True, exist_ok=True)
    state = load_state()

    LOG.info("Scanning existing videos in %s", WATCH_DIR)
    scan_existing(state)

    LOG.info("Watching %s for new videos...", WATCH_DIR)
    handler = VideoHandler(state)
    observer = Observer()
    observer.schedule(handler, str(WATCH_DIR), recursive=False)
    observer.start()
    try:
        while True:
            time.sleep(POLL_INTERVAL)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


if __name__ == "__main__":
    main()

"""Pipeline: video -> audio -> English transcript (faster-whisper) -> .srt"""

import logging
import subprocess
import tempfile
from pathlib import Path

from faster_whisper import WhisperModel

LOG = logging.getLogger("subtitle_pipeline")

WHISPER_MODEL_SIZE = "medium"

_whisper_model = None


def get_whisper_model():
    global _whisper_model
    if _whisper_model is None:
        LOG.info("Loading faster-whisper model '%s' (cpu, int8)...", WHISPER_MODEL_SIZE)
        _whisper_model = WhisperModel(WHISPER_MODEL_SIZE, device="cpu", compute_type="int8")
    return _whisper_model


def extract_audio(video_path: Path) -> Path:
    wav_path = Path(tempfile.mkstemp(suffix=".wav")[1])
    cmd = [
        "ffmpeg", "-y", "-i", str(video_path),
        "-vn", "-ac", "1", "-ar", "16000", "-f", "wav", str(wav_path),
    ]
    LOG.info("Extracting audio from %s", video_path.name)
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed for {video_path}: {result.stderr[-2000:]}")
    return wav_path


def transcribe(wav_path: Path) -> list[dict]:
    model = get_whisper_model()
    LOG.info("Transcribing %s", wav_path)
    segments, info = model.transcribe(str(wav_path), language="en", vad_filter=True)
    result = []
    for seg in segments:
        text = seg.text.strip()
        if not text:
            continue
        result.append({"start": seg.start, "end": seg.end, "text": text})
    LOG.info("Transcribed %d segments (detected language=%s)", len(result), info.language)
    return result


def _format_timestamp(seconds: float) -> str:
    ms = round(seconds * 1000)
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def write_srt(segments: list[dict], output_path: Path) -> None:
    lines = []
    for i, seg in enumerate(segments, start=1):
        lines.append(str(i))
        lines.append(f"{_format_timestamp(seg['start'])} --> {_format_timestamp(seg['end'])}")
        lines.append(seg["text"])
        lines.append("")
    output_path.write_text("\n".join(lines), encoding="utf-8")
    LOG.info("Wrote %s (%d cues)", output_path, len(segments))


def process_video(video_path: Path, output_path: Path) -> None:
    wav_path = extract_audio(video_path)
    try:
        segments = transcribe(wav_path)
        if not segments:
            LOG.warning("No speech detected in %s, skipping srt generation", video_path.name)
            return
        write_srt(segments, output_path)
    finally:
        wav_path.unlink(missing_ok=True)


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if len(sys.argv) != 2:
        print("usage: python pipeline.py <video_path>")
        raise SystemExit(1)
    video = Path(sys.argv[1]).resolve()
    out = video.with_suffix(".srt")
    process_video(video, out)

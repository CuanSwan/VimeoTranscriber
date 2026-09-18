import math
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

MAX_CHUNK_BYTES = 24 * 1024 * 1024  # stay under Whisper API's 25MB request limit


def _resolve_binary(name: str, ffmpeg_location: Optional[str]) -> str:
    """Find ffmpeg/ffprobe next to a bundled ffmpeg, falling back to PATH."""
    if not ffmpeg_location:
        return name

    candidate = Path(ffmpeg_location)
    directory = candidate.parent if candidate.is_file() else candidate
    exe_name = f"{name}.exe" if os.name == "nt" else name
    exe_path = directory / exe_name
    return str(exe_path) if exe_path.exists() else name


def download_audio(
    url: str,
    dest_dir: Path,
    video_password: Optional[str] = None,
    ffmpeg_location: Optional[str] = None,
) -> Path:
    """Download the best available audio track for a Vimeo URL via yt-dlp."""
    import yt_dlp

    out_template = str(dest_dir / "%(id)s.%(ext)s")
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": out_template,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "128",
            }
        ],
        "quiet": True,
        "noprogress": True,
    }
    if video_password:
        ydl_opts["videopassword"] = video_password
    if ffmpeg_location:
        ydl_opts["ffmpeg_location"] = ffmpeg_location

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        video_id = info["id"]

    audio_path = dest_dir / f"{video_id}.mp3"
    if not audio_path.exists():
        raise FileNotFoundError(f"Expected downloaded audio at {audio_path}, not found.")
    return audio_path


def _audio_duration_seconds(path: Path, ffmpeg_location: Optional[str] = None) -> float:
    result = subprocess.run(
        [
            _resolve_binary("ffprobe", ffmpeg_location),
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(result.stdout.strip())


def split_audio(
    path: Path, dest_dir: Path, ffmpeg_location: Optional[str] = None
) -> list[Path]:
    """Split an audio file into chunks small enough for the Whisper API, if needed."""
    size = path.stat().st_size
    if size <= MAX_CHUNK_BYTES:
        return [path]

    duration = _audio_duration_seconds(path, ffmpeg_location)
    num_chunks = math.ceil(size / MAX_CHUNK_BYTES)
    chunk_seconds = math.ceil(duration / num_chunks)

    chunk_paths = []
    for i in range(num_chunks):
        chunk_path = dest_dir / f"{path.stem}_part{i:03d}.mp3"
        subprocess.run(
            [
                _resolve_binary("ffmpeg", ffmpeg_location),
                "-y",
                "-loglevel",
                "error",
                "-i",
                str(path),
                "-ss",
                str(i * chunk_seconds),
                "-t",
                str(chunk_seconds),
                "-c",
                "copy",
                str(chunk_path),
            ],
            check=True,
        )
        chunk_paths.append(chunk_path)
    return chunk_paths


def transcribe_audio(
    audio_path: Path,
    api_key: str,
    language: Optional[str] = None,
    ffmpeg_location: Optional[str] = None,
) -> str:
    """Transcribe an audio file with the OpenAI Whisper API, chunking if it's too large."""
    from openai import OpenAI

    client = OpenAI(api_key=api_key)

    with tempfile.TemporaryDirectory() as tmp:
        chunks = split_audio(audio_path, Path(tmp), ffmpeg_location)
        transcripts = []
        for chunk in chunks:
            with open(chunk, "rb") as f:
                kwargs = {"model": "whisper-1", "file": f, "response_format": "text"}
                if language:
                    kwargs["language"] = language
                text = client.audio.transcriptions.create(**kwargs)
            transcripts.append(str(text).strip())

    return " ".join(transcripts)

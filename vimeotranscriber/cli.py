import argparse
import os
import sys
import tempfile
from pathlib import Path

from .transcribe import download_audio, transcribe_audio
from .utils import parse_vimeo_url
from .vimeo_api import VimeoAPIError, VimeoCaptionsClient


def is_frozen() -> bool:
    """True when running as a PyInstaller-built executable."""
    return bool(getattr(sys, "frozen", False))


def get_base_dir() -> Path:
    """Directory the .env file and a bundled ffmpeg are expected next to."""
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            os.environ.setdefault(key, value)


def get_ffmpeg_location(base_dir: Path) -> str | None:
    """Look for an ffmpeg binary bundled next to the executable/script."""
    for name in ("ffmpeg.exe", "ffmpeg"):
        if (base_dir / name).exists():
            return str(base_dir)
    return None


def process_url(
    url: str,
    output_dir: Path,
    vimeo_token: str | None,
    openai_key: str | None,
    language: str | None,
    video_password: str | None,
    ffmpeg_location: str | None = None,
) -> Path:
    ref = parse_vimeo_url(url)
    transcript = None
    source = None

    if vimeo_token:
        try:
            client = VimeoCaptionsClient(vimeo_token)
            transcript = client.fetch_transcript(ref, preferred_language=language)
            if transcript:
                source = "vimeo-captions"
        except VimeoAPIError as exc:
            print(f"[{ref.video_id}] Vimeo captions unavailable ({exc}); "
                  f"falling back to speech-to-text.", file=sys.stderr)

    if not transcript:
        if not openai_key:
            raise RuntimeError(
                f"[{ref.video_id}] No captions found and no OPENAI_API_KEY provided "
                f"for speech-to-text fallback."
            )
        print(f"[{ref.video_id}] No captions available; downloading audio for "
              f"speech-to-text transcription...", file=sys.stderr)
        with tempfile.TemporaryDirectory() as tmp:
            audio_path = download_audio(
                url, Path(tmp), video_password=video_password, ffmpeg_location=ffmpeg_location
            )
            transcript = transcribe_audio(
                audio_path, openai_key, language=language, ffmpeg_location=ffmpeg_location
            )
        source = "whisper"

    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"{ref.video_id}_transcript.txt"
    out_path.write_text(transcript, encoding="utf-8")
    print(f"[{ref.video_id}] Transcript saved to {out_path} (source: {source})")
    return out_path


def read_urls_from_file(path: Path) -> list[str]:
    if not path.exists():
        raise FileNotFoundError(
            f"Input file {path} not found. Create it with one Vimeo URL or ID per line."
        )

    urls = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        urls.append(line)

    if not urls:
        raise ValueError(f"Input file {path} contains no URLs.")

    return urls


def pause() -> None:
    try:
        input("\nPress Enter to exit...")
    except EOFError:
        pass


def prompt(message: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{message}{suffix}: ").strip()
    return value or default


def prompt_for_urls() -> list[str]:
    print("Enter Vimeo links, one per line. Leave a blank line when you're done.")
    urls = []
    while True:
        line = input("> ").strip()
        if not line:
            break
        urls.append(line)
    return urls


def run_batch(
    urls: list[str],
    output_dir: Path,
    vimeo_token: str | None,
    openai_key: str | None,
    language: str | None,
    video_password: str | None,
    ffmpeg_location: str | None,
) -> int:
    exit_code = 0
    for url in urls:
        try:
            process_url(
                url,
                output_dir,
                vimeo_token,
                openai_key,
                language,
                video_password,
                ffmpeg_location=ffmpeg_location,
            )
        except Exception as exc:
            print(f"Error processing {url}: {exc}", file=sys.stderr)
            exit_code = 1
    return exit_code


def interactive_main(ffmpeg_location: str | None) -> int:
    print("=== Vimeo Transcriber ===")
    print("Fetches official captions when available, and transcribes with")
    print("speech-to-text otherwise.\n")

    choice = prompt("Load links from a (f)ile, or (t)ype/paste them now?", "t")
    if choice.lower().startswith("f"):
        file_path = prompt("Path to your links file", "links.txt")
        try:
            urls = read_urls_from_file(Path(file_path))
        except (FileNotFoundError, ValueError) as exc:
            print(f"Error: {exc}")
            pause()
            return 1
    else:
        urls = prompt_for_urls()
        if not urls:
            print("No links entered, nothing to do.")
            pause()
            return 1

    vimeo_token = os.environ.get("VIMEO_ACCESS_TOKEN") or prompt(
        "Vimeo API access token (Enter to skip, will use speech-to-text instead)"
    ) or None
    openai_key = os.environ.get("OPENAI_API_KEY") or prompt(
        "OpenAI API key (Enter to skip if every video already has captions)"
    ) or None
    output_dir = Path(prompt("Folder to save transcripts in", "transcripts"))

    print()
    exit_code = run_batch(
        urls, output_dir, vimeo_token, openai_key, None, None, ffmpeg_location
    )

    print("\nDone!" if exit_code == 0 else "\nFinished with errors — see above.")
    pause()
    return exit_code


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    base_dir = get_base_dir()
    load_dotenv(base_dir / ".env")
    ffmpeg_location = get_ffmpeg_location(base_dir)

    if not argv:
        return interactive_main(ffmpeg_location)

    parser = argparse.ArgumentParser(
        description="Fetch transcripts for Vimeo videos: uses official captions when "
        "available, falls back to Whisper speech-to-text otherwise."
    )
    parser.add_argument(
        "input_file",
        help="Text file with one Vimeo URL or ID per line (blank lines and lines "
        "starting with # are ignored).",
    )
    parser.add_argument(
        "-o", "--output-dir", default="transcripts", help="Directory to save transcripts to."
    )
    parser.add_argument(
        "--vimeo-token",
        default=os.environ.get("VIMEO_ACCESS_TOKEN"),
        help="Vimeo API access token (or set VIMEO_ACCESS_TOKEN).",
    )
    parser.add_argument(
        "--openai-key",
        default=os.environ.get("OPENAI_API_KEY"),
        help="OpenAI API key for Whisper fallback (or set OPENAI_API_KEY).",
    )
    parser.add_argument(
        "--language", default=None, help="Preferred language code (e.g. 'en')."
    )
    parser.add_argument(
        "--video-password",
        default=None,
        help="Password for password-protected Vimeo videos (used by the fallback path).",
    )
    args = parser.parse_args(argv)

    try:
        urls = read_urls_from_file(Path(args.input_file))
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        if is_frozen():
            pause()
        return 1

    output_dir = Path(args.output_dir)
    exit_code = run_batch(
        urls,
        output_dir,
        args.vimeo_token,
        args.openai_key,
        args.language,
        args.video_password,
        ffmpeg_location,
    )

    if is_frozen():
        pause()

    return exit_code


if __name__ == "__main__":
    sys.exit(main())

import argparse
import os
import sys
import tempfile
from pathlib import Path

from .transcribe import download_audio, transcribe_audio
from .utils import parse_vimeo_url
from .vimeo_api import VimeoAPIError, VimeoCaptionsClient


def process_url(
    url: str,
    output_dir: Path,
    vimeo_token: str | None,
    openai_key: str | None,
    language: str | None,
    video_password: str | None,
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
            audio_path = download_audio(url, Path(tmp), video_password=video_password)
            transcript = transcribe_audio(audio_path, openai_key, language=language)
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Fetch transcripts for Vimeo videos: uses official captions when "
        "available, falls back to Whisper speech-to-text otherwise."
    )
    parser.add_argument(
        "input_file",
        nargs="?",
        default="links.txt",
        help="Text file with one Vimeo URL or ID per line (blank lines and lines "
        "starting with # are ignored). Defaults to 'links.txt'.",
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
        return 1

    output_dir = Path(args.output_dir)
    exit_code = 0
    for url in urls:
        try:
            process_url(
                url,
                output_dir,
                args.vimeo_token,
                args.openai_key,
                args.language,
                args.video_password,
            )
        except Exception as exc:
            print(f"Error processing {url}: {exc}", file=sys.stderr)
            exit_code = 1

    return exit_code


if __name__ == "__main__":
    sys.exit(main())

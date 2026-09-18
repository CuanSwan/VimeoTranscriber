# VimeoTranscriber

Fetch transcripts from Vimeo video links.

For each URL, it:
1. Tries to pull the video's official captions/subtitles via the Vimeo API.
2. If no captions exist (or no Vimeo token is configured), downloads the
   audio with `yt-dlp` and transcribes it with the OpenAI Whisper API.

## Requirements

- Python 3.10+
- [`ffmpeg`](https://ffmpeg.org/) installed and on `PATH` (used by `yt-dlp`
  and for splitting long audio files)
- A Vimeo API access token (optional, enables the fast captions path) —
  create one at https://developer.vimeo.com/apps
- An OpenAI API key (optional, enables the Whisper fallback path)

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env   # then fill in your tokens
export $(cat .env | xargs)
```

## Usage

List the videos you want transcribed in a text file, one URL (or bare video
ID) per line — blank lines and lines starting with `#` are ignored. See
`links.txt.example` for the format.

```bash
cp links.txt.example links.txt   # then edit it with your video links

python -m vimeotranscriber.cli links.txt

# custom output directory and preferred language
python -m vimeotranscriber.cli links.txt -o transcripts --language en
```

If no file is given, it defaults to `links.txt` in the current directory.

Or, after installing the package (`pip install -e .`), use the `vimeo-transcriber`
command directly.

Transcripts are saved as `<output-dir>/<video_id>_transcript.txt`.

### Notes

- Unlisted videos (URLs with a hash, e.g. `vimeo.com/123456789/abcdef1234`)
  are supported for both paths.
- Password-protected videos are only supported on the speech-to-text fallback
  path; pass `--video-password`.
- If neither `VIMEO_ACCESS_TOKEN` nor `OPENAI_API_KEY` is set, the tool can't
  produce a transcript.

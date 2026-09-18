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

### Interactive mode

Run it with no arguments and it will walk you through everything —
whether to load links from a file or paste them in, which API keys to use
(if you haven't set them in `.env`), and where to save the output:

```bash
python -m vimeotranscriber.cli
```

### Command-line mode

List the videos you want transcribed in a text file, one URL (or bare video
ID) per line — blank lines and lines starting with `#` are ignored. See
`links.txt.example` for the format.

```bash
cp links.txt.example links.txt   # then edit it with your video links

python -m vimeotranscriber.cli links.txt

# custom output directory and preferred language
python -m vimeotranscriber.cli links.txt -o transcripts --language en
```

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

## Building a Windows executable (for non-technical users)

PyInstaller can package this into a single `VimeoTranscriber.exe` that
doesn't require Python to be installed. It has to be built **on Windows**
(PyInstaller doesn't cross-compile), but once built it works standalone.

1. On a Windows machine, install Python 3.10+ and clone/download this repo.
2. Download a static `ffmpeg.exe` build (e.g. from
   https://www.gyan.dev/ffmpeg/builds/) — the app looks for `ffmpeg.exe`
   sitting next to it and uses that automatically, so users don't need to
   install ffmpeg separately or touch `PATH`.
3. Run `build_windows.bat` (double-click it, or run it from a command
   prompt). This creates a virtual environment, installs dependencies and
   PyInstaller, and builds `dist\VimeoTranscriber.exe`.
4. Put together a folder for your users containing:
   - `dist\VimeoTranscriber.exe`
   - `ffmpeg.exe` (from step 2, same folder as the exe)
   - Optionally a `.env` file (copy `.env.example`, fill in
     `VIMEO_ACCESS_TOKEN`/`OPENAI_API_KEY`) so users aren't prompted for keys
   - Optionally a `links.txt` if you want double-click-and-go behavior

Non-technical users can then either:
- **Double-click `VimeoTranscriber.exe`** — it opens a console window and
  walks them through everything interactively, or
- **Drag a `links.txt` file onto the exe icon** — it processes that file
  directly using the defaults.

Either way, the window stays open and shows progress/errors, and waits for
a keypress before closing so results aren't missed.

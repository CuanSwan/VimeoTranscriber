import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class VimeoRef:
    video_id: str
    unlisted_hash: Optional[str] = None


_VIMEO_URL_RE = re.compile(
    r"vimeo\.com/(?:channels/[^/]+/|groups/[^/]+/videos/|video/|album/\d+/video/)?"
    r"(\d+)(?:/([0-9a-f]+))?",
    re.IGNORECASE,
)


def parse_vimeo_url(url_or_id: str) -> VimeoRef:
    """Extract a Vimeo video id (and unlisted-video hash, if present) from a link."""
    if url_or_id.isdigit():
        return VimeoRef(video_id=url_or_id)

    match = _VIMEO_URL_RE.search(url_or_id)
    if not match:
        raise ValueError(f"Could not find a Vimeo video id in: {url_or_id!r}")

    return VimeoRef(video_id=match.group(1), unlisted_hash=match.group(2))


def vtt_to_text(vtt_content: str) -> str:
    """Collapse a WebVTT captions file down to plain, deduplicated transcript text."""
    lines = vtt_content.splitlines()
    cue_re = re.compile(r"-->")
    tag_re = re.compile(r"<[^>]+>")

    text_lines = []
    last_line = None
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.upper().startswith("WEBVTT"):
            continue
        if line.isdigit():
            continue
        if cue_re.search(line):
            continue
        if line.upper().startswith(("NOTE", "STYLE", "REGION")):
            continue

        clean = tag_re.sub("", line).strip()
        if clean and clean != last_line:
            text_lines.append(clean)
            last_line = clean

    return " ".join(text_lines)

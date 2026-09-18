from typing import List, Optional

import requests

from .utils import VimeoRef, vtt_to_text

API_BASE = "https://api.vimeo.com"
API_ACCEPT_HEADER = "application/vnd.vimeo.*+json;version=3.4"


class VimeoAPIError(RuntimeError):
    pass


class VimeoCaptionsClient:
    def __init__(self, access_token: str):
        if not access_token:
            raise ValueError("A Vimeo API access token is required.")
        self._session = requests.Session()
        self._session.headers.update(
            {
                "Authorization": f"bearer {access_token}",
                "Accept": API_ACCEPT_HEADER,
            }
        )

    def list_texttracks(self, ref: VimeoRef) -> List[dict]:
        params = {"h": ref.unlisted_hash} if ref.unlisted_hash else None
        resp = self._session.get(
            f"{API_BASE}/videos/{ref.video_id}/texttracks", params=params
        )
        if resp.status_code == 404:
            raise VimeoAPIError(f"Video {ref.video_id} not found or not accessible.")
        if resp.status_code == 403:
            raise VimeoAPIError(
                f"Access token is not authorized to view video {ref.video_id}."
            )
        resp.raise_for_status()
        return resp.json().get("data", [])

    def fetch_transcript(
        self, ref: VimeoRef, preferred_language: Optional[str] = None
    ) -> Optional[str]:
        """Return the plain-text transcript from the best available text track, or None."""
        tracks = self.list_texttracks(ref)
        if not tracks:
            return None

        def score(track: dict) -> tuple:
            lang_match = 1 if preferred_language and track.get("language", "").startswith(
                preferred_language
            ) else 0
            is_active = 1 if track.get("active") else 0
            is_caption = 1 if track.get("type") == "captions" else 0
            return (lang_match, is_active, is_caption)

        best = max(tracks, key=score)
        link = best.get("link")
        if not link:
            return None

        vtt_resp = self._session.get(link)
        vtt_resp.raise_for_status()
        return vtt_to_text(vtt_resp.text)

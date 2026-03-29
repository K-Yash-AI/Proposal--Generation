"""
Fireflies.ai GraphQL API client.

Fetches meeting transcripts for a given client (identified by name or email).
Implements retry logic and pagination.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

import requests
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from config import settings
from utils.logger import log

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class TranscriptSummary:
    overview: str = ""
    action_items: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    shorthand_bullet: list[str] = field(default_factory=list)


@dataclass
class Sentence:
    speaker_name: str
    text: str
    start_time: Optional[float] = None


@dataclass
class Transcript:
    id: str
    title: str
    date: Optional[datetime]
    duration: Optional[int]  # seconds
    participants: list[str]
    host_email: Optional[str]
    summary: TranscriptSummary
    sentences: list[Sentence]

    @property
    def full_text(self) -> str:
        """Returns the full conversation as plain text."""
        lines = []
        for s in self.sentences:
            lines.append(f"{s.speaker_name}: {s.text}")
        return "\n".join(lines)

    @property
    def date_str(self) -> str:
        if self.date:
            return self.date.strftime("%B %d, %Y")
        return "Unknown date"


# ---------------------------------------------------------------------------
# GraphQL queries
# ---------------------------------------------------------------------------

_TRANSCRIPTS_QUERY = """
query GetTranscripts($limit: Int, $skip: Int) {
  transcripts(limit: $limit, skip: $skip) {
    id
    title
    date
    duration
    participants
    host_email
    summary {
      overview
      shorthand_bullet
      action_items
      keywords
    }
    sentences {
      speaker_name
      text
      start_time
    }
  }
}
"""

_TRANSCRIPT_BY_ID_QUERY = """
query GetTranscript($id: String!) {
  transcript(id: $id) {
    id
    title
    date
    duration
    participants
    host_email
    summary {
      overview
      shorthand_bullet
      action_items
      keywords
    }
    sentences {
      speaker_name
      text
      start_time
    }
  }
}
"""


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class FirefliesService:
    """Fireflies.ai API wrapper."""

    def __init__(self) -> None:
        self._api_key = settings.fireflies_api_key
        self._url = settings.fireflies_api_url
        self._session = requests.Session()
        self._session.headers.update(
            {
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            }
        )

    @retry(
        retry=retry_if_exception_type(requests.RequestException),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def _execute(self, query: str, variables: dict[str, Any] | None = None) -> dict:
        """Execute a GraphQL query and return the data dict."""
        payload: dict[str, Any] = {"query": query}
        if variables:
            payload["variables"] = variables

        resp = self._session.post(self._url, json=payload, timeout=30)
        resp.raise_for_status()

        body = resp.json()
        if "errors" in body:
            errors = body["errors"]
            raise ValueError(f"GraphQL errors: {errors}")

        return body.get("data", {})

    # ── Parsing helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _parse_transcript(raw: dict) -> Transcript:
        summary_raw = raw.get("summary") or {}
        summary = TranscriptSummary(
            overview=summary_raw.get("overview") or "",
            action_items=summary_raw.get("action_items") or [],
            keywords=summary_raw.get("keywords") or [],
            shorthand_bullet=summary_raw.get("shorthand_bullet") or [],
        )

        sentences = [
            Sentence(
                speaker_name=s.get("speaker_name") or "Unknown",
                text=s.get("text") or "",
                start_time=s.get("start_time"),
            )
            for s in (raw.get("sentences") or [])
            if s.get("text")
        ]

        date_val = raw.get("date")
        parsed_date: Optional[datetime] = None
        if date_val:
            try:
                # Fireflies returns epoch ms or ISO string
                if isinstance(date_val, (int, float)):
                    parsed_date = datetime.fromtimestamp(date_val / 1000)
                else:
                    from dateutil.parser import parse as dateparse
                    parsed_date = dateparse(str(date_val))
            except Exception:
                pass

        return Transcript(
            id=raw.get("id", ""),
            title=raw.get("title") or "Untitled Meeting",
            date=parsed_date,
            duration=raw.get("duration"),
            participants=raw.get("participants") or [],
            host_email=raw.get("host_email"),
            summary=summary,
            sentences=sentences,
        )

    # ── Public API ───────────────────────────────────────────────────────────

    def get_transcripts_for_client(
        self,
        client_name: Optional[str] = None,
        client_email: Optional[str] = None,
        limit: int = 5,
    ) -> list[Transcript]:
        """
        Return the most recent `limit` transcripts that involve the given client.
        Identification is done by matching participant name (case-insensitive) or email.
        """
        if not client_name and not client_email:
            raise ValueError("Provide at least one of: client_name, client_email")

        log.info(
            f"[step]Fetching Fireflies transcripts for client:[/step] "
            f"name={client_name!r}, email={client_email!r}"
        )

        matched: list[Transcript] = []
        skip = 0
        batch_size = 20  # Fetch in larger batches to find matching ones
        max_pages = 10   # Search at most 200 transcripts (10 × 20)

        for _page in range(max_pages):
            if len(matched) >= limit:
                break

            data = self._execute(
                _TRANSCRIPTS_QUERY,
                {"limit": batch_size, "skip": skip},
            )
            raw_list = data.get("transcripts") or []
            if not raw_list:
                break  # No more transcripts

            for raw in raw_list:
                t = self._parse_transcript(raw)
                if self._matches_client(t, client_name, client_email):
                    matched.append(t)
                    if len(matched) >= limit:
                        break

            if len(raw_list) < batch_size:
                break  # Fetched everything available

            skip += batch_size

        if not matched:
            log.warning(
                f"No transcripts found for client name={client_name!r}, "
                f"email={client_email!r}. Check spelling or Fireflies permissions."
            )
        else:
            log.info(f"[success]Found {len(matched)} transcript(s)[/success]")

        return matched[:limit]

    @staticmethod
    def _matches_client(
        t: Transcript,
        name: Optional[str],
        email: Optional[str],
    ) -> bool:
        participants_lower = [p.lower() for p in t.participants]

        if email and email.lower() in participants_lower:
            return True
        if name:
            name_lower = name.lower()
            # Substring match on any participant string
            for p in participants_lower:
                if name_lower in p:
                    return True
            # Also check title in case it contains the client name
            if name_lower in t.title.lower():
                return True
        return False

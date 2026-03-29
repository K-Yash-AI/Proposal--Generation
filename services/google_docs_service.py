"""
Google Docs / Drive API client.

Downloads a Google Doc as a .docx file (OOXML export) so it can be used as
the proposal template.  Supports both Service Account and OAuth2 auth.
"""
from __future__ import annotations

import io
import os
import pickle
from pathlib import Path
from typing import Optional

from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential
from utils.logger import log

_SCOPES = [
    "https://www.googleapis.com/auth/drive",  # Full Drive access for upload/share
    "https://www.googleapis.com/auth/documents.readonly",
]

_DOCX_MIME = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)


class GoogleDocsService:
    """Thin wrapper around Google Drive export for Docs → DOCX."""

    def __init__(self) -> None:
        self._creds = None
        self._drive_service = None
        self._docs_service = None

    # ── Auth ─────────────────────────────────────────────────────────────────

    def _authenticate(self) -> None:
        """Build credentials from Service Account or OAuth2 flow."""
        from config import settings

        try:
            from google.oauth2 import service_account
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from google.auth.transport.requests import Request
            from googleapiclient.discovery import build
        except ImportError as exc:
            raise RuntimeError(
                "Google client libraries not installed. "
                "Run: pip install google-api-python-client google-auth-oauthlib"
            ) from exc

        if settings.google_service_account_file:
            sa_file = settings.google_service_account_file
            if not Path(sa_file).exists():
                raise FileNotFoundError(
                    f"Service account file not found: {sa_file}"
                )
            log.info("[step]Authenticating with Google Service Account[/step]")
            self._creds = service_account.Credentials.from_service_account_file(
                sa_file, scopes=_SCOPES
            )

        elif settings.google_credentials_file:
            token_path = settings.google_token_file
            creds: Optional[Credentials] = None

            if Path(token_path).exists():
                with open(token_path, "rb") as f:
                    creds = pickle.load(f)

            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        settings.google_credentials_file, _SCOPES
                    )
                    creds = flow.run_local_server(port=0)
                with open(token_path, "wb") as f:
                    pickle.dump(creds, f)

            log.info("[step]Authenticated with Google OAuth2[/step]")
            self._creds = creds

        else:
            raise RuntimeError(
                "No Google credentials configured. Set GOOGLE_SERVICE_ACCOUNT_FILE "
                "or GOOGLE_CREDENTIALS_FILE in your .env"
            )

        self._drive_service = build("drive", "v3", credentials=self._creds)
        self._docs_service = build("docs", "v1", credentials=self._creds)

    def _ensure_authenticated(self) -> None:
        if self._creds is None:
            self._authenticate()

    # ── Public API ───────────────────────────────────────────────────────────

    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def download_template_as_docx(self, doc_id: str) -> bytes:
        """
        Export a Google Doc as DOCX bytes.

        Args:
            doc_id: The Google Docs document ID (from the URL).

        Returns:
            Raw bytes of the exported .docx file.
        """
        self._ensure_authenticated()
        log.info(f"[step]Downloading Google Doc template: {doc_id}[/step]")

        from googleapiclient.errors import HttpError

        try:
            request = self._drive_service.files().export_media(
                fileId=doc_id, mimeType=_DOCX_MIME
            )
            buf = io.BytesIO()
            from googleapiclient.http import MediaIoBaseDownload

            downloader = MediaIoBaseDownload(buf, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()

            content = buf.getvalue()
            log.info(
                f"[success]Downloaded template ({len(content):,} bytes)[/success]"
            )
            return content

        except HttpError as exc:
            if exc.resp.status == 404:
                raise FileNotFoundError(
                    f"Google Doc not found: {doc_id}. "
                    "Check the doc ID and sharing permissions."
                ) from exc
            raise

    def get_doc_title(self, doc_id: str) -> str:
        """Return the title of a Google Doc."""
        self._ensure_authenticated()
        doc = self._docs_service.documents().get(documentId=doc_id).execute()
        return doc.get("title", "Proposal Template")

    # ── Upload & Share ──────────────────────────────────────────────────────

    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def upload_docx_to_drive(
        self, 
        file_path: str, 
        folder_id: Optional[str] = None,
        make_public: bool = True
    ) -> tuple[str, str]:
        """
        Upload a DOCX file to Google Drive and optionally make it shareable.

        Args:
            file_path: Path to the .docx file to upload
            folder_id: Optional Google Drive folder ID to upload to
            make_public: Whether to make the document publicly viewable

        Returns:
            Tuple of (document_id, shareable_link)
        """
        from googleapiclient.http import MediaFileUpload
        from googleapiclient.errors import HttpError

        self._ensure_authenticated()

        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        file_name = file_path_obj.stem
        log.info(f"[step]Uploading to Google Drive: {file_name}[/step]")

        try:
            media = MediaFileUpload(file_path, mimetype=_DOCX_MIME)
            
            file_metadata = {
                "name": f"{file_name}.docx",
                "mimeType": _DOCX_MIME,
            }
            
            if folder_id:
                file_metadata["parents"] = [folder_id]

            file = self._drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields="id, webViewLink"
            ).execute()

            doc_id = file.get("id")
            view_link = file.get("webViewLink")
            
            log.info(f"[success]File uploaded: {doc_id}[/success]")

            # Make shareable if requested
            if make_public:
                self._make_file_shareable(doc_id)
                log.info(f"[success]Document link: {view_link}[/success]")

            return doc_id, view_link

        except HttpError as exc:
            log.error(f"Failed to upload file: {exc}")
            raise

    def _make_file_shareable(self, file_id: str) -> None:
        """Make a file publicly viewable on Google Drive."""
        try:
            self._drive_service.permissions().create(
                fileId=file_id,
                body={"kind": "drive#permission", "role": "reader", "type": "anyone"},
                fields="id"
            ).execute()
            log.info("[step]File made publicly shareable[/step]")
        except Exception as exc:
            log.warning(f"Could not make file public: {exc}")

    def get_file_share_link(self, file_id: str) -> str:
        """Get the sharable link for a file."""
        try:
            self._ensure_authenticated()
            file = self._drive_service.files().get(
                fileId=file_id,
                fields="webViewLink"
            ).execute()
            return file.get("webViewLink", "")
        except Exception as exc:
            log.error(f"Could not get share link: {exc}")
            return ""


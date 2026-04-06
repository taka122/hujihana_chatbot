import io
import logging
import re
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import parse_qs, urlparse

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

logger = logging.getLogger(__name__)

_RAW_DRIVE_ID = re.compile(r"^[A-Za-z0-9_-]{10,}$")
_VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".m4v", ".webm"}


def extract_drive_folder_id(value: str) -> str:
    """Accept either a raw folder ID or a full Google Drive folder URL."""
    candidate = (value or "").strip()
    if not candidate:
        raise ValueError("Google DriveフォルダのURLまたはIDを入力してください。")

    if _RAW_DRIVE_ID.fullmatch(candidate) and "://" not in candidate and "/" not in candidate and "?" not in candidate:
        return candidate

    parsed = urlparse(candidate)
    if "drive.google.com" not in parsed.netloc:
        raise ValueError("Google DriveフォルダのURLを入力してください。")

    path_parts = [part for part in parsed.path.split("/") if part]
    if "file" in path_parts:
        raise ValueError("ファイルURLではなく、Google DriveフォルダのURLを入力してください。")

    if "folders" in path_parts:
        folder_index = path_parts.index("folders")
        if folder_index + 1 < len(path_parts):
            return path_parts[folder_index + 1]

    query_id = parse_qs(parsed.query).get("id", [""])[0].strip()
    if _RAW_DRIVE_ID.fullmatch(query_id):
        return query_id

    raise ValueError("Google DriveフォルダIDをURLから取得できませんでした。")


def filter_video_files(files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    supported: List[Dict[str, Any]] = []
    for item in files:
        mime_type = str(item.get("mimeType") or "").lower()
        name = str(item.get("name") or "")
        ext = Path(name).suffix.lower()
        if mime_type.startswith("video/") or ext in _VIDEO_EXTENSIONS:
            supported.append(item)
    return supported


class DriveService:
    def __init__(self, service_account_info: Dict[str, Any]):
        """
        Google Service Account の情報（JSONの内容）を受け取って初期化します。
        """
        self.creds = service_account.Credentials.from_service_account_info(
            service_account_info,
            scopes=["https://www.googleapis.com/auth/drive.readonly"],
        )
        self.service = build("drive", "v3", credentials=self.creds, cache_discovery=False)

    def list_files_in_folder(self, folder_id: str) -> List[Dict[str, Any]]:
        """指定したフォルダ内のファイル一覧を取得します。"""
        files: List[Dict[str, Any]] = []
        next_page_token: str | None = None

        while True:
            results = self.service.files().list(
                q=f"'{folder_id}' in parents and trashed = false",
                fields="nextPageToken, files(id, name, mimeType, size, modifiedTime, webViewLink)",
                pageToken=next_page_token,
                includeItemsFromAllDrives=True,
                supportsAllDrives=True,
            ).execute()
            files.extend(results.get("files", []))
            next_page_token = results.get("nextPageToken")
            if not next_page_token:
                break

        return files

    def get_file_metadata(self, file_id: str) -> Dict[str, Any]:
        """ファイルのメタデータを取得します。"""
        return self.service.files().get(
            fileId=file_id,
            fields="id, name, mimeType, webViewLink, size",
            supportsAllDrives=True,
        ).execute()

    def download_file_to_memory(self, file_id: str) -> bytes:
        """ファイルをメモリ上にダウンロードします。"""
        request = self.service.files().get_media(fileId=file_id, supportsAllDrives=True)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
            if status:
                logger.info("Download percentage: %d%%", int(status.progress() * 100))

        return fh.getvalue()

    def get_stream_url(self, file_id: str) -> str:
        """Google Drive上の閲覧URLを返します。"""
        file_meta = self.get_file_metadata(file_id)
        return file_meta.get("webViewLink", "")

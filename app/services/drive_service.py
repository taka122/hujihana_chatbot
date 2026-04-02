import logging
import io
from typing import List, Dict, Any, Optional
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

logger = logging.getLogger(__name__)

class DriveService:
    def __init__(self, service_account_info: Dict[str, Any]):
        """
        Google Service Account の情報（JSONの内容）を受け取って初期化します。
        """
        self.creds = service_account.Credentials.from_service_account_info(
            service_account_info,
            scopes=['https://www.googleapis.com/auth/drive.readonly']
        )
        self.service = build('drive', 'v3', credentials=self.creds)

    def list_files_in_folder(self, folder_id: str) -> List[Dict[str, Any]]:
        """
        指定したフォルダ内のファイル一覧を取得します。
        """
        results = self.service.files().list(
            q=f"'{folder_id}' in parents and trashed = false",
            fields="nextPageToken, files(id, name, mimeType, size, modifiedTime)"
        ).execute()
        return results.get('files', [])

    def get_file_metadata(self, file_id: str) -> Dict[str, Any]:
        """
        ファイルのメタデータを取得します。
        """
        return self.service.files().get(
            fileId=file_id,
            fields="id, name, mimeType, webViewLink, size"
        ).execute()

    def download_file_to_memory(self, file_id: str) -> bytes:
        """
        ファイルをメモリ上にダウンロードします。
        """
        request = self.service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
            if status:
                logger.info("Download percentage: %d%%", int(status.progress() * 100))
        
        return fh.getvalue()

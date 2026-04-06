import json
import logging
import os
from app.services.drive_service import DriveService
from app.config import get_settings

logging.basicConfig(level=logging.INFO)

def test_download(file_id: str, f):
    settings = get_settings()
    sa_path = settings.google_drive_service_account_path
    if not sa_path or not os.path.exists(sa_path):
        f.write("Service account path not found!\n")
        return
        
    with open(sa_path, "r") as sa_f:
        sa_info = json.load(sa_f)
        
    drive = DriveService(sa_info)
    
    f.write(f"Testing download for file_id: {file_id}\n")
    try:
        meta = drive.get_file_metadata(file_id)
        f.write(f"File Metadata: {meta}\n")
        
        f.write("Downloading...\n")
        data = drive.download_file_to_memory(file_id)
        f.write(f"Success! Downloaded {len(data)} bytes.\n")
    except Exception as e:
        f.write(f"Fail to download: {e}\n")

if __name__ == "__main__":
    with open("/app/test_log.txt", "w", encoding="utf-8") as f:
        # Test with the ID found in tmp_import_single.py first
        test_id = "1JDSGLGb-03B6KmqtNnVpGLHaZeEt"
        test_download(test_id, f)
        f.write("\n------------------\n")
        # Also test the one that caused the error
        error_id = "1YhlD8uQ8ifUciVQdH10bbl_ljZocR1lHUO"
        test_download(error_id, f)

import json
from app.services.drive_service import DriveService
from app.config import get_settings

def list_files():
    settings = get_settings()
    with open(settings.google_drive_service_account_path, "r") as f:
        sa_info = json.load(f)
    drive = DriveService(sa_info)
    files = drive.list_files_in_folder('1zcxbAmnodfu1gMtLOHATFuYM8Ak-hi0H')
    # Filter and sort
    video_files = [f for f in files if f.get('mimeType', '').startswith('video/')]
    for f in video_files:
        f['size_int'] = int(f.get('size', 0))
    
    video_files.sort(key=lambda x: x['size_int'])
    
    print("--- Smallest 3 Videos ---")
    for f in video_files[:3]:
        print(f"NAME: {f['name']} (SIZE: {f['size_int'] / 1024 / 1024:.2f} MB, ID: {f['id']})")

if __name__ == "__main__":
    list_files()

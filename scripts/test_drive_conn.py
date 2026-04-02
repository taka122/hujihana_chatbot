import os
import json
import logging
import sys

# プロジェクトのルートをPathに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.drive_service import DriveService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_connection():
    service_account_path = "service-account.json"
    
    if not os.path.exists(service_account_path):
        logger.error(f"Error: {service_account_path} が見つかりません。")
        logger.info("ダウンロードしたJSONファイルをこのディレクトリに配置してください。")
        return

    try:
        with open(service_account_path, "r") as f:
            creds_info = json.load(f)
        
        drive = DriveService(creds_info)
        logger.info("Successfully initialized DriveService.")
        
        # フォルダIDを取得（引数があればそれを使う）
        folder_id = sys.argv[1] if len(sys.argv) > 1 else input("テストしたい Google Drive フォルダの ID を入力してください: ").strip()
        if not folder_id:
            logger.warning("フォルダIDが指定されませんでした。接続確認のみ完了します。")
            return

        files = drive.list_files_in_folder(folder_id)
        logger.info(f"アクセス成功！ {len(files)} 個のファイルが見つかりました:")
        for f in files:
            logger.info(f" - {f['name']} (ID: {f['id']}, Type: {f['mimeType']})")

    except Exception as e:
        logger.exception("Google Drive への接続中にエラーが発生しました。")
        logger.error("以下の点を確認してください：")
        logger.error("1. Google Cloud で Google Drive API が有効になっているか")
        logger.error("2. サービスアカウントのメールアドレスにフォルダの共有（閲覧）権限を与えているか")

if __name__ == "__main__":
    test_connection()

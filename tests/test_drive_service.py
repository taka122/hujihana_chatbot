import unittest

from app.services.drive_service import extract_drive_folder_id, filter_video_files


class DriveServiceHelpersTest(unittest.TestCase):
    def test_extract_folder_id_from_drive_folder_url(self) -> None:
        url = "https://drive.google.com/drive/folders/1AbCdEfGhIjKlMnOp?usp=sharing"
        self.assertEqual(extract_drive_folder_id(url), "1AbCdEfGhIjKlMnOp")

    def test_extract_folder_id_from_open_id_url(self) -> None:
        url = "https://drive.google.com/open?id=1ZYXwVuTsRqPoNmLk"
        self.assertEqual(extract_drive_folder_id(url), "1ZYXwVuTsRqPoNmLk")

    def test_extract_folder_id_accepts_raw_id(self) -> None:
        self.assertEqual(extract_drive_folder_id("1RawFolderIdExample"), "1RawFolderIdExample")

    def test_extract_folder_id_rejects_file_url(self) -> None:
        with self.assertRaises(ValueError):
            extract_drive_folder_id("https://drive.google.com/file/d/1AbCdEfGhIjKlMnOp/view")

    def test_filter_video_files_keeps_only_video_items(self) -> None:
        files = [
            {"id": "video-1", "name": "movie.mov", "mimeType": "video/quicktime"},
            {"id": "doc-1", "name": "manual.pdf", "mimeType": "application/pdf"},
            {"id": "video-2", "name": "clip.mp4", "mimeType": "application/octet-stream"},
        ]

        result = filter_video_files(files)

        self.assertEqual([item["id"] for item in result], ["video-1", "video-2"])


if __name__ == "__main__":
    unittest.main()

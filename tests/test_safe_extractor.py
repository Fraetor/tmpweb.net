import io
import tarfile
import tempfile
import unittest
import zipfile
from pathlib import Path

from src.safe_extractor import safe_extract


class SafeExtractTests(unittest.TestCase):
    def test_extracts_zip_archive(self):
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, "w") as zip_file:
            zip_file.writestr("site/index.html", "<h1>Hello</h1>")
        archive.seek(0)

        with tempfile.TemporaryDirectory() as directory:
            extract_path = Path(directory)
            safe_extract(archive, extract_path, archive_type="zip")

            self.assertEqual(
                (extract_path / "site/index.html").read_text(), "<h1>Hello</h1>"
            )

    def test_extracts_tar_archive(self):
        archive = io.BytesIO()
        with tarfile.open(fileobj=archive, mode="w:gz") as tar_file:
            content = b"body{}"
            info = tarfile.TarInfo("site/style.css")
            info.size = len(content)
            tar_file.addfile(info, io.BytesIO(content))
        archive.seek(0)

        with tempfile.TemporaryDirectory() as directory:
            extract_path = Path(directory)
            safe_extract(archive, extract_path, archive_type="tar")

            self.assertEqual((extract_path / "site/style.css").read_bytes(), b"body{}")

    def test_blocks_zip_path_traversal(self):
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, "w") as zip_file:
            zip_file.writestr("../outside.txt", "should not be written")
            zip_file.writestr("site/index.html", "safe")
        archive.seek(0)

        with tempfile.TemporaryDirectory() as directory:
            extract_path = Path(directory)
            safe_extract(archive, extract_path, archive_type="zip")

            self.assertFalse((extract_path.parent / "outside.txt").exists())
            self.assertEqual((extract_path / "site/index.html").read_text(), "safe")

    def test_rejects_invalid_zip(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            self.assertRaisesRegex(ValueError, "Bad zip file"),
        ):
            safe_extract(
                io.BytesIO(b"not a zip"),
                Path(directory),
                archive_type="zip",
            )

    def test_rejects_archive_over_size_limit(self):
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, "w") as zip_file:
            zip_file.writestr("site/index.html", "12345")
        archive.seek(0)

        with (
            tempfile.TemporaryDirectory() as directory,
            self.assertRaisesRegex(ValueError, "too big"),
        ):
            safe_extract(
                archive,
                Path(directory),
                max_size=4,
                archive_type="zip",
            )

    def test_restores_working_directory_after_failure(self):
        original_directory = Path.cwd()

        with (
            tempfile.TemporaryDirectory() as directory,
            self.assertRaisesRegex(ValueError, "Unknown file type"),
        ):
            safe_extract(io.BytesIO(), Path(directory), archive_type="rar")

        self.assertEqual(Path.cwd(), original_directory)


if __name__ == "__main__":
    unittest.main()

import base64
import importlib
import os
import sys
import tempfile
import unittest
from pathlib import Path


class TmpwebTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_directory = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp_directory.name)
        (cls.root / "config.toml").write_text(
            f'domain = "https://example.test"\n'
            "default_retention = 7\n"
            "max_site_size = 1024\n"
            f'web_root = "{cls.root / "web"}"\n'
            f'database_location = "{cls.root / "tmpweb.db"}"\n'
        )
        (cls.root / "web").mkdir()
        cls.original_directory = Path.cwd()
        os.chdir(cls.root)
        sys.path.insert(0, str(cls.original_directory / "src"))
        cls.module = importlib.import_module("tmpweb")

    @classmethod
    def tearDownClass(cls):
        os.chdir(cls.original_directory)
        sys.path.remove(str(cls.original_directory / "src"))
        sys.modules.pop("tmpweb", None)
        cls.temp_directory.cleanup()

    def test_is_valid_json(self):
        self.assertTrue(self.module.is_valid_json(b'{"site": true}'))
        self.assertTrue(self.module.is_valid_json(b" [1, 2] "))
        self.assertFalse(self.module.is_valid_json(b"<html></html>"))
        self.assertFalse(self.module.is_valid_json(b"{invalid}"))

    def test_unwrap_multipart_returns_first_file(self):
        multipart = (
            b"--boundary\r\n"
            b'Content-Disposition: form-data; name="file"; filename="site.zip"\r\n'
            b"Content-Type: application/zip\r\n\r\n"
            b"archive contents\r\n"
            b"--boundary--\r\n"
        )

        self.assertEqual(self.module.unwrap_multipart(multipart), b"archive contents")

    def test_get_web_root_finds_directory_containing_files(self):
        site_root = self.root / "nested"
        (site_root / "site" / "public").mkdir(parents=True)
        (site_root / "site" / "public" / "index.html").write_text("home")

        self.assertEqual(
            self.module.get_web_root(site_root), site_root / "site" / "public"
        )

    def test_authorisation_accepts_matching_token(self):
        token = "tmpweb_test_token"
        self.module.db.execute(
            "INSERT INTO api_tokens VALUES(?, ?);", (token, "test@example.test")
        )
        self.module.db.commit()
        credentials = base64.b64encode(f"token:{token}".encode()).decode()

        self.assertTrue(
            self.module.is_authorised({"HTTP_AUTHORIZATION": f"Basic {credentials}"})
        )
        self.assertFalse(
            self.module.is_authorised({"HTTP_AUTHORIZATION": "Bearer anything"})
        )

    def test_app_routes_ping_and_rejects_remote_delete(self):
        responses = []

        def start_response(status, headers):
            responses.append((status, headers))

        ping_body = self.module.app(
            {"REQUEST_METHOD": "GET", "PATH_INFO": "/ping"}, start_response
        )
        self.assertEqual(responses[-1][0], "200 OK")
        self.assertEqual(ping_body, [])

        delete_body = self.module.app(
            {
                "REQUEST_METHOD": "DELETE",
                "PATH_INFO": "/",
                "REMOTE_ADDR": "192.0.2.10",
            },
            start_response,
        )
        self.assertEqual(responses[-1][0], "403 Forbidden")
        self.assertEqual(delete_body, [])


if __name__ == "__main__":
    unittest.main()

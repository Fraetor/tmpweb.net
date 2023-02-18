import logging
from pathlib import Path
import secrets
import shutil
import sqlite3
import time
import tempfile
import os

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

from . import safe_extractor

db = sqlite3.connect("tmpweb.db")
cur = db.cursor()
query = """CREATE TABLE IF NOT EXISTS sites(
    site_id TEXT PRIMARY KEY,
    creation_date INT,
    expiry_date INT
);
"""
cur.execute(query)
db.commit()

config = tomllib.load(Path("tmpweb_config.toml").read_bytes())


def get_web_root(dir: Path) -> Path:
    """Descend tree until we find either multiple directories or some files."""
    for root, dirs, files in os.walk(dir, followlinks=False):
        if len(dirs) >= 2 or len(files) > 0:
            return Path(root)
    raise ValueError("No files in archive.")


def create_site(archive_path: Path, retention_length: int = config.default_retention):
    # Generated URLs will have a 9 byte long base64 path. As base64 encodes 3 bytes
    # to 4 characters this gives us a nice length of URL whilst having sufficient
    # keyspace for randomly finding a site to take many millennia.
    site_id = secrets.token_urlsafe(9)
    creation_date = int(time.time())
    if retention_length > config.max_retention:
        retention_length = config.max_retention
    expiry_date = creation_date + retention_length * 24 * 3600
    try:
        with tempfile.TemporaryDirectory as tmpdir:
            # Unzip/untar in a vaguely safe way.
            if archive_path.suffix.lower() == ".zip":
                safe_extractor.unzip(archive_path, tmpdir)
            elif ".tar" in archive_path.suffix.lower():
                safe_extractor.untar(archive_path, tmpdir)
            else:
                raise ValueError(f"Unknown filetype for {archive_path}")
            # Delete any symlinks in the archive for security.
            total_size = 0
            for _, dirs, files in os.walk(tmpdir, followlinks=False):
                for dir in dirs:
                    if dir.is_symlink():
                        os.remove(dir.path)
                for file in files:
                    if file.is_symlink():
                        os.remove(file.path)
                    else:
                        total_size += file.stat().st_size
                # Check the extracted site is not too big.
                if total_size > config.max_site_size:
                    raise ValueError(
                        f"Unpacked archive is too big! Max size is {config.max_site_size} bytes."
                    )
            web_root = get_web_root(tmpdir)
            # Record site in database
            query = "INSERT INTO sites VALUES(?, ?, ?);"
            cur.execute(query, site_id, creation_date, expiry_date)
            db.commit()
            shutil.copytree(web_root, config.web_root, dirs_exist_ok=True)
        return {"status": 200, "content": f"https://{config.domain}/{site_id}/"}
    except Exception as err:
        logging.error(err)
        return {"status": 500, "content": f"{err}"}


def delete_old_sites():
    query = "SELECT * FROM sites WHERE expiry_date < ?;"
    for row in cur.execute(query, int(time.time)):
        site_id = row[0]
        shutil.rmtree(Path(config.web_root).joinpath(f"{site_id}/"))
        cur.execute("DELETE FROM sites WHERE site_id IS ?", site_id)
        db.commit()


def handle_request():
    pass

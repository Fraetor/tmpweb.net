import logging
from pathlib import Path
import secrets
import shutil
import sqlite3
import time
import tomllib
import tempfile

db = sqlite3.connect("tmpweb.db")

config = tomllib.load(Path("tmpweb_config.toml").read_bytes())


def create_site(
    site_archive_path: Path, retention_length: int = config.default_retention
):
    # Generated URLs will have a 9 byte long base64 path. As base64 encodes 3 bytes
    # to 4 characters this gives us a nice length of URL whilst having sufficient
    # keyspace for randomly finding a page to take many millennia.
    site_id = secrets.token_urlsafe(9)
    creation_date = int(time.time())
    if retention_length > config.max_retention:
        retention_length = config.max_retention
    expiry_time = creation_date + retention_length * 24 * 3600
    try:
        # https://docs.python.org/3/library/tempfile.html#tempfile.TemporaryDirectory
        with tempfile.TemporaryDirectory as tmpdir:
            # Unzip/untar file. Needs some more thinking around security issues
            # of absolute paths and ../ paths in archives.
            # https://docs.python.org/3/library/shutil.html#shutil.unpack_archive
            shutil.unpack_archive(site_archive_path, tmpdir)

            # Test recursively until we find a subdir with more than a single
            # directory.
            # https://docs.python.org/3/library/os.html#os.scandir
            # https://docs.python.org/3/library/os.html#os.DirEntry.is_dir

            # Record site in database
            # https://docs.python.org/3/library/sqlite3.html
            db.execute("INSERT")

            # Delete any symlinks in the archive for security.
            # https://docs.python.org/3/library/os.html#os.walk
            # https://docs.python.org/3/library/os.html#os.DirEntry
            # https://docs.python.org/3/library/os.html#os.DirEntry.is_symlink
            # https://docs.python.org/3/library/os.html#os.remove
            # https://docs.python.org/3/library/os.html#os.DirEntry.path

            # Copy that (possible) subdir to serving location
            # https://docs.python.org/3/library/shutil.html#shutil.copytree
        # Return URL of site
        return f"https://{config.domain}/{site_id}/"

        # Return empty string if any prior step failed.
    except Exception as err:
        logging.error(err)
        return ""


def delete_old_sites():
    # Sample through database and if the expiry_time is less than the current
    # time delete the site's files, and remove its entry from the database.
    cur = db.execute(
        f"SELECT * FROM sites WHERE expiry_time IS GREATER THAN {int(time.time)}"
    )
    # Do something with the cursor.

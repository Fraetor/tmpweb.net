from pathlib import Path
import secrets
import shutil
import sqlite3
import time
import tomllib


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
        # Unzip/untar file

        # Test recursively until we find a subdir with more than a single directory.

        # Record site in database
        db.execute("INSERT")

        # Delete any symlinks in the archive for security.

        # Copy that (possible) subdir to serving location
        shutil.copytree("")

        # Cleanup site archive and extraction files.
        shutil.rmtree

        # Return URL of site
        return f"https://{config.domain}/{site_id}/"

        # Return empty string if any prior step failed.
    except Exception:
        return ""


def delete_old_sites():
    # Sample through database and if the expiry_time is less than the current
    # time delete the site's files, and remove its entry from the database.
    cur = db.execute(
        f"SELECT * FROM sites WHERE expiry_time IS GREATER THAN {int(time.time)}"
    )
    # Do something with the cursor.

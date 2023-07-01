from pathlib import Path
import logging
import os
import secrets
import shutil
import sqlite3
import tempfile
import time
import tomllib

from safe_extractor import safe_extract


logging.basicConfig(level=os.getenv("LOGLEVEL", "INFO"))

# Read config file.
with open("config.toml", "rb") as fp:
    config = tomllib.load(fp)

# Connect to database and setup table.
db = sqlite3.connect(config["database_location"])
db.execute(
    """\
CREATE TABLE IF NOT EXISTS sites(
    site_id TEXT PRIMARY KEY,
    creation_date INT,
    expiry_date INT
);
"""
)
db.commit()


def get_web_root(directory: Path) -> Path:
    """Descend tree until we find either multiple directories or some files."""
    for root, dirs, files in os.walk(directory, followlinks=False):
        if len(dirs) >= 2 or len(files) > 0:
            return Path(root)
    raise ValueError("No files in archive.")


def create_site(environ):
    """Create a site from a POSTed archive."""

    # Check incoming upload is below max size.
    if int(environ["CONTENT_LENGTH"]) > config["max_site_size"]:
        logging.error(
            "Archive is too big! Max size is %s bytes.", config["max_site_size"]
        )
        return http_response(413)
    upload = environ["wsgi.input"].read(config["max_site_size"])
    if len(environ["wsgi.input"].read(1)):
        logging.error(
            "Archive is too big! Max size is %s bytes.", config["max_site_size"]
        )
        return http_response(413)

    # Save upload to temporary location.
    archive_path = Path(tempfile.gettempdir(), secrets.token_hex())
    if upload[:4] == b"\x50\x4b\x03\x04" or upload[:4] == b"\x50\x4b\x01\x02":
        archive_path = archive_path.with_suffix(".zip")
    elif upload[:9] == b"<!DOCTYPE" or upload[:9] == b"<!doctype":
        archive_path = archive_path.with_suffix(".html")
    else:
        archive_path = archive_path.with_suffix(".tar")
    archive_path.write_bytes(upload)

    with tempfile.TemporaryDirectory() as tmpdir:
        if archive_path.suffix == ".html":
            shutil.move(archive_path, tmpdir)
        else:
            try:
                safe_extract(archive_path, tmpdir, config["max_site_size"])
            except ValueError:
                logging.error("Unknown filetype for %s", {archive_path})
                return http_response(400)
            finally:
                # Remove original archive.
                archive_path.unlink()
        try:
            upload_root = get_web_root(tmpdir)
        except ValueError:
            logging.error("No servable files found in archive.")
            return http_response(400)

        # Generated URLs will have a 9 byte long base64 path. As base64 encodes
        # 3 bytes to 4 characters this gives us a nice length of URL whilst
        # having sufficient keyspace for randomly finding a site to take many
        # millennia.
        site_id = secrets.token_urlsafe(9)
        # Might make retention length configurable as part of the upload in
        # future, probably with a HTTP header.
        creation_date = int(time.time())
        expiry_date = creation_date + config["default_retention"] * 24 * 3600

        # Record site in database.
        query = "INSERT INTO sites VALUES(?, ?, ?);"
        db.execute(query, (site_id, creation_date, expiry_date))
        db.commit()
        # Copy files to web server directory.
        shutil.copytree(upload_root, Path(config["web_root"], site_id))

    url_bytes = f"{config['domain']}/{site_id}/\n".encode()
    logging.info("Created site at %s", url_bytes.decode())
    response = {
        "status": "200 OK",
        "headers": [
            ("Content-Type", "text/plain"),
            ("Content-Length", str(len(url_bytes))),
        ],
        "data": [url_bytes],
    }
    return response


def delete_old_sites():
    """Deletes expired sites."""
    logging.info("Deleting expired sites.")
    query = "SELECT site_id FROM sites WHERE expiry_date < ?;"
    for row in db.execute(query, (int(time.time()),)):
        site_id = row[0]
        logging.info("Deleting site: %s", site_id)
        shutil.rmtree(Path(config["web_root"]).joinpath(f"{site_id}/"))
        db.execute("DELETE FROM sites WHERE site_id = ?;", (site_id,))
    db.commit()
    return http_response(200)


def get_client_address(environ):
    """Gets the address of the client"""
    try:
        return environ["HTTP_FORWARDED"].split(",")[-1].strip()
    except KeyError:
        try:
            return environ["HTTP_X_FORWARDED_FOR"].split(",")[-1].strip()
        except KeyError:
            return environ["REMOTE_ADDR"]


def http_response(status_code):
    """Returns a HTTP response with an empty body."""
    status = {
        200: "200 OK",
        400: "400 Bad Request",
        403: "403 Forbidden",
        404: "404 Not Found",
        405: "405 Method Not Allowed",
        413: "413 Content Too Large",
        418: "418 I'm a teapot",
        500: "500 Internal Server Error",
        507: "507 Insufficient Storage",
    }
    return {
        "status": status[status_code],
        "headers": [("Content-Length", "0")],
        "data": [],
    }


def app(environ, start_response):
    """Entry point of WSGI app."""
    try:
        logging.debug("Received %s request", environ["REQUEST_METHOD"])
        if environ["REQUEST_METHOD"] == "POST":
            response = create_site(environ)
        elif environ["REQUEST_METHOD"] == "DELETE":
            if get_client_address(environ) == "127.0.0.1":
                response = delete_old_sites()
            else:
                response = http_response(403)
        else:
            logging.error("Unhandled request method: %s", environ["REQUEST_METHOD"])
            response = http_response(405)
    except Exception as err:
        logging.error(err)
        response = http_response(500)

    start_response(response["status"], response["headers"])
    return response["data"]

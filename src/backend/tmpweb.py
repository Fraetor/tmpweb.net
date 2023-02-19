import logging
from pathlib import Path
import mimetypes
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

from safe_extractor import safe_extract


logging.basicConfig(level=logging.DEBUG)

# Read config file.
with open("tmpweb_config.toml", "rb") as fp:
    config = tomllib.load(fp)

# Connect to database and setup table.
db = sqlite3.connect(config["database_location"])
query = """CREATE TABLE IF NOT EXISTS sites(
    site_id TEXT PRIMARY KEY,
    creation_date INT,
    expiry_date INT
);
"""
db.execute(query)
db.commit()


def get_web_root(dir: Path) -> Path:
    """Descend tree until we find either multiple directories or some files."""
    for root, dirs, files in os.walk(dir, followlinks=False):
        if len(dirs) >= 2 or len(files) > 0:
            return Path(root)
    raise ValueError("No files in archive.")


def create_site(environ):
    """Create a site from a POSTed archive."""
    # Save archive
    if int(environ["CONTENT_LENGTH"]) < config["max_site_size"]:
        body = environ["wsgi.input"]
        archive = body.read(config["max_site_size"])
        if len(body.read(1)):
            logging.error(
                f"Archive is too big! Max size is {config['max_site_size']} bytes."
            )
            return http_response(413)
        if archive[:4] == b"\x50\x4b\x03\x04" or archive[:4] == b"\x50\x4b\x01\x02":
            suffix = ".zip"
        else:
            suffix = ".tar"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as file:
            archive_path = Path(file.name)
            file.write(archive)
    else:
        logging.error(
            f"Archive is too big! Max size is {config['max_site_size']} bytes."
        )
        return http_response(413)
    # Might make this configurable in future.
    retention_length = config["default_retention"]
    # Generated URLs will have a 9 byte long base64 path. As base64 encodes 3 bytes
    # to 4 characters this gives us a nice length of URL whilst having sufficient
    # keyspace for randomly finding a site to take many millennia.
    site_id = secrets.token_urlsafe(9)
    creation_date = int(time.time())
    if retention_length > config["max_retention"]:
        retention_length = config["max_retention"]
    expiry_date = creation_date + retention_length * 24 * 3600
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                safe_extract(archive_path, tmpdir, config["max_site_size"])
            except ValueError:
                logging.error(f"Unknown filetype for {archive_path}")
                return http_response(400)
            finally:
                # Remove original archive.
                archive_path.unlink()
            try:
                web_root = get_web_root(tmpdir)
            except ValueError:
                logging.error("No servable files found in archive.")
                return http_response(400)
            # Record site in database
            query = "INSERT INTO sites VALUES(?, ?, ?);"
            db.execute(query, (site_id, creation_date, expiry_date))
            db.commit()
            shutil.copytree(
                web_root, Path(config["web_root"], site_id), dirs_exist_ok=True
            )
    except Exception as err:
        logging.error(err)
        return http_response(500)
    url = f"https://{config['domain']}/{site_id}/\n".encode()
    logging.info(f"Created site at {url.decode()}")
    response = {
        "status": "200 OK",
        "headers": [
            ("Content-Type", "text/plain"),
            ("Content-Length", f"{len(url)}"),
        ],
        "data": [url],
    }
    return response


def get_client_address(environ):
    """Gets the address of the client"""
    try:
        return environ["HTTP_FORWARDED"].split(",")[-1].strip()
    except KeyError:
        try:
            return environ["HTTP_X_FORWARDED_FOR"].split(",")[-1].strip()
        except KeyError:
            return environ["REMOTE_ADDR"]


def delete_old_sites():
    """Deletes expired sites."""
    logging.info("Deleting expired sites.")
    query = "SELECT site_id FROM sites WHERE expiry_date < ?;"
    for row in db.execute(query, (int(time.time()),)):
        site_id = row[0]
        shutil.rmtree(Path(config["web_root"]).joinpath(f"{site_id}/"))
        db.execute("DELETE FROM sites WHERE site_id = ?;", (site_id,))
        db.commit()
    return http_response(200)


def redirect(target_path, temporary: bool = False):
    if temporary:
        response = {
            "status": "302 Found",
            "headers": [("Location", f"{target_path}")],
            "data": [],
        }
    else:
        response = {
            "status": "301 Moved Permanently",
            "headers": [("Location", f"{target_path}")],
            "data": [],
        }
    return response


def get_page(environ):
    # Sanitise paths.
    path = Path(config["web_root"], environ["PATH_INFO"]).resolve()
    if not path.is_relative_to(config["web_root"]):
        file = open(Path(config["web_root"], "404.html"), "rb")
        if "wsgi.file_wrapper" in environ:
            data = environ["wsgi.file_wrapper"](file)
        else:
            data = iter(lambda: file.read(), "")
        return {
            "status": "404 Not Found",
            "headers": [("Content-Type", "text/html")],
            "data": data,
        }
    html_suffixes = (".html", ".htm")
    if path.suffix in html_suffixes:
        return {
            "status": "301 Moved Permanently",
            "headers": [("Location", f"/{path.relative_to(config['web_root']).stem}")],
            "data": [],
        }
    if path.suffix == "":
        for suffix in [".html", ".htm", ".txt"]:
            if path.with_suffix(suffix).is_file():
                path = path.with_suffix(suffix)
                break
    response = {
        "status": "200 OK",
        "headers": [("Content-Type", mimetypes.guess_type(path))],
    }
    file = open(path, "rb")
    if "wsgi.file_wrapper" in environ:
        response["data"] = environ["wsgi.file_wrapper"](file)
    else:
        response["data"] = iter(lambda: file.read(), "")
    return response


def http_response(status_code):
    """Returns a HTTP response with an empty body."""
    status = {
        200: "200 OK",
        400: "400 Bad Request",
        403: "403 Forbidden",
        404: "404 Not Found",
        405: "405 Method Not Allowed",
        413: "413 Content Too Large",
        500: "500 Internal Server Error",
        507: "507 Insufficient Storage",
    }
    return {
        "status": status[status_code],
        "headers": [("Content-Length", "0")],
        "data": [],
    }


def app(environ, start_response):
    match environ["REQUEST_METHOD"]:
        case "GET":
            response = get_page(environ)
        case "POST":
            response = create_site(environ)
        case "DELETE":
            if get_client_address(environ) == "127.0.0.1":
                response = delete_old_sites()
            else:
                response = http_response(403)
        case _:
            response = http_response(405)
    start_response(response["status"], response["headers"])
    return response["data"]

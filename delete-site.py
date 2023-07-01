#! /usr/bin/env python3

from pathlib import Path
import shutil
import sqlite3
import sys
import tomllib

if len(sys.argv) < 2 or "-h" in sys.argv or "--help" in sys.argv:
    print(f"Usage: {sys.argv[0]} site_id [site_id]...\nDeletes sites matching site_id.")
    sys.exit(1)

# Read config file.
with open("config.toml", "rb") as fp:
    config = tomllib.load(fp)

with sqlite3.connect(config["database_location"]) as db:
    for site_id in sys.argv[1:]:
        print(f"Deleting site {site_id}")
        shutil.rmtree(Path(config["web_root"]).joinpath(f"{site_id}/"))
        db.execute("DELETE FROM sites WHERE site_id = ?;", (site_id,))
        db.commit()

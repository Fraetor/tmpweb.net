#! /usr/bin/env python3

import shutil

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

with open("src/config.toml", "rb") as fp:
    config = tomllib.load(fp)

print(f"Installing into {config['web_root']}...")
shutil.copytree("static/", config["web_root"], dirs_exist_ok=True)

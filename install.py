#! /usr/bin/env python3

import shutil
import os
try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

with open("src/config.toml", "rb") as fp:
    config = tomllib.load(fp)

print(f"Installing into {config['web_root']}...")
os.makedirs(config["web_root"], exist_ok=True)
shutil.copytree("static/", config["web_root"], dirs_exist_ok=True)

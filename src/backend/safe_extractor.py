################################################################################
# safe_extractor.py
#
# Copyright © 2022 Jonathan Porta <jonathan@jonathanPorta.com>
# https://github.com/JonathanPorta/safe_extractor
#
# Modified by James Frost <git@frost.cx>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the “Software”), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
################################################################################

import os
import sys
from pathlib import Path
import tarfile
import zipfile


def _contains_path(path: Path, parent_path: Path):
    try:
        path = Path(path).resolve()
    except RuntimeError:
        return False
    return path.is_relative_to(parent_path.resolve())


def _safe_tar_members(members: tarfile.TarInfo, extract_path: Path):
    valid_members = []
    for member in members:
        if member.isdev():
            print(f"{member.name} is blocked (device file)", file=sys.stderr)
        elif member.issym() or member.islnk():
            print(f"{member.name} is blocked (symlink or hard link)", file=sys.stderr)
        elif not _contains_path(member.name, extract_path):
            print(f"{member.name} is blocked (illegal path)", file=sys.stderr)
        else:
            valid_members.append(member)
        return valid_members


def _safe_zip_members(members: zipfile.ZipInfo, extract_path: Path):
    valid_members = []
    for member in members:
        # ZIP can't contain device files/symlinks... Probably...
        if not _contains_path(member.filename, extract_path):
            print(f"{member.filename} is blocked (illegal path)", file=sys.stderr)
        else:
            valid_members.append(member)
        return valid_members


def untar(tar_file: Path, extract_path: Path = Path(".")):
    extract_path = Path(extract_path)
    old_cwd = Path.cwd()
    os.chdir(extract_path)
    try:
        with tarfile.open(tar_file) as archive:
            permitted_members = _safe_tar_members(archive.getmembers(), extract_path)
            archive.extractall(path=extract_path, members=permitted_members)
    finally:
        os.chdir(old_cwd)


def unzip(zip_file: Path, extract_path: Path = Path(".")):
    extract_path = Path(extract_path)
    old_cwd = Path.cwd()
    os.chdir(extract_path)
    try:
        with zipfile.ZipFile(zip_file) as archive:
            permitted_members = _safe_zip_members(archive.infolist(), extract_path)
            archive.extractall(path=extract_path, members=permitted_members)
    finally:
        os.chdir(old_cwd)

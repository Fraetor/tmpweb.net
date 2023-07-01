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

from pathlib import Path
import logging
import os
import tarfile
import zipfile

logging.basicConfig(level=logging.INFO)


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
            logging.info("%s is blocked (device file)", {member.name})
        elif member.issym() or member.islnk():
            logging.info("%s is blocked (symlink or hard link)", member.name)
        elif not _contains_path(member.name, extract_path):
            logging.info("%s is blocked (illegal path)", member.name)
        else:
            valid_members.append(member)
    return valid_members


def _safe_zip_members(members: zipfile.ZipInfo, extract_path: Path):
    valid_members = []
    for member in members:
        # ZIP can't contain device files/symlinks... Probably...
        if not _contains_path(member.filename, extract_path):
            logging.info("%s is blocked (illegal path)", member.filename)
        else:
            valid_members.append(member)
    return valid_members


def _delete_remaining_symlinks(extract_path: Path, max_size: int):
    # Delete any symlinks in the archive for security.
    total_size = 0
    for root, dirs, files in os.walk(extract_path, followlinks=False):
        for directory in dirs:
            directory = Path(root, directory)
            if directory.is_symlink():
                directory.unlink()
        for file in files:
            file = Path(root, file)
            if file.is_symlink():
                file.unlink()
            else:
                total_size += file.stat().st_size
        # Check the extracted site is not too big.
        if total_size > max_size:
            raise ValueError(
                f"Unpacked archive is too big! Max size is {max_size} bytes."
            )


def safe_extract(
    file_path: Path, extract_path: Path = Path("."), max_size: int = 2**32 - 1
):
    """Unzip/untar in a vaguely safe way."""
    extract_path = Path(extract_path)
    old_cwd = Path.cwd()
    os.chdir(extract_path)
    try:
        if file_path.suffix.lower() == ".zip":
            try:
                with zipfile.ZipFile(file_path) as archive:
                    permitted_members = _safe_zip_members(
                        archive.infolist(), extract_path
                    )
                    archive.extractall(path=extract_path, members=permitted_members)
                _delete_remaining_symlinks(extract_path, max_size)
            except zipfile.BadZipFile as err:
                raise ValueError("Bad zip file") from err
        elif file_path.suffix.lower() == ".tar":
            try:
                with tarfile.open(file_path) as archive:
                    permitted_members = _safe_tar_members(
                        archive.getmembers(), extract_path
                    )
                    archive.extractall(path=extract_path, members=permitted_members)
                _delete_remaining_symlinks(extract_path, max_size)
            except tarfile.TarError as err:
                raise ValueError("Bad tar file") from err
        else:
            raise ValueError(f"Unknown file extension: {file_path.suffix}")
    finally:
        os.chdir(old_cwd)

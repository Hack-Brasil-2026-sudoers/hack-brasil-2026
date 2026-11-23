"""Bounded repository archive handling. Errors contain public messages, never remote bodies or URLs."""
import stat
import time
import zipfile
import zlib

import httpx
from pathlib import Path, PurePosixPath

MAX_DOWNLOAD_BYTES = 25 * 1024 * 1024
MAX_ARCHIVE_BYTES = 100 * 1024 * 1024
MAX_FILE_BYTES = 20 * 1024 * 1024
MAX_ARCHIVE_ENTRIES = 5000
MAX_ARCHIVE_SECONDS = 120
CHUNK_BYTES = 65536


class ArchiveError(ValueError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def receive_archive(response, destination: Path):
    """Consume a real streaming HTTP response with transfer and ZIP envelope validation."""
    started = time.monotonic()
    if response.status_code != 200:
        raise ArchiveError("download_http", f"GitHub archive download returned HTTP {response.status_code}; no scanners ran.")
    if response.headers.get("content-encoding", "identity").lower() != "identity":
        raise ArchiveError("download_encoding", "GitHub returned an unexpected HTTP content encoding; archive download was blocked.")
    content_type = response.headers.get("content-type", "").split(";", 1)[0].lower().strip()
    if content_type and content_type not in ("application/zip", "application/x-zip-compressed", "application/octet-stream"):
        raise ArchiveError("download_format", "GitHub returned a non-ZIP response instead of a repository archive.")
    length = response.headers.get("content-length")
    if length is not None and not length.isdigit():
        raise ArchiveError("download_length", "GitHub returned an invalid archive Content-Length header.")
    expected = int(length) if length is not None else None
    if expected is not None and expected > MAX_DOWNLOAD_BYTES:
        raise ArchiveError("download_limit", "Repository ZIP exceeds the 25 MiB download limit. Remove large generated assets before retrying.")
    total = 0
    try:
        with destination.open("xb") as output:
            for chunk in response.iter_bytes(chunk_size=CHUNK_BYTES):
                if time.monotonic() - started > MAX_ARCHIVE_SECONDS:
                    raise ArchiveError("download_timeout", "Repository archive download exceeded the 120-second limit. Retry when the connection is stable.")
                total += len(chunk)
                if total > MAX_DOWNLOAD_BYTES:
                    raise ArchiveError("download_limit", "Repository ZIP exceeds the 25 MiB download limit. Remove large generated assets before retrying.")
                output.write(chunk)
    except httpx.RemoteProtocolError as exc:
        raise ArchiveError("download_incomplete", "Repository archive download was interrupted or incomplete. Retry the analysis.") from exc
    if expected is not None and total != expected:
        raise ArchiveError("download_incomplete", "Repository archive download is incomplete: received size differs from Content-Length. Retry the analysis.")
    if not zipfile.is_zipfile(destination):
        raise ArchiveError("invalid_zip", "Repository response is not a readable ZIP: its directory is missing or damaged. Retry the download.")
    return total


def extract_archive(archive: Path, target: Path):
    started = time.monotonic()
    if archive.stat().st_size > MAX_DOWNLOAD_BYTES:
        raise ArchiveError("download_limit", "Repository ZIP exceeds the 25 MiB download limit.")
    try:
        with zipfile.ZipFile(archive) as package:
            entries = package.infolist()
            if not entries:
                raise ArchiveError("archive_empty", "Repository ZIP is empty; no files are available to scan.")
            if len(entries) > MAX_ARCHIVE_ENTRIES:
                raise ArchiveError("archive_entry_limit", "Repository ZIP exceeds the limit of 5,000 entries (files and directories).")
            root = None
            names = set()
            planned = []
            declared_total = 0
            for entry in entries:
                raw = entry.orig_filename
                path = PurePosixPath(raw)
                if (path.is_absolute() or ".." in path.parts or "\\" in raw or "\x00" in raw
                        or not path.parts or any(":" in part for part in path.parts)):
                    raise ArchiveError("archive_unsafe_path", "Repository ZIP contains an unsafe path; extraction was blocked.")
                root = root or path.parts[0]
                if path.parts[0] != root:
                    raise ArchiveError("archive_roots", "Repository ZIP must contain a single root directory.")
                relative = Path(*path.parts[1:])
                mode = entry.external_attr >> 16
                if stat.S_IFMT(mode) not in (0, stat.S_IFREG, stat.S_IFDIR):
                    raise ArchiveError("archive_special_file", "Repository ZIP contains a link or special file; extraction was blocked.")
                if relative in names:
                    raise ArchiveError("archive_duplicate", "Repository ZIP contains duplicate or conflicting paths; extraction was blocked.")
                names.add(relative)
                if entry.flag_bits & 1:
                    raise ArchiveError("archive_encrypted", "Encrypted ZIP entries cannot be scanned.")
                if entry.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):
                    raise ArchiveError("archive_compression", "Repository ZIP uses an unsupported compression method.")
                if entry.is_dir():
                    if entry.file_size:
                        raise ArchiveError("archive_directory", "Repository ZIP contains a directory with file data; extraction was blocked.")
                    continue
                if not relative.parts:
                    raise ArchiveError("archive_root_file", "Repository ZIP contains a file instead of a root directory.")
                if entry.file_size > MAX_FILE_BYTES:
                    raise ArchiveError("archive_file_limit", "A repository file exceeds the 20 MiB per-file limit. Remove large generated files or binaries before retrying.")
                declared_total += entry.file_size
                if declared_total > MAX_ARCHIVE_BYTES:
                    raise ArchiveError("archive_total_limit", "Repository ZIP exceeds the 100 MiB uncompressed limit.")
                planned.append((entry, relative))
            # Validate the entire layout before writing anything, including file/parent collisions.
            file_paths = {relative for _, relative in planned}
            if any(parent in file_paths for path in names for parent in path.parents if parent.parts):
                raise ArchiveError("archive_conflict", "Repository ZIP contains conflicting file and directory paths.")
            if not planned:
                raise ArchiveError("archive_empty", "Repository ZIP contains no regular files to scan.")
            actual_total = 0
            if target.is_symlink():
                raise ArchiveError("archive_unsafe_path", "Extraction root is a symbolic link; extraction was blocked.")
            target = target.resolve()
            for entry, relative in planned:
                output = target / relative
                # Refuse pre-existing symlinks as well as symlinks encoded in the ZIP.
                if any(parent.is_symlink() for parent in output.parents if parent != target.parent):
                    raise ArchiveError("archive_unsafe_path", "Extraction destination contains a symbolic link; extraction was blocked.")
                output.parent.mkdir(parents=True, exist_ok=True)
                copied = 0
                with package.open(entry) as src, output.open("xb") as dst:
                    while chunk := src.read(CHUNK_BYTES):
                        if time.monotonic() - started > MAX_ARCHIVE_SECONDS:
                            raise ArchiveError("archive_timeout", "Repository ZIP extraction exceeded the 120-second limit.")
                        copied += len(chunk)
                        actual_total += len(chunk)
                        if copied > MAX_FILE_BYTES or copied > entry.file_size:
                            raise ArchiveError("archive_file_limit", "Extracted file exceeds its declared size or the 20 MiB per-file limit.")
                        if actual_total > MAX_ARCHIVE_BYTES:
                            raise ArchiveError("archive_total_limit", "Extracted repository exceeds the 100 MiB uncompressed limit.")
                        dst.write(chunk)
                if copied != entry.file_size:
                    raise ArchiveError("archive_incomplete", "Repository ZIP contains an incomplete file; extraction did not finish.")
                output.chmod(0o600)
    except zipfile.BadZipFile as exc:
        raise ArchiveError("archive_corrupt", "Repository ZIP is damaged or failed CRC verification. No scanners ran; retry the download.") from exc
    except (NotImplementedError, RuntimeError, EOFError, zlib.error) as exc:
        raise ArchiveError("archive_format", "Repository ZIP cannot be decompressed: unsupported or damaged archive data.") from exc

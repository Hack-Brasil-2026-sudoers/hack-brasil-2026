"""Regression coverage with real ZIP files and real local HTTP transfers, without mocked transports."""
import io
import stat
import threading
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import httpx
import pytest

from cybercheck.archives import (ArchiveError, MAX_ARCHIVE_ENTRIES,
                                MAX_DOWNLOAD_BYTES, MAX_FILE_BYTES, extract_archive, receive_archive)


def write_member(package, name, size):
    with package.open(name, 'w') as member:
        remaining = size
        while remaining:
            part = b'x' * min(65536, remaining)
            member.write(part)
            remaining -= len(part)


def error_code(path, target, code):
    with pytest.raises(ArchiveError) as raised:
        extract_archive(path, target)
    assert raised.value.code == code


def test_real_zip_with_original_17096584_byte_binary_is_extracted(tmp_path):
    archive = tmp_path / 'repo.zip'
    binary = '.agents/skills/impeccable/scripts/bin/windows-x64/impeccable.exe'
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as package:
        write_member(package, 'github-root/' + binary, 17096584)
        package.writestr('github-root/backend/app.py', 'eval(input())\n')
    target = tmp_path / 'source'; target.mkdir()
    extract_archive(archive, target)
    assert (target / binary).stat().st_size == 17096584
    assert (target / 'backend/app.py').read_text() == 'eval(input())\n'
    assert (target / binary).stat().st_mode & 0o077 == 0


def test_limits_are_checked_before_extracting_any_file(tmp_path):
    archive = tmp_path / 'repo.zip'
    target = tmp_path / 'source'; target.mkdir()
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as package:
        package.writestr('root/first.py', 'pass')
        write_member(package, 'root/large.bin', MAX_FILE_BYTES + 1)
    error_code(archive, target, 'archive_file_limit')
    assert not list(target.rglob('*'))
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as package:
        for i in range(5):
            write_member(package, f'root/file-{i}', MAX_FILE_BYTES)
        package.writestr('root/overflow', 'x')
    error_code(archive, target, 'archive_total_limit')
    assert not list(target.rglob('*'))
    with zipfile.ZipFile(archive, 'w') as package:
        for i in range(MAX_ARCHIVE_ENTRIES + 1):
            package.writestr(f'root/file-{i}', '')
    error_code(archive, target, 'archive_entry_limit')
    assert not list(target.rglob('*'))


@pytest.mark.parametrize('name', ['root/../escape', '/absolute', 'root/path\\escape', 'C:/escape', 'root/C:/escape'])
def test_traversal_paths_still_fail(tmp_path, name):
    archive=tmp_path/'repo.zip'; target=tmp_path/'source'; target.mkdir()
    with zipfile.ZipFile(archive, 'w') as package:
        package.writestr(name, 'unsafe')
    error_code(archive, target, 'archive_unsafe_path')
    assert not list(target.rglob('*'))


def test_symlinks_and_path_conflicts_are_rejected(tmp_path):
    archive=tmp_path/'repo.zip'; target=tmp_path/'source'; target.mkdir()
    info=zipfile.ZipInfo('root/link');info.create_system=3
    info.external_attr=(stat.S_IFLNK|0o777)<<16
    with zipfile.ZipFile(archive, 'w') as package:package.writestr(info, '../../outside')
    error_code(archive,target,'archive_special_file')
    with zipfile.ZipFile(archive, 'w') as package:
        package.writestr('root/folder', 'file')
        package.writestr('root/folder/file.py', 'pass')
    error_code(archive,target,'archive_conflict')
    assert not list(target.rglob('*'))
    with zipfile.ZipFile(archive, 'w') as package:package.writestr('root/existing/file.py', 'pass')
    outside=tmp_path/'outside';outside.mkdir()
    (target/'existing').symlink_to(outside,target_is_directory=True)
    error_code(archive,target,'archive_unsafe_path')
    assert not list(outside.iterdir())


def test_corrupt_zip_and_crc_failures_are_specific(tmp_path):
    archive=tmp_path/'repo.zip';target=tmp_path/'source';target.mkdir()
    archive.write_bytes(b'not a ZIP')
    error_code(archive,target,'archive_corrupt')
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_STORED) as package:
        package.writestr('root/file.py', 'unique-file-content')
    raw=archive.read_bytes().replace(b'unique-file-content',b'broken-file-content')
    archive.write_bytes(raw)
    error_code(archive,target,'archive_corrupt')


@pytest.fixture
def http_archive():
    data=io.BytesIO()
    with zipfile.ZipFile(data,'w') as package:package.writestr('root/app.py','pass\n')
    payload=data.getvalue()
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_GET(self):
            self.send_response(502 if self.path=='/http-error' else 200)
            self.send_header('Content-Type','text/html' if self.path=='/html' else 'application/zip')
            if self.path=='/too-large':self.send_header('Content-Length',str(MAX_DOWNLOAD_BYTES+1))
            elif self.path=='/short':self.send_header('Content-Length',str(len(payload)+100))
            self.end_headers()
            if self.path=='/too-large':return
            try:
                if self.path=='/actual-limit':
                    for _ in range(MAX_DOWNLOAD_BYTES//65536+1):self.wfile.write(b'x'*65536)
                else:self.wfile.write(b'<html>Error</html>' if self.path=='/html' else b'not ZIP' if self.path=='/invalid' else payload)
            except (BrokenPipeError,ConnectionResetError):pass
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:yield f'http://127.0.0.1:{server.server_port}'
    finally:server.shutdown();server.server_close();thread.join(timeout=3)


def test_http_stream_without_content_length_is_a_valid_zip(http_archive,tmp_path):
    archive=tmp_path/'repo.zip'
    with httpx.stream('GET',http_archive+'/valid',trust_env=False) as response:
        receive_archive(response,archive)
    target=tmp_path/'source';target.mkdir()
    extract_archive(archive,target)
    assert (target/'app.py').read_text()=='pass\n'


@pytest.mark.parametrize(('path','code'),[('/too-large','download_limit'),('/actual-limit','download_limit'),('/html','download_format'),('/http-error','download_http'),('/invalid','invalid_zip'),('/short','download_incomplete')])
def test_real_http_failures_are_distinguished(http_archive,tmp_path,path,code):
    with httpx.stream('GET',http_archive+path,trust_env=False) as response:
        with pytest.raises(ArchiveError) as raised:
            receive_archive(response,tmp_path/'repo.zip')
    assert raised.value.code==code

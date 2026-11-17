"""Install official binaries pinned in the lockfile after verifying SHA-256."""
import hashlib
import json
import platform
import tarfile
import tempfile
from pathlib import Path
from urllib.request import urlopen


def install(tool, directory):
    directory.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=directory) as tmp:
        download = Path(tmp) / "download"
        checksum = hashlib.sha256()
        total = 0
        with urlopen(tool["url"], timeout=30) as response, download.open("wb") as output:
            while chunk := response.read(65536):
                total += len(chunk)
                if total > 150 * 1024 * 1024:
                    raise ValueError("Download exceeds 150 MiB.")
                checksum.update(chunk)
                output.write(chunk)
        if checksum.hexdigest() != tool["sha256"]:
            raise ValueError(f"SHA-256 mismatch: {tool['name']}. Binary was not installed.")
        binary = Path(tmp) / "binary"
        if "archive_member" in tool:
            with tarfile.open(download) as archive:
                member = archive.getmember(tool["archive_member"])
                if not member.isfile() or member.size > 150 * 1024 * 1024:
                    raise ValueError("Invalid binary archive entry.")
                binary.write_bytes(archive.extractfile(member).read())
        else:
            download.rename(binary)
        binary.chmod(0o755)
        binary.replace(directory / tool["name"])


def main():
    if platform.system() != "Linux" or platform.machine() not in ("x86_64", "AMD64"):
        raise SystemExit("The initial installer supports Linux x86_64. Configure executables manually on other systems.")
    root = Path(__file__).resolve().parents[1]
    for tool in json.loads((root / "tools.lock.json").read_text())["tools"]:
        install(tool, root / ".tools")
        print(f"{tool['name']} {tool['version']}: SHA-256 verified; license {tool['license']}.")


if __name__ == "__main__":
    main()

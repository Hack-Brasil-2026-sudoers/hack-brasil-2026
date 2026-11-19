"""Pull the digest-pinned container images used by the isolated web laboratory."""
import json
import platform
import re
import shutil
import subprocess
from pathlib import Path


def main():
    runtime = shutil.which("podman")
    if platform.system() != "Linux" or not runtime:
        raise SystemExit("The first web tool laboratory requires Linux and Podman.")
    lock = json.loads((Path(__file__).resolve().parents[1] / "web-tools.lock.json").read_text())
    for name, spec in lock["images"].items():
        image = spec["image"]
        if not re.fullmatch(r"[a-z0-9./_-]+@sha256:[0-9a-f]{64}", image):
            raise SystemExit("Refusing an image that is not pinned by digest.")
        print(f"Installing {name} {spec['version']} ({spec['license']}).", flush=True)
        subprocess.run([runtime, "pull", image], check=True, timeout=600)


if __name__ == "__main__":
    main()

import fcntl
import shutil
import stat
import tempfile
import time
import zipfile
from pathlib import Path, PurePosixPath

import httpx

from .config import Settings
from .github import GitHub, GitHubError
from .scanners import run_scanners
from .store import Store


def extract_archive(archive: Path, target: Path):
    total = 0
    names = set()
    with zipfile.ZipFile(archive) as package:
        entries = package.infolist()
        if not entries or len(entries) > 5000:
            raise ValueError("Arquivo vazio ou mais de 5.000 entradas.")
        root = None
        for entry in entries:
            path = PurePosixPath(entry.filename)
            if path.is_absolute() or ".." in path.parts or "\\" in entry.filename:
                raise ValueError("Arquivo com caminho inseguro.")
            if not path.parts:
                raise ValueError("Caminho vazio no arquivo.")
            root = root or path.parts[0]
            if path.parts[0] != root:
                raise ValueError("Arquivo deve conter uma única raiz.")
            relative = Path(*path.parts[1:])
            mode = entry.external_attr >> 16
            if stat.S_ISLNK(mode) or (stat.S_IFMT(mode) not in (0, stat.S_IFREG, stat.S_IFDIR)):
                raise ValueError("Links e arquivos especiais não são aceitos.")
            if entry.is_dir():
                continue
            if not relative.parts or relative in names:
                raise ValueError("Entrada inválida ou duplicada.")
            names.add(relative)
            if entry.file_size > 2 * 1024 * 1024:
                raise ValueError("Arquivo individual excede 2 MiB.")
            total += entry.file_size
            if total > 100 * 1024 * 1024:
                raise ValueError("Conteúdo descompactado excede 100 MiB.")
            output = target / relative
            output.parent.mkdir(parents=True, exist_ok=True)
            with package.open(entry) as src, output.open("xb") as dst:
                shutil.copyfileobj(src, dst, 65536)
            output.chmod(0o600)


def process(analysis, store: Store, github: GitHub, settings: Settings):
    try:
        with tempfile.TemporaryDirectory(prefix="analysis-", dir=store.directory) as tmp:
            working = Path(tmp)
            archive = working / "source.zip"
            source = working / "source"
            source.mkdir()
            github.download(analysis, archive)
            extract_archive(archive, source)
            archive.unlink()
            findings, checks = run_scanners(source, working, settings, analysis["dependency_lookup"])
            statuses = [c["status"] for c in checks]
            status = "completed" if all(s == "completed" for s in statuses) else (
                "partial" if any(s in ("completed", "partial") for s in statuses) else "failed")
        # Só finaliza depois de descartar código e saídas brutas.
        store.finish(analysis["id"], status, findings, checks)
    except GitHubError as exc:
        store.finish(analysis["id"], "failed", error=str(exc))
    except (ValueError, zipfile.BadZipFile):
        store.finish(analysis["id"], "failed", error="Arquivo inválido ou excede os limites do MVP.")
    except (OSError, httpx.HTTPError):
        store.finish(analysis["id"], "failed", error="Falha de rede ou de armazenamento durante a análise.")
    except Exception:
        # Erros inesperados não devem persistir conteúdo/token presente em exceções.
        store.finish(analysis["id"], "failed", error="Falha inesperada no worker. Solicite uma nova análise.")


def run(settings: Settings, once=False):
    store = Store(settings.data_dir)
    with (store.directory / "worker.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SystemExit("Já existe um worker para esse diretório de dados.")
        # Com o lock adquirido, nenhum processo anterior deve estar trabalhando aqui.
        for old in store.directory.glob("analysis-*"):
            if old.is_dir() and not old.is_symlink():
                shutil.rmtree(old)
        store.recover()
        github = GitHub(settings)
        while True:
            analysis = store.claim()
            if analysis:
                process(analysis, store, github, settings)
            if once:
                return
            time.sleep(2)

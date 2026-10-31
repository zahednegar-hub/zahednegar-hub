"""Build the cPanel / Passenger deployment package.

Usage::

    python tools/build_cpanel_package.py            # writes dist/fanoos-v<version>-cpanel.zip (+ .sha256)

Only an explicit allow-list is copied: the ``fanoos`` package (``.py`` files), the web UI,
the brand assets, the deployment templates in ``deployment/cpanel/`` and the license.
Nothing else (tests, docs, screenshots, CI, git metadata, caches, ``.env`` files) can end
up in the archive. The build fails if anything that looks like a real API key is found.
"""

from __future__ import annotations

import hashlib
import re
import shutil
import sys
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TEMPLATES = REPO / "deployment" / "cpanel"
FIXED_TIME = (2026, 1, 1, 0, 0, 0)  # deterministic archive timestamps
APP_DIR = "fanoos-app"  # folder created when the ZIP is extracted = cPanel "Application root"

KEY_SHAPES = re.compile(rb"(xai-[A-Za-z0-9]{20,}|AIza[0-9A-Za-z_\-]{30,}|gsk_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9_\-]{24,})")
FORBIDDEN_NAMES = {".env", ".git", ".github", "__pycache__", ".pytest_cache", "node_modules", ".venv", "tests"}


def version() -> str:
    match = re.search(r'^__version__ = "([^"]+)"', (REPO / "fanoos" / "__init__.py").read_text(encoding="utf-8"), re.M)
    if not match:
        raise SystemExit("cannot read fanoos.__version__")
    return match.group(1)


def collect() -> list[tuple[Path, str]]:
    """Return (source file, archive path) pairs."""
    files: list[tuple[Path, str]] = []
    for path in sorted((REPO / "fanoos").glob("*.py")):
        files.append((path, f"fanoos/{path.name}"))
    for base in ("web", "assets"):
        for path in sorted((REPO / base).rglob("*")):
            if path.is_file() and not (set(path.relative_to(REPO).parts) & FORBIDDEN_NAMES):
                files.append((path, path.relative_to(REPO).as_posix()))
    for name in ("passenger_wsgi.py", "requirements.txt", ".env.example", "README_DEPLOY.md", "DEPLOY_CPanel_FA.md"):
        files.append((TEMPLATES / name, name))
    files.append((REPO / "LICENSE", "LICENSE"))
    files.append((REPO / "CHANGELOG.md", "CHANGELOG.md"))
    missing = [str(src) for src, _ in files if not src.is_file()]
    if missing:
        raise SystemExit("missing files: " + ", ".join(missing))
    return files


def check(files: list[tuple[Path, str]]) -> None:
    """Refuse forbidden paths and anything shaped like a real credential."""
    for src, arc in files:
        parts = set(Path(arc).parts)
        if parts & FORBIDDEN_NAMES or arc.endswith((".pyc", ".env")):
            raise SystemExit(f"refusing to package {arc}")
        hit = KEY_SHAPES.search(src.read_bytes())
        if hit:
            raise SystemExit(f"possible API key in {arc}: {hit.group(0)[:6]!r}…")


def build(out_dir: Path) -> Path:
    files = collect()
    check(files)
    name = f"fanoos-v{version()}-cpanel"
    out_dir.mkdir(parents=True, exist_ok=True)
    zip_path = out_dir / f"{name}.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for src, arc in files:
            info = zipfile.ZipInfo(f"{APP_DIR}/{arc}", date_time=FIXED_TIME)
            info.external_attr = 0o644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(info, src.read_bytes())
    digest = hashlib.sha256(zip_path.read_bytes()).hexdigest()
    (out_dir / f"{name}.zip.sha256").write_text(f"{digest}  {zip_path.name}\n", encoding="utf-8")
    shutil.copy(TEMPLATES / "DEPLOY_CPanel_FA.md", out_dir / "DEPLOY_CPanel_FA.md")
    print(f"{zip_path}  {len(files)} files  {zip_path.stat().st_size / 1024:.0f} KB  sha256 {digest}")
    return zip_path


if __name__ == "__main__":
    build(Path(sys.argv[1]) if len(sys.argv) > 1 else REPO / "dist")

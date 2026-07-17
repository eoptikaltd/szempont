"""Deploy-image guard (staging incident 2026-07-17): the app container crashed
at boot (gunicorn exit 3, module-level ImportError) because W2 packages were
imported by app.py but never COPYed into app/Dockerfile. These tests fail
whenever a local top-level package reachable from the app's imports is missing
from the Dockerfile COPY list."""
import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCKERFILE = ROOT / "app" / "Dockerfile"


def _local_packages() -> set[str]:
    return {p.name for p in ROOT.iterdir() if (p / "__init__.py").exists()}


def _copied_top_level(dockerfile_text: str) -> set[str]:
    copied = set()
    for m in re.finditer(r"^\s*COPY\s+(?:--\S+\s+)*(.+)$", dockerfile_text, re.M):
        for src in m.group(1).split()[:-1]:  # last token is the destination
            copied.add(src.rstrip("/").split("/")[0])
    return copied


def _imported_local_packages(start: str = "app") -> set[str]:
    """Transitive closure of local top-level packages imported from `start`,
    including lazy in-function imports (ast.walk sees them all)."""
    local = _local_packages()
    seen: set[str] = set()
    todo = {start}
    while todo:
        pkg = todo.pop()
        seen.add(pkg)
        for py in (ROOT / pkg).rglob("*.py"):
            tree = ast.parse(py.read_text(encoding="utf-8"), filename=str(py))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names = [a.name for a in node.names]
                elif isinstance(node, ast.ImportFrom) and not node.level and node.module:
                    names = [node.module]
                else:
                    continue
                for name in names:
                    top = name.split(".")[0]
                    if top in local and top not in seen:
                        todo.add(top)
    return seen


def test_app_dockerfile_copies_every_imported_package():
    needed = _imported_local_packages("app")
    missing = sorted(needed - _copied_top_level(DOCKERFILE.read_text()))
    assert not missing, (
        f"app/Dockerfile is missing COPY lines for local packages the app "
        f"imports: {missing}")


def test_app_dockerfile_installs_requirements():
    # python-barcode (print routes) and google-cloud-bigquery (SZEMPONT_CATALOG=bq,
    # the image's default mode) ride in via app/requirements.txt.
    text = DOCKERFILE.read_text()
    assert re.search(r"pip install[^\n]*app/requirements\.txt", text)
    reqs = (ROOT / "app" / "requirements.txt").read_text()
    assert "python-barcode" in reqs and "google-cloud-bigquery" in reqs


def test_ingest_dockerfile_copies_every_imported_package():
    needed = _imported_local_packages("ingest")
    text = (ROOT / "infra" / "Dockerfile.ingest").read_text()
    missing = sorted(needed - _copied_top_level(text))
    assert not missing, (
        f"infra/Dockerfile.ingest is missing COPY lines for local packages "
        f"the ingest job imports: {missing}")

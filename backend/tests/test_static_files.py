"""La interfaz compilada: la página se revalida en cada visita y los archivos con huella se guardan para siempre."""

from pathlib import Path

from app.api.main import static_file


def dist(tmp_path: Path) -> Path:
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text("<!doctype html>")
    (tmp_path / "assets" / "index-abc123.js").write_text("")
    (tmp_path / "favicon.svg").write_text("<svg/>")
    (tmp_path.parent / "secreto.txt").write_text("no")
    return tmp_path


def test_any_route_is_the_page_and_is_revalidated(tmp_path):
    root = dist(tmp_path)
    for path in ("", "resultados", "nba", "index.html", "../secreto.txt", "assets/no-existe.js"):
        r = static_file(root, path)
        assert Path(r.path).name == "index.html", path
        assert r.headers["cache-control"] == "no-cache", path


def test_fingerprinted_assets_are_cached_for_good(tmp_path):
    root = dist(tmp_path)
    r = static_file(root, "assets/index-abc123.js")
    assert Path(r.path).name == "index-abc123.js"
    assert r.headers["cache-control"] == "public, max-age=31536000, immutable"
    assert static_file(root, "favicon.svg").headers["cache-control"] == "no-cache"

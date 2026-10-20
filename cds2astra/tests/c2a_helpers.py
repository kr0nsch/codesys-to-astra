"""Общие помощники тестов cds2astra (отдельный модуль: conftest.py есть и в tools/tests)."""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path
from typing import Any

import pytest

REPO = Path(__file__).resolve().parents[2]
CORPUS = Path(__file__).resolve().parent / "corpus"
sys.path.insert(0, str(REPO / "tools"))

from cds2astra import api, resources  # noqa: E402
from cds2astra.session import Options, Session  # noqa: E402


def sample(name: str) -> Path:
    """Публичный образец из .cache (tools/fetch_samples.py); нет файла и сети — skip с понятным сообщением."""
    import fetch_samples

    p = fetch_samples.cached(name)
    if p is not None:
        return p
    try:
        return fetch_samples.fetch(name, timeout_s=20)
    except Exception as exc:  # pragma: no cover - зависит от сети
        pytest.skip(f"образец {name} недоступен (нет .cache и сети): {exc}")
        raise


def layout_files(root: Path) -> dict[str, str]:
    return {p.relative_to(root).as_posix(): p.read_text(encoding="utf-8") for p in sorted((root / "src").rglob("*.st"))}


def case_session(case_dir: Path) -> Session:
    meta: dict[str, Any] = tomllib.loads((case_dir / "case.toml").read_text(encoding="utf-8"))
    if (case_dir / "input.xml").is_file():
        data = (case_dir / "input.xml").read_bytes()
    else:
        data = api.layout_to_xml(layout_files(case_dir), case_dir.parent.name)
    p = api.load_project(data, f"{case_dir.parent.name}-{case_dir.name}.xml")
    spec_text = None
    if "spec" in meta:
        spec_text = "\n".join(
            f"{k} = {('true' if v else 'false') if isinstance(v, bool) else repr(v)}" for k, v in meta["spec"].items()
        )
    target_text = None
    if meta.get("profile_unknown"):
        text = resources.read_text("profiles", "astra-ide-1.7.2.2_dev-11.7.2.60.toml")
        for key in meta["profile_unknown"]:
            section, _, leaf = key.partition(".")
            head = f"[{section}.{leaf}]"
            start = text.index(head)
            end = text.index("\n[", start + 1)
            block = text[start:end]
            import re

            block = re.sub(r'status = "[a-z_]+"', 'status = "unknown"', block)
            text = text[:start] + block + text[end:]
        target_text = text
    s = api.make_session(p, api.DEFAULT_TARGET, target_text, spec_text, None, Options())
    return api.analyze(s)

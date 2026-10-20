#!/usr/bin/env python3
"""Файлы веб-демо в web/public/: пакет cds2astra.zip для Pyodide и предрасчитанные примеры.

Пакет — каталог cds2astra/ без тестов (ZIP без сжатия, фиксированные даты). Примеры — вход и результат CLI
(report, файлы, zip и его SHA-256): пока Pyodide грузится, демо показывает их.

    python tools/web_bundle.py
"""

from __future__ import annotations

import base64
import hashlib
import json
import shutil
import sys
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from cds2astra import api  # noqa: E402
from cds2astra.session import Options  # noqa: E402

PUBLIC = REPO / "web" / "public"


def package_zip(dest: Path) -> None:
    files = sorted(
        p
        for p in (REPO / "cds2astra").rglob("*")
        if p.is_file() and "tests" not in p.relative_to(REPO / "cds2astra").parts and "__pycache__" not in p.parts
    )
    with zipfile.ZipFile(dest, "w", compression=zipfile.ZIP_STORED) as zf:
        for p in files:
            info = zipfile.ZipInfo(p.relative_to(REPO).as_posix(), date_time=(1980, 1, 1, 0, 0, 0))
            info.external_attr = 0o644 << 16
            zf.writestr(info, p.read_bytes())


def example(eid: str, data: bytes, spec: str | None = None) -> None:
    d = PUBLIC / "examples" / eid
    d.mkdir(parents=True, exist_ok=True)
    (d / "input.xml").write_bytes(data)
    if spec:
        (d / "target.toml").write_text(spec, encoding="utf-8", newline="\n")
    res = api.run(data, f"{eid}.xml", spec_text=spec, options=Options(source_date="1970-01-01T00:00:00"))
    z = api.to_zip(res.files)
    payload = {
        "report": res.report,
        "files": {k: v.decode("utf-8", "replace") for k, v in res.files.items()},
        "zip": base64.b64encode(z).decode(),
        "zip_sha256": hashlib.sha256(z).hexdigest(),
    }
    (d / "result.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8", newline="\n")


def main() -> int:
    if PUBLIC.exists():
        shutil.rmtree(PUBLIC)
    PUBLIC.mkdir(parents=True)
    package_zip(PUBLIC / "cds2astra.zip")
    corpus = REPO / "corpus"
    example(
        "boiler",
        (corpus / "boiler-plc210" / "export.xml").read_bytes(),
        (corpus / "boiler-plc210" / "target.toml").read_text(encoding="utf-8"),
    )
    example("lang-matrix", (corpus / "lang-matrix" / "source.handmade.xml").read_bytes())
    example("sp18", (corpus / "sp18-speedtests" / "codesys_code_execution_speedTests.xml").read_bytes())
    s7 = {
        p.relative_to(corpus / "s7-chain").as_posix(): p.read_text(encoding="utf-8")
        for p in sorted((corpus / "s7-chain" / "src").rglob("*.st"))
    }
    example("s7-chain", api.layout_to_xml(s7, "s7-chain"))
    print(f"web/public: cds2astra.zip, примеры {len(list((PUBLIC / 'examples').iterdir()))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

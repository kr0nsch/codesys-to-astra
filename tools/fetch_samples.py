#!/usr/bin/env python3
"""Публичные образцы PLCopen XML и схема TC6 2.01 — в `.cache/` с проверкой SHA-256 (в git не кладутся).

Образцы закреплены по SHA коммита (PROMPT §7.3, docs/SOURCES.md):

| id | репозиторий @ коммит | лицензия -> использование |
|---|---|---|
| niksosov | niksosov/astraregul_stand @ 851ac49 | нет лицензии -> только скачивание |
| sp18 | tkucic/codesys_code_execution_speedTests @ d3abcf4 | MIT -> также копия в corpus/sp18-speedtests |
| srci | ThorstenBrach/SRCI @ 67fd773 | MIT -> также копия в corpus/srci |
| xsd | plcopen.org, архив «PLCopen XML version 2.01 xsd file» | условия не указаны -> только скачивание |

Фикстура ООП kns-port-domestic (`tools/plcopen/tests/fixtures/constructs` @ 6262d0f, MIT, тот же автор)
берётся из соседней рабочей копии только через `git archive <коммит>` (рабочую копию не читаем).

    python tools/fetch_samples.py [id ...]       # по умолчанию все
    python tools/fetch_samples.py --kns PATH     # фикстура constructs в .cache/kns-constructs/
Коды: 0 — всё на месте, 1 — сеть недоступна или SHA не совпал, 2 — аргументы.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import os
import subprocess
import sys
import tarfile
import urllib.request
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CACHE = REPO / ".cache"

SAMPLES: dict[str, dict[str, str | int]] = {
    "niksosov": {
        "url": "https://raw.githubusercontent.com/niksosov/astraregul_stand/"
        "851ac492bcb545e524d50eff8dfedea27f830efe/AstraRegul_stand.xml",
        "file": "niksosov/AstraRegul_stand.xml",
        "size": 525698,
        "sha256": "1c3d8d5731c9ff7faaa683d7cbe9aaeb6e5c6c3de28b074ac4be124866acf09d",
    },
    "sp18": {
        "url": "https://raw.githubusercontent.com/tkucic/codesys_code_execution_speedTests/"
        "d3abcf45935e6d46f526c186ab0ba5cc46f23cb2/codesys_code_execution_speedTests.xml",
        "file": "sp18/codesys_code_execution_speedTests.xml",
        "size": 262357,
        "sha256": "3d56646f8d34e0b1bfb77b8d343c72817c318d5c0975ba70784c612bc8d9f80a",
    },
    "srci": {
        "url": "https://raw.githubusercontent.com/ThorstenBrach/SRCI/"
        "67fd773b5692561a5d609bbe1e93d1945043e124/RobotLibrarySysDep_3S.xml",
        "file": "srci/RobotLibrarySysDep_3S.xml",
        "size": 28673,
        "sha256": "fe47b4f371a8efc74e98ac346a4b88f220f575379645bb288c5422d186168632",
    },
    "xsd": {
        "url": "https://www.plcopen.org/download_file/force/d397ab98-6a21-47d5-9fb1-37da9e94ef34/342/",
        "file": "xsd/tc6_xml_v201.xsd",
        "member": "tc6_xml_v201.xsd",
        "size": 85975,
        "sha256": "591b92ba65018a77c32ab9e606abf27bd810cb1f7761d972a85689531c51e20f",
    },
}
KNS_COMMIT = "6262d0fdc065ceb9d891c1ac3ab150010dc75ef1"
KNS_FIXTURE = "tools/plcopen/tests/fixtures/constructs"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def path_of(sample: str) -> Path:
    return CACHE / str(SAMPLES[sample]["file"])


def cached(sample: str) -> Path | None:
    """Путь к образцу в .cache, если он есть и SHA-256 совпадает; иначе None (тест — skip)."""
    p = path_of(sample)
    if p.is_file() and sha256(p.read_bytes()) == SAMPLES[sample]["sha256"]:
        return p
    return None


def fetch(sample: str, timeout_s: float = 60.0) -> Path:
    spec = SAMPLES[sample]
    have = cached(sample)
    if have is not None:
        return have
    req = urllib.request.Request(str(spec["url"]), headers={"User-Agent": "cds2astra-fetch/0.1"})
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        payload = resp.read()
    if "member" in spec:
        with zipfile.ZipFile(io.BytesIO(payload)) as zf:
            payload = zf.read(str(spec["member"]))
    got = sha256(payload)
    if got != spec["sha256"]:
        raise RuntimeError(f"{sample}: SHA-256 {got} не совпадает с {spec['sha256']}")
    dest = path_of(sample)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(payload)
    return dest


def fetch_kns(kns_repo: Path) -> Path:
    """Фикстура constructs kns-port-domestic @ 6262d0f через git archive (рабочая копия не читается)."""
    out = CACHE / "kns-constructs"
    data = subprocess.run(
        ["git", "-C", str(kns_repo), "archive", KNS_COMMIT, KNS_FIXTURE], check=True, capture_output=True
    ).stdout
    with tarfile.open(fileobj=io.BytesIO(data)) as tar:
        tar.extractall(out, filter="data")
    return out / KNS_FIXTURE


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Образцы PLCopen XML в .cache/ (SHA-256)")
    ap.add_argument("samples", nargs="*", help=f"какие ({', '.join(SAMPLES)}); по умолчанию все")
    ap.add_argument("--kns", help="рабочая копия kns-port-domestic (для фикстуры constructs @ 6262d0f)")
    args = ap.parse_args(argv)
    names = args.samples or list(SAMPLES)
    bad = [n for n in names if n not in SAMPLES]
    if bad:
        print(f"неизвестные образцы: {', '.join(bad)}", file=sys.stderr)
        return 2
    code = 0
    for name in names:
        try:
            p = fetch(name)
            print(f"{name}: {p.relative_to(REPO).as_posix()} ({p.stat().st_size} Б)")
        except (OSError, RuntimeError) as exc:
            print(f"{name}: не получен — {exc}", file=sys.stderr)
            code = 1
    if args.kns or os.environ.get("KNS_REPO"):
        p = fetch_kns(Path(args.kns or os.environ["KNS_REPO"]))
        print(f"kns constructs: {p.relative_to(REPO).as_posix()}")
    return code


if __name__ == "__main__":
    sys.exit(main())

"""Две IDE оракулов: Astra.IDE 1.7.2.2 (цель) и CODESYS 3.5.17.30 (тот же компилятор, coUnit, Control Win).

Здесь — пути, профили, устройства и раздельные учёт установок и блокировка репозитория библиотек:
у Astra.IDE свой репозиторий (`C:/ProgramData/Astra.IDE_64_1.7.2.2/Managed Libraries`), библиотеки
CODESYS в нём не видны, поэтому учёт установок `cds.py` и блокировка для неё — свои файлы
(так же собирал kns-port-domestic, его docs/BUILD_ERRORS.md, «Сборка без интерфейса»).

`environ_for(ide)` — переменные окружения для `cds.py` (сборка AstraCompat и заглушек в нужной IDE);
`run_ide_job` — запуск скрипта ScriptEngine с заданием JSON под блокировкой рабочей копии.
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from . import cli

TOOLS_CODESYS = Path(__file__).resolve().parent.parent
REPO_ROOT = TOOLS_CODESYS.parent.parent

_LOCAL = os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))

IDES: dict[str, dict[str, Any]] = {
    "astra": {
        "title": "Astra.IDE 1.7.2.2",
        "version": "1.7.2.2",
        "exe": os.environ.get(
            "ASTRA_IDE_EXE", r"C:\Program Files\AstraRegul\Astra.IDE_64_1.7.2.2\Astra.IDE\Common\Astra.IDE.exe"
        ),
        "profile": os.environ.get("ASTRA_IDE_PROFILE", "Astra.IDE_V1.7.2.2"),
        # REGUL R500 61: описание устройства 11.7.2.60 из C:/ProgramData/Astra.IDE_64_1.7.2.2/Devices/4096/
        "device": {"name": "Device", "type": 4096, "id": "109B 0008", "version": "11.7.2.60", "title": "REGUL R500 61"},
        "library_lock": os.path.join(_LOCAL, "plc-tools", "astra-library-repo.lock"),
        "library_registry": os.path.join(_LOCAL, "plc-tools", "astra-libraries.json"),
    },
    "codesys": {
        "title": "CODESYS 3.5.17.30",
        "version": "3.5.17.30",
        "exe": os.environ.get(
            "CODESYS_317_EXE", r"C:\Program Files (x86)\CODESYS 3.5.17.30\CODESYS\Common\CODESYS.exe"
        ),
        "profile": os.environ.get("CODESYS_317_PROFILE", "CODESYS V3.5 SP17 Patch 3"),
        "device": {
            "name": "Device",
            "type": 4096,
            "id": "0000 0001",
            "version": "3.5.17.30",
            "title": "CODESYS Control Win V3",
        },
        "library_lock": os.path.join(_LOCAL, "plc-tools", "codesys-library-repo.lock"),
        "library_registry": os.path.join(_LOCAL, "plc-tools", "codesys-libraries.json"),
    },
}


def ide(name: str) -> dict[str, Any]:
    if name not in IDES:
        raise SystemExit(f"неизвестная IDE {name!r}: astra | codesys")
    return IDES[name]


def available(name: str) -> bool:
    return Path(ide(name)["exe"]).is_file()


def environ_for(name: str, base: Mapping[str, str] | None = None) -> dict[str, str]:
    """Окружение для cds.py: exe, профиль, устройство, учёт и блокировка репозитория библиотек IDE."""
    spec = ide(name)
    env = dict(os.environ if base is None else base)
    env.update(
        {
            "CODESYS_EXE": spec["exe"],
            "CODESYS_PROFILE": spec["profile"],
            "CDS_DEVICE_TYPE": str(spec["device"]["type"]),
            "CDS_DEVICE_ID": spec["device"]["id"],
            "CDS_DEVICE_VERSION": spec["device"]["version"],
            "CDS_LIBRARY_LOCK": spec["library_lock"],
            "CDS_LIBRARY_REGISTRY": spec["library_registry"],
        }
    )
    return env


def run_ide_job(
    name: str, script: Path, job: dict[str, Any], work: Path, label: str, timeout_s: float = 1800.0
) -> dict[str, Any]:
    """Запустить скрипт ScriptEngine в IDE name с заданием job; результат — JSON скрипта."""
    spec = ide(name)
    work.mkdir(parents=True, exist_ok=True)
    job = dict(job)
    job.setdefault("tools_codesys", str(TOOLS_CODESYS))
    job["result"] = str(work / f"{label}-result.json")
    job.setdefault("log", str(work / f"{label}.log"))
    job_path = work / f"{label}-job.json"
    job_path.write_text(json.dumps(job, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    result_path = Path(job["result"])
    if result_path.exists():
        result_path.unlink()
    cmd = cli.build_cmdline(spec["exe"], spec["profile"], script)
    env = dict(os.environ)
    env["CDS_JOB"] = str(job_path)
    lock = cli.FileLock(REPO_ROOT / "build" / "codesys" / f"oracle-{name}.lock", timeout_s, purpose=f"oracle {label}")
    started = time.time()
    with lock:
        proc = subprocess.run(cmd, env=env, capture_output=True, timeout=timeout_s, check=False)
    (work / f"{label}.stdout.log").write_bytes(proc.stdout + proc.stderr)
    if not result_path.exists():
        raise RuntimeError(f"{spec['title']}: код {proc.returncode}, нет файла результата {result_path}")
    data: dict[str, Any] = json.loads(result_path.read_text(encoding="utf-8"))
    data["elapsed_s"] = round(time.time() - started, 1)
    data["ide"] = name
    data["ide_title"] = spec["title"]
    return data


def library_spec(title: str, company: str, version: str = "*", namespace: str | None = None) -> dict[str, Any]:
    """Описание библиотеки в формате cds.py (resolve_libraries) по названию и компании."""
    spec: dict[str, Any] = {"label": f"{title} ({company})", "title": title, "company": company, "version": version,
                            "qualified_only": False}
    if namespace:
        spec["namespace"] = namespace
    return spec


def standard_spec() -> dict[str, Any]:
    return {
        "label": "Standard (#Standard)",
        "title": "Standard",
        "company": "System",
        "version": "*",
        "placeholder": "Standard",
        "namespace": "Standard",
        "qualified_only": False,
    }


def placeholder_spec(title: str, namespace: str | None = None) -> dict[str, Any]:
    return {
        "label": f"{title} (#{title})",
        "title": title,
        "company": "System",
        "version": "*",
        "placeholder": title,
        "namespace": namespace or title,
        "qualified_only": False,
    }

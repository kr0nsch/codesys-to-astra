#!/usr/bin/env python3
"""Все картинки README — воспроизводимо, фирменным медиа-китом портфолио (`_shared/media-kit`).

    python tools/media/make_media.py banner            # баннеры и social preview
    python tools/media/make_media.py chart             # минуты модели по правилам (котельная)
    python tools/media/make_media.py report            # скриншоты MIGRATION_REPORT.html в двух темах
    python tools/media/make_media.py demo              # скриншоты и GIF веб-демо (нужен web/dist)
    python tools/media/make_media.py term [--capture]  # GIF терминала из docs/media/sessions/*.json
    python tools/media/make_media.py all

`term --capture` снимает новую сессию: реальные cds2astra inventory / migrate и оракул Astra.IDE 1.7.2.2
(нужна локальная Astra.IDE). Без `--capture` GIF рисуется из уже снятой сессии.
"""

from __future__ import annotations

import argparse
import functools
import importlib
import json
import os
import subprocess
import sys
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
# кит портфолио лежит рядом с репозиторием (…/asu_TP/domestic-plc-gaps/_shared/media-kit) или по MEDIA_KIT
KIT = Path(os.environ.get("MEDIA_KIT", str(REPO.parent / "asu_TP" / "domestic-plc-gaps" / "_shared" / "media-kit")))
MEDIA = REPO / "docs" / "media"
SESSION = MEDIA / "sessions" / "demo-migrate.json"
REPO_ID = "codesys-to-astra"
BOILER = REPO / "corpus" / "boiler-plc210"
SCROLL_TABS = "window.scrollTo(0, document.querySelector('nav.tabs').getBoundingClientRect().top + scrollY - 12)"

sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tools"))


def kit(name: str) -> Any:
    if str(KIT) not in sys.path:
        sys.path.insert(0, str(KIT))
    return importlib.import_module(name)


def banner() -> None:
    spec = KIT / "repos-migration.json"
    cmd = [sys.executable, str(KIT / "banner.py"), "render", "--spec", str(spec), "--repo", REPO_ID]
    subprocess.run([*cmd, "--repo-layout", "--out", str(MEDIA)], check=True)


def _boiler_report(out: Path) -> dict[str, Any]:
    from cds2astra import api
    from cds2astra.session import Options

    res = api.run(
        (BOILER / "export.xml").read_bytes(),
        "export.xml",
        spec_text=(BOILER / "target.toml").read_text(encoding="utf-8"),
        options=Options(source_date="1970-01-01T00:00:00"),
    )
    out.mkdir(parents=True, exist_ok=True)
    for name, data in res.files.items():
        (out / name).write_bytes(data)
    report: dict[str, Any] = res.report
    return report


def chart() -> None:
    from cds2astra.rules.registry import RULES

    charts = kit("charts")
    report = _boiler_report(REPO / "out" / "media" / "boiler")
    items = sorted(((v, k) for k, v in report["effort_by_rule_minutes"].items() if v > 0), reverse=True)
    labels = [f"{k}  {RULES[k].title[:52]}" for _v, k in items]
    values = [v for v, _k in items]
    eff = report["effort"]

    def build(c: dict[str, Any]) -> Any:
        fig, axes = charts.figure(1, size=(10, 0.5 * len(values) + 1.6))
        ax = axes[0] if isinstance(axes, list | tuple) else axes
        charts.bars(ax, labels, values, c, highlight=0, unit="мин")
        charts.header(
            fig,
            "Котельная на ПЛК210: где уходит время переноса",
            f"модель: сумма mode по находкам, мин; итог P50 {eff['p50_h']} ч / P90 {eff['p90_h']} ч"
            " (Монте-Карло); слой ОВЕН — синтетика",
            c,
        )
        return fig

    for p in charts.save_themes(build, MEDIA / "chart-effort-by-rule"):
        print(f"[media] {p.relative_to(REPO)}")


def report_shots() -> None:
    shot = kit("shot")
    html = REPO / "out" / "media" / "boiler" / "MIGRATION_REPORT.html"
    _boiler_report(html.parent)
    with shot.Browser() as br:
        for scheme in ("dark", "light"):
            out = MEDIA / f"shot-report-{scheme}.png"
            br.page_to_png(html, out, 1000, 760, 1.4, scheme=scheme, wait_ms=200)
            print(f"[media] {out.relative_to(REPO)}")


def demo() -> None:
    """Скриншоты вкладок в двух темах и GIF ~13 с (тёмная тема) с настоящего веб-демо (web/dist)."""
    import e2e_smoke
    from playwright.sync_api import sync_playwright

    shot = kit("shot")
    if not (e2e_smoke.DIST / "index.html").is_file():
        raise SystemExit("нет web/dist: python tools/web_bundle.py && cd web && npm ci && npm run build")
    srv = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(e2e_smoke.Handler, directory=str(e2e_smoke.DIST)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{srv.server_address[1]}{e2e_smoke.BASE}"
    frames: list[Any] = []
    durations: list[int] = []
    tmp = REPO / "out" / "media" / "frames"
    tmp.mkdir(parents=True, exist_ok=True)
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            for scheme in ("dark", "light"):
                page = browser.new_page(viewport={"width": 1200, "height": 800}, color_scheme=scheme)
                page.goto(url)
                page.wait_for_selector("#status[data-kind='ok']", timeout=180_000)
                page.wait_for_function(
                    "document.querySelector('#tab-summary').innerText.includes('Посчитано в браузере')", timeout=120_000
                )

                def snap(name: str, ms: int, page: Any = page, scheme: str = scheme) -> Path:
                    p = tmp / f"{scheme}-{len(frames):02d}-{name}.png"
                    page.screenshot(path=str(p))
                    if scheme == "dark":
                        frames.append(p)
                        durations.append(ms)
                    return p

                snap("start", 2200)
                for tab, ms in (("summary", 2600), ("langs", 2000), ("io", 2800), ("code", 2800), ("zip", 2000)):
                    page.click(f"nav.tabs button[data-tab='{tab}']")
                    if tab != "summary":  # вкладки с длинным содержимым — от строки вкладок
                        page.evaluate(SCROLL_TABS)
                    page.wait_for_timeout(250)
                    p = snap(tab, ms)
                    if tab in ("summary", "io", "libs", "code"):
                        dest = MEDIA / f"shot-demo-{tab}-{scheme}.png"
                        dest.write_bytes(p.read_bytes())
                        print(f"[media] {dest.relative_to(REPO)}")
                page.click("nav.tabs button[data-tab='libs']")
                page.evaluate(SCROLL_TABS)
                page.wait_for_timeout(250)
                page.screenshot(path=str(MEDIA / f"shot-demo-libs-{scheme}.png"))
                print(f"[media] docs/media/shot-demo-libs-{scheme}.png")
                page.close()
            browser.close()
    finally:
        srv.shutdown()
    gif = MEDIA / "demo-web.gif"
    shot.frames_to_gif([frames[-1], *frames], gif, [600, *durations], colors=192)
    print(f"[media] {gif.relative_to(REPO)} ({gif.stat().st_size // 1024} КБ, кадров {len(frames) + 1})")


def term(capture: bool) -> None:
    t2g = kit("term2gif")
    if capture:
        cmds = [
            "python -m cds2astra inventory corpus/boiler-plc210/export.xml",
            "python -m cds2astra migrate corpus/boiler-plc210/export.xml"
            " --target-spec corpus/boiler-plc210/target.toml --out out/boiler --fail-on never",
            "python tools/codesys/xml_oracle.py out/boiler/astra-import.xml --ide astra --target app",
        ]
        SESSION.parent.mkdir(parents=True, exist_ok=True)
        # PowerShell 5.1 не входит в каталог с «[12]» в пути (шаблон подстановки) — сессия снимается в cmd
        prompt = "\x1b[94mcodesys-to-astra\x1b[0m> "
        t2g.capture(cmds, SESSION, shell="cmd", cwd=str(REPO), title="Командная строка", prompt=prompt, cols=104)
        # в файле сессии — только имя проекта, без пути рабочего места
        data = json.loads(SESSION.read_text(encoding="utf-8"))
        data.setdefault("meta", {})["cwd"] = REPO_ID
        SESSION.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        print(f"[media] {SESSION.relative_to(REPO)}")
    session = json.loads(SESSION.read_text(encoding="utf-8"))
    out = MEDIA / "demo-migrate.gif"
    t2g.render(session, out, speed=1.2)
    print(f"[media] {out.relative_to(REPO)} ({out.stat().st_size // 1024} КБ)")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="медиа README кит-ом портфолио")
    ap.add_argument("what", choices=["banner", "chart", "report", "demo", "term", "all"])
    ap.add_argument("--capture", action="store_true", help="term: снять новую сессию (нужна Astra.IDE)")
    args = ap.parse_args(argv)
    MEDIA.mkdir(parents=True, exist_ok=True)
    steps = ["banner", "chart", "report", "demo", "term"] if args.what == "all" else [args.what]
    for step in steps:
        if step == "banner":
            banner()
        elif step == "chart":
            chart()
        elif step == "report":
            report_shots()
        elif step == "demo":
            demo()
        else:
            term(args.capture)
    return 0


if __name__ == "__main__":
    sys.exit(main())

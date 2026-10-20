#!/usr/bin/env python3
"""E2E веб-демо: web/dist под ThreadingHTTPServer (порт 0) -> Playwright (Chromium) -> пример «Котельная».

Проверяется: страница грузится без запросов к чужим доменам; Pyodide запускается и считает отчёт в браузере;
итоги совпадают с CLI; SHA-256 zip из Pyodide равен SHA-256 zip из CPython (воспроизводимость, 00-INDEX §4.10).
Скриншоты для README — `--shots DIR` (светлая и тёмная тема).

    python tools/e2e_smoke.py [--shots docs/media] [--headed]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

REPO = Path(__file__).resolve().parents[1]
DIST = REPO / "web" / "dist"
BASE = "/codesys-to-astra/"
sys.path.insert(0, str(REPO))


class Handler(SimpleHTTPRequestHandler):
    def translate_path(self, path: str) -> str:
        p = urlparse(path).path
        if p.startswith(BASE):
            p = "/" + p[len(BASE) :]
        return str(DIST / p.lstrip("/")) if p != "/" else str(DIST / "index.html")

    def log_message(self, *args: object) -> None:  # тихо
        pass

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


Handler.extensions_map.update({".mjs": "text/javascript", ".wasm": "application/wasm", ".js": "text/javascript"})


def _foreign(url: str) -> bool:
    return "127.0.0.1" not in url and not url.startswith(("data:", "blob:"))


def cpython_zip_sha() -> str:
    from cds2astra import api
    from cds2astra.session import Options

    case = REPO / "corpus" / "boiler-plc210"
    res = api.run(
        (case / "export.xml").read_bytes(),
        "boiler.xml",
        spec_text=(case / "target.toml").read_text(encoding="utf-8"),
        options=Options(source_date="1970-01-01T00:00:00"),
    )
    return hashlib.sha256(api.to_zip(res.files)).hexdigest()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="e2e веб-демо")
    ap.add_argument("--shots", help="каталог для скриншотов (shot-demo-*-{light,dark}.png)")
    ap.add_argument("--headed", action="store_true")
    args = ap.parse_args(argv)
    if not (DIST / "index.html").is_file():
        print("нет web/dist: cd web && npm ci && npm run build", file=sys.stderr)
        return 2
    from playwright.sync_api import sync_playwright

    srv = ThreadingHTTPServer(("127.0.0.1", 0), partial(Handler, directory=str(DIST)))
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{port}{BASE}"
    foreign: list[str] = []
    ok = True
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=not args.headed)
            for scheme in ("light", "dark"):
                page = browser.new_page(viewport={"width": 1280, "height": 900}, color_scheme=scheme)
                page.on("request", lambda r: foreign.append(r.url) if _foreign(r.url) else None)
                page.goto(url)
                page.wait_for_selector("#status[data-kind='ok']", timeout=180_000)
                page.wait_for_function(
                    "document.querySelector('#tab-summary').innerText.includes('Посчитано в браузере')", timeout=120_000
                )
                summary = page.inner_text("#tab-summary")
                page.click("nav.tabs button[data-tab='zip']")
                sha = page.inner_text("#tab-zip").split("SHA-256:")[1].split()[0]
                want = cpython_zip_sha()
                same = sha == want
                print(
                    f"[e2e] {scheme}: Pyodide готов; zip SHA-256 Pyodide {sha[:16]}… / CPython {want[:16]}… — "
                    + ("совпадает" if same else "РАЗНЫЙ")
                )
                ok = ok and same and "вручную" in summary
                if args.shots:
                    out = Path(args.shots)
                    out.mkdir(parents=True, exist_ok=True)
                    for tab in ("summary", "io", "libs", "code"):
                        page.click(f"nav.tabs button[data-tab='{tab}']")
                        page.wait_for_timeout(300)
                        page.screenshot(path=str(out / f"shot-demo-{tab}-{scheme}.png"), full_page=False)
                page.close()
            browser.close()
    finally:
        srv.shutdown()
    if foreign:
        print(f"[e2e] запросы к чужим доменам: {sorted(set(foreign))[:5]}", file=sys.stderr)
        ok = False
    print(json.dumps({"ok": ok, "foreign_requests": len(foreign)}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

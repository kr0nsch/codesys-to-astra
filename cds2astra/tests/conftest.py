"""Фикстуры тестов cds2astra; помощники — c2a_helpers.py."""

from __future__ import annotations

import pytest
from c2a_helpers import REPO

from cds2astra import api
from cds2astra.session import Session


@pytest.fixture
def boiler_session() -> Session:
    case = REPO / "corpus" / "boiler-plc210"
    p = api.load_project((case / "export.xml").read_bytes(), "export.xml")
    return api.analyze(api.make_session(p, spec_text=(case / "target.toml").read_text(encoding="utf-8")))

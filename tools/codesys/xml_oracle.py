# -*- coding: utf-8 -*-
"""xml_oracle.py — оракул импорта и сборки astra-import.xml в Astra.IDE 1.7.2.2 или CODESYS 3.5.17.30.

    python tools/codesys/xml_oracle.py --ide astra|codesys [--target app pool] [--case NAME] out/boiler/astra-import.xml
Рядом с XML должен лежать MIGRATION_REPORT.json (объекты, задачи, библиотеки, находки todo).
Итоги — build/oracle/<case>-<ide>-pous-<target>.json. Коды: 0 — импорт полный и ошибок вне todo нет,
1 — есть расхождения, 2 — аргументы, 3 — IDE нет или скрипт IDE упал.
Запускатель на общем подмножестве Python 2.7 и 3 (как cds.py); реализация — cdshost/oracle.py.
"""
from __future__ import absolute_import, print_function, unicode_literals

import os
import sys

if sys.version_info < (3, 11):
    sys.stderr.write('xml_oracle.py: нужен Python 3.11+\n')
    sys.exit(2)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cdshost.oracle_cli import main

if __name__ == '__main__':
    sys.exit(main())

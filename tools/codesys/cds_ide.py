# -*- coding: utf-8 -*-
"""cds_ide.py — cds.py в выбранной IDE: `python tools/codesys/cds_ide.py astra|codesys <команда cds.py> ...`

Переменные окружения IDE (exe, профиль, устройство, учёт и блокировка репозитория библиотек) —
tools/codesys/cdshost/ide_env.py. Пример: сборка AstraCompat в Astra.IDE 1.7.2.2 на REGUL R500 61:
    python tools/codesys/cds_ide.py astra check
    python tools/codesys/cds_ide.py astra library --compiled --install
Запускатель на общем подмножестве Python 2.7 и 3 (как cds.py); реализация — Python 3.11+.
"""
from __future__ import absolute_import, print_function, unicode_literals

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def main():
    if len(sys.argv) < 3 or sys.argv[1] not in ('astra', 'codesys'):
        sys.stderr.write('usage: cds_ide.py astra|codesys <команда cds.py> ...\n')
        return 2
    from cdshost import ide_env
    env = ide_env.environ_for(sys.argv[1])
    cmd = [sys.executable, os.path.join(HERE, 'cds.py')] + sys.argv[2:]
    return subprocess.call(cmd, env=env)


if __name__ == '__main__':
    sys.exit(main())

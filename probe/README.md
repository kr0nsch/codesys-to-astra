# Пробник

Минимальные файлы на каждую конструкцию, поведение которой при импорте в Astra.IDE 1.7.2.2 и CODESYS
3.5.17.30 надо было проверить до кода (пробы A0). Итоги и выводы — `docs/PROBES.md`, строки —
`RESULTS.csv` (столбцы семейства: `probe_id,construct,file,expected,observed,ide,ide_version,date,notes`;
`observed` — `ok`, `error:<текст дословно>`, `value:<значение>`, `place:<путь в дереве>` или `not-run`).

| Файл | Проба | Что внутри | Минут на прогон |
|---|---|---|---|
| `p2_resource_form.xml` | P2, P6 | POU в форме `resource` с configuration `CfgOther` и resource `ResOther`, задачи `T_Fast` (3) и `T_Slow` (20) | < 1 |
| `p3_libraries.xml` | P3 | POU и `addData` со ссылками на библиотеки | < 1 |
| `p4_il.xml` | P4 | программа на IL (`<IL><xhtml>`) | < 1 |
| `corpus/lang-matrix/source.handmade.xml` | P5 | шесть языков (рукописный TC6) | < 1 |
| `build/probes/p8_constructs.xml` | P8 | фикстура ООП kns @ `6262d0f`, собирается `tools/probes.py` из кэша | < 1 |

Порядок: `python tools/probes.py --ide astra codesys --lang-matrix` (оба IDE, ~1 мин). Пробы владельца —
`cds2astra probe --out <каталог>`: `layout-probe.xml` (раскладка `SIZEOF(POINTER)` и порядок слов), инструкции
E5, E7, E8 и пустой `RESULTS.csv` для его строк.

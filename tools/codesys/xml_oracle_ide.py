# -*- coding: utf-8 -*-
"""Оракул импорта PLCopen XML в Astra.IDE 1.7.2.2 / CODESYS 3.5.17.30 (ScriptEngine, IronPython 2.7).

Запускается только из tools/codesys/xml_oracle.py:
    "<Astra.IDE.exe|CODESYS.exe>" --profile="<профиль>" --noUI --runscript="tools/codesys/xml_oracle_ide.py"
Задание — JSON (путь в переменной CDS_JOB):

    {
      "tools_codesys": "<repo>/tools/codesys",
      "repository": "System",
      "libraries": [описания библиотек cds.py],       ссылки Library Manager (Standard, AstraCompat, заглушки)
      "introspect": false,                            записать dir() объектов ScriptEngine (пробы P3/P4)
      "result": "<путь>.json", "log": "<путь>.log",
      "cases": [{"name", "xml", "target": "app" | "pool", "device": {"name","type","id","version"} | null,
                 "project", "tasks": [{"name","interval_ms","priority","pous"}] | null,
                 "export": "<путь>.xml" | null, "build": true, "keep_project": false,
                 "libraries": [индексы в libraries] | null}]
    }

Цели: app — проект с устройством, импорт в приложение (`app.import_xml`), задачи (если заданы),
полная сборка `app.rebuild()`; pool — проект без устройства, импорт в пул POU (`proj.import_xml`),
«Проверить все объекты пула». Итог по случаю: сообщения импорта (ImportReporter), дерево объектов,
задачи после импорта, ссылки на библиотеки, сообщения компилятора, обратный экспорт.

Образец — tools/plcopen/cds_import_check.py проекта kr0nsch/kns-port-domestic @ 6262d0f (MIT, тот же
автор). Синтаксис — общее подмножество Python 2.7 и 3.x.
"""

from __future__ import absolute_import, print_function, unicode_literals

import io
import json
import os
import sys
import time
import traceback

JOB_ENV = 'CDS_JOB'
DUMP_KINDS = ('folder', 'pou', 'dut', 'gvl', 'pvl', 'itf', 'method', 'property', 'accessor', 'action')
TEXT_KINDS = ('pou', 'dut', 'gvl', 'pvl', 'itf', 'method', 'property', 'accessor', 'action')


def load_job():
    path = os.environ.get(JOB_ENV)
    if not path or not os.path.isfile(path):
        raise RuntimeError('нет файла задания (переменная %s): запускайте через xml_oracle.py' % JOB_ENV)
    with io.open(path, encoding='utf-8') as handle:
        return json.loads(handle.read())


JOB = load_job()
sys.path.insert(0, JOB['tools_codesys'])

import build as B  # noqa: E402
import import_sources as I  # noqa: E402
import make_library as ML  # noqa: E402

import cds_common as C  # noqa: E402

SE = C.api()


class Reporter(SE.ImportReporter):
    """Сообщения импорта PLCopen XML; конфликт имён — копия (в пустом проекте их быть не должно)."""

    def __init__(self):
        self.messages = []

    def error(self, message):
        self.messages.append({'level': 'error', 'text': C._text(message)})

    def warning(self, message):
        self.messages.append({'level': 'warning', 'text': C._text(message)})

    def resolve_conflict(self, obj):
        self.messages.append({'level': 'conflict', 'text': C.obj_name(obj)})
        return SE.ConflictResolve.Copy

    def added(self, obj):
        self.messages.append({'level': 'added', 'text': C.obj_name(obj)})

    def replaced(self, obj):
        self.messages.append({'level': 'replaced', 'text': C.obj_name(obj)})

    def skipped(self, objectname):
        self.messages.append({'level': 'skipped', 'text': C._text(objectname)})

    @property
    def aborting(self):
        return False


def kind_name(obj):
    kind = C.kind_of(obj)
    if kind:
        return kind
    try:
        if obj.is_task:
            return 'task'
    except Exception:
        pass
    try:
        if obj.is_device:
            return 'device'
    except Exception:
        pass
    return 'other'


def dump_tree(container, path, out, depth=0):
    """Все объекты под container: путь, вид, тексты объявления и тела (у объектов с текстом)."""
    if depth > 12:
        return
    for obj in C.children(container):
        kind = kind_name(obj)
        name = C.obj_name(obj)
        item = {'path': path + [name], 'kind': kind}
        if kind in TEXT_KINDS:
            item['decl'] = C.decl_text(obj)
            item['impl'] = C.impl_text(obj)
        try:
            item['guid'] = C._text(obj.type)
        except Exception:
            pass
        out.append(item)
        dump_tree(obj, path + [name], out, depth + 1)


def dump_tasks(app):
    """Задачи приложения после импорта: имя, приоритет, интервал, тип, POU."""
    tasks = []
    try:
        configs = [o for o in C.children(app) if getattr(o, 'is_task_configuration', False)]
    except Exception:
        configs = []
    for cfg in configs:
        for task in C.children(cfg):
            if not getattr(task, 'is_task', False):
                continue
            item = {'name': C.obj_name(task)}
            for attr in ('priority', 'interval', 'interval_unit', 'kind_of_task'):
                try:
                    item[attr] = C._text(getattr(task, attr))
                except Exception:
                    pass
            try:
                item['pous'] = I._task_pou_names(task)
            except Exception:
                item['pous'] = []
            tasks.append(item)
    return tasks


def introspect():
    """dir() объектов ScriptEngine: ищем API опций IDE (проба P4) и экспорта символов (P3)."""
    found = {}
    for label, obj in (('system', getattr(SE, 'system', None)), ('projects', getattr(SE, 'projects', None))):
        if obj is None:
            continue
        try:
            found[label] = [n for n in dir(obj) if not n.startswith('_')]
        except Exception as exc:
            found[label] = 'error: %s' % exc
    try:
        found['scriptengine'] = [n for n in dir(SE) if not n.startswith('_')]
    except Exception:
        pass
    return found


def remove_quietly(path):
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass


def project_side_files(project):
    folder = os.path.dirname(project)
    stem = os.path.splitext(os.path.basename(project))[0]
    found = []
    if os.path.isdir(folder):
        for name in os.listdir(folder):
            if name.startswith(stem) and (name.endswith('.opt') or name.endswith('.precompilecache')):
                found.append(os.path.join(folder, name))
    return found


def run_case(case, resolved_all, log):
    result = {'name': case['name'], 'target': case['target'], 'xml': case['xml'], 'ok': False}
    project = case['project']
    C.ensure_dir(os.path.dirname(project))
    remove_quietly(project)
    for side in project_side_files(project):
        remove_quietly(side)
    started = time.time()
    proj = None
    try:
        proj = SE.projects.create(project, True)
        report = I.Report(log)
        if case['target'] == 'app':
            dev = case['device']
            proj.add(dev['name'], SE.DeviceID(int(dev['type']), dev['id'], dev['version']))
            target = C.application(proj)
            libman = I.find_library_manager(target)
        else:
            target = proj
            libman = proj.get_library_manager()
        resolved = resolved_all
        I.sync_libraries(libman, resolved, [], log, report)
        result['libraries_before'] = [C.ref_record(ref)['name'] for ref in libman.references]
        reporter = Reporter()
        try:
            target.import_xml(reporter, case['xml'], True)
        except Exception as exc:
            result['import_exception'] = C._text(exc)
        result['import_messages'] = reporter.messages
        try:
            result['libraries_after'] = [C.ref_record(ref)['name'] for ref in libman.references]
        except Exception as exc:
            result['libraries_after_error'] = C._text(exc)
        objects = []
        dump_tree(target, [], objects)
        result['objects'] = objects
        if case['target'] == 'app':
            result['tasks_after_import'] = dump_tasks(target)
        B.clear_messages()
        if case['target'] == 'app':
            if case.get('tasks'):
                I.sync_tasks(target, case['tasks'], log, report)
                result['tasks_after_sync'] = dump_tasks(target)
            if case.get('build', True):
                target.rebuild()
                result['messages'] = B.collect_messages()
            else:
                result['messages'] = []
        else:
            result['messages'] = ML.check_pool(proj, log)['messages'] if case.get('build', True) else []
        result['summary'] = B.summarize(result['messages'])
        if case.get('export'):
            try:
                C.ensure_dir(os.path.dirname(case['export']))
                remove_quietly(case['export'])
                if case['target'] == 'app':
                    what = [target]
                else:
                    # объект проекта экспортировать нельзя (IScriptProject) — экспортируются объекты пула
                    what = [o for o in C.children(proj) if C.kind_of(o) in DUMP_KINDS]
                proj.export_xml(what, path=case['export'], recursive=True, export_folder_structure=True,
                                declarations_as_plaintext=True)
                result['export'] = case['export']
            except Exception as exc:
                result['export_error'] = C._text(exc)
        if case.get('keep_project'):
            proj.save()
            result['project'] = project
        result['ok'] = True
    except Exception:
        result['error'] = traceback.format_exc()
    finally:
        if proj is not None:
            try:
                proj.close()
            except Exception:
                pass
        if not case.get('keep_project'):
            remove_quietly(project)
            for side in project_side_files(project):
                remove_quietly(side)
    result['seconds'] = round(time.time() - started, 1)
    return result


def main():
    result = {'cases': [], 'python': sys.version, 'started': time.strftime('%Y-%m-%dT%H:%M:%S')}
    code = 0
    log = C.Log(JOB.get('log'))
    try:
        try:
            result['ide_version'] = C._text(SE.system.build_info) if hasattr(SE.system, 'build_info') else None
        except Exception:
            pass
        if JOB.get('introspect'):
            result['introspect'] = introspect()
        resolved = []
        missing = []
        for spec in JOB.get('libraries') or []:
            try:
                resolved.extend(I.resolve_libraries([spec], JOB.get('repository') or 'System', log))
            except Exception as exc:
                missing.append({'library': spec.get('label') or spec.get('title'), 'error': C._text(exc)})
        result['libraries_missing'] = missing
        for case in JOB['cases']:
            log.info('случай %s (%s): %s' % (case['name'], case['target'], case['xml']))
            result['cases'].append(run_case(case, resolved, log))
    except Exception:
        result['error'] = traceback.format_exc()
        code = 3
    finally:
        log.close()
    C.write_json(JOB['result'], result)
    sys.exit(code)


main()

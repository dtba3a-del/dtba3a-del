#!/usr/bin/env python3
"""chatman — стенограммы, поиск и канон. Один инструмент на все проекты.

НАЗНАЧЕНИЕ
    Контекст чата сжимается по мере роста, и подробности обсуждения потом
    не найти, хотя решения принимаются именно там. chatman выгружает
    стенограмму в репозиторий ДОСЛОВНО, ищет по ней и по корпусу файлов, и
    держит перед глазами канон работы. Ставится один раз, работает в любом
    проекте и в любом чате.

УСТАНОВКА (однократно)
    python3 chatman.py install
        кладёт себя в ~/.claude/tools/chatman.py, делает пусковой файл
        ~/.local/bin/chatman и навык ~/.claude/skills/chatman/SKILL.md,
        чтобы инструмент был виден в каждом чате.

В НОВОМ ПРОЕКТЕ (однократно)
    cd <корень проекта> && chatman init
        заводит .chatman/rules.md (канон этого проекта) и .chatman/config.json,
        печатает, что дописать в .gitignore.

ПОРЯДОК ПРИМЕНЕНИЯ
    chatman repos                           какие репозитории есть в профиле
    chatman find --prompts --grep '...'     найти распоряжение
    chatman find --context 77 --around 3    что было вокруг него
    chatman find --repo Oscill --prompts    заглянуть в другой свой проект
    chatman search Ричардсон --fuzzy 1      поиск по корпусу с замером
    chatman rules                           канон: общий + проектный
    chatman doctor                          самопроверка установки
    chatman export                          ВЫГРУЗИТЬ в репозиторий (см. ниже)

===========================================================================
ГДЕ ЖИВЁТ СТЕНОГРАММА: В ПРОФИЛЕ, А НЕ В РЕПОЗИТОРИИ
===========================================================================

Общего каталога логов НЕТ и он не нужен: записи уже лежат в профиле
(`~/.claude/projects/`) — в приватной зоне. Инструмент читает их ТАМ, на
месте, ничего никуда не копируя. Поэтому:

  * `find`, `search`, `repos` выгрузки НЕ ТРЕБУЮТ;
  * контексты всех ваших репозиториев доступны сразу (`repos`, `--repo`);
  * в публичный репозиторий не попадает ничего.

`export` остаётся, но это ОСОЗНАННОЕ действие: он публикует дословную
запись — со всем, что было в выводе команд, — в тот репозиторий, где
запущен. Осмысленно для приватного репозитория; для публичного сперва
подумайте, что именно вы публикуете. Команда об этом предупреждает.

===========================================================================
ПРИВЯЗКА К ПРОЕКТУ — ГЛАВНОЕ ДЛЯ ОБЩЕГО ИНСТРУМЕНТА
===========================================================================

Стенограммы всех проектов лежат в одном месте (`~/.claude/projects/`).
Инструмент, который берёт оттуда всё подряд, при работе в нескольких
проектах кладёт стенограмму проекта A в репозиторий проекта B. Это не
неудобство, а утечка.

Поэтому отбор идёт не по имени каталога (оно кодируется по-разному), а по
полю `cwd` внутри самих записей: берутся только те стенограммы, чей `cwd`
лежит внутри корня текущего проекта. Корень определяется через
`git rev-parse --show-toplevel`, иначе — текущий каталог.

Ключ `--all-projects` снимает ограничение, но требуется явно: по умолчанию
чужого в репозиторий не попадает.

===========================================================================
СТРУКТУРА
===========================================================================

    <корень проекта>/
      .chatman/rules.md               канон ЭТОГО проекта (правится руками)
      .chatman/config.json            имя проекта, область поиска, якоря
      chatlog/
        raw/<сессия>.part-NNN.jsonl   запись ДОСЛОВНО (не перерабатывается)
        raw/<сессия>.manifest.json    границы кусков + sha256 (проверяемость)
        index/<сессия>.prompts.jsonl  производный индекс распоряжений
        <сессия>.meta.json            рамка чата: заголовок, ветка, счётчики

`raw/` — источник истины. Всё прочее производно: удалил — пересобрал
командой `export`.

===========================================================================
КАНОН: ЧТО В ТЕЛЕ, А ЧТО В ПРОЕКТЕ
===========================================================================

Правила, лежащие только в отдельном файле, можно не прочитать; инструмент
запускают всегда — поэтому канон печатается им. Но канон у каждого проекта
свой, и вшивать чужой в общий инструмент нельзя: так в него однажды попали
правила про осциллограф, которого в проекте нет.

Разделение: ОБЩАЯ часть (ниже, в теле) верна везде — она о стенограмме,
поиске и совместной работе чатов. ПРОЕКТНАЯ часть лежит в
`.chatman/rules.md` и печатается следом. `doctor` проверяет, что проектный
канон на месте и его опорные фразы не разошлись с источниками.

===========================================================================
ВРЕЗКИ
===========================================================================

Часть распоряжений приходит не отдельным ходом, а очередью — внутрь уже
идущего. В стенограмме они записаны дословно, но НЕ ролью `user`: это
`type="attachment"` с `attachment.type="queued_command"`. Читалка, не
знающая о них, теряет их молча: замер по одному репозиторию дал 14
распоряжений из 22 — 8 врезок (36 %) были невидимы, и среди них самые
весомые поправки разговора. Системные уведомления
(`commandMode="task-notification"`) отделены от человеческих по
`origin.kind`. Вложения врезки (изображения-референсы) не выбрасываются, а
отмечаются строкой `[изображение …]`: без них смысл указания теряется.

Нумерация событий у `find --prompts` (по индексу) и у `find --context`
(по кускам) — ОДНА: тот же счётчик и тот же ключ отсева повторов. Иначе
номер из одного режима показывал бы в другом чужую реплику; так и было,
пока не исправили.

---------------------------------------------------------------------------
Модуль поиска по корпусу (`search`) — авторства пользователя проекта:
отчёт с областью, шагом, точностью и покрытием. Логика перенесена без
переделки.
"""
from __future__ import annotations

import argparse
import difflib
import glob
import hashlib
import io
import json
import os
import pathlib
import re
import shutil
import signal
import subprocess
import sys
import unicodedata
import zipfile
from dataclasses import dataclass, field

VERSION = "2.0"

# ===========================================================================
# ОБЩИЙ КАНОН — В ТЕЛЕ ИНСТРУМЕНТА НАМЕРЕННО
#
# Здесь только то, что верно в ЛЮБОМ проекте. Всё, что касается предмета
# конкретной работы, живёт в <корень>/.chatman/rules.md и печатается следом.
# ===========================================================================
RULES_COMMON = """\
ОБЩИЙ КАНОН (верен в любом проекте; печатается инструментом всегда)

СТЕНОГРАММА
  * НЕ ПЕРЕРАБАТЫВАЕТСЯ: ни чистки символов, ни сокращения выводов, ни
    пересказа — иначе перестаёт быть той сущностью, которой называется.
    Допустимы ровно два действия, оба обратимы: нарезка на куски и
    подсчёт sha256.
  * raw/ — источник истины; index/, meta, реестр — производное.
  * Врезки — тоже распоряжения, хотя роли user у них нет.
  * Разбор, не записанный в репозиторий, считается НЕ СДЕЛАННЫМ: контекст
    сессии сжимается, репозиторий — нет.

ПРИВЯЗКА К ПРОЕКТУ
  * У каждого проекта свой репозиторий. Стенограмма проекта пишется только
    в его репозиторий: отбор по полю `cwd` записей, а не по имени каталога.
  * Инструмент один на пользователя (~/.claude/tools). Копия в репозитории
    проекта — источник расхождения версий, а не удобство.

СЕМЕЙСТВО ЧАТОВ
  * ГЛАВНОГО ЧАТА НЕТ. Каждый чат пишет только файлы со своим
    идентификатором сессии; общих записываемых файлов не заводить — это
    гонка «чей коммит лёг последним, тот и главный».
  * При отказе push: git pull --rebase и повтор. Конфликтов внутри
    chatlog/ не бывает по построению.
  * Метка [сессия · номер] печатается у каждого совпадения: цитата без
    источника — заготовка для ложного основания. Более позднее
    распоряжение отменяет более раннее; прежде чем опереться на находку из
    чужого чата — сверить рамку и дату (`sessions`).

ПОИСК И ОТРИЦАТЕЛЬНЫЙ ОТВЕТ
  * «Не найдено» без параметров ничем не подтверждено. Отчёт обязан нести
    запрос X, область [a; b], шаг c (нормализация), точность ±d и
    ПОКРЫТИЕ. «Не найдено при 70 % байт» и «при 99 %» — разные утверждения.
  * Расширение не доказательство формата: важнее сигнатура. Растровые
    изображения без OCR идут в «не просмотрено», а не в «не найдено».
  * Отсутствие — такое же утверждение, как присутствие, и требует замера.

ДАННЫЕ
  * «Только на чтение» распространяется на побочные эффекты инструментов:
    импорт модуля из каталога данных оставляет там __pycache__ — это тоже
    запись.
  * Ничего не удаляется «за ненадобностью»: неверный указатель не отменяет
    верной идеи.
"""

PROJECT_RULES_STUB = """\
ПРАВИЛА ПРОЕКТА {name}

Здесь канон ЭТОГО проекта: что считается доказанным, чем меряется
готовность, какие ошибки уже случались и чего из-за них нельзя. Общая часть
(стенограмма, поиск, семейство чатов) печатается инструментом до этого
текста — дублировать её не нужно.

Пишите короткими правилами с причиной: правило без причины через месяц
выглядит произволом и его обходят.

    ПРИМЕР
      * <правило>. <из какой ошибки возникло и что она стоила>.
"""

UPSTREAM = "https://github.com/dtba3a-del/dtba3a-del/tree/main/chatman"
HOME_TOOL = pathlib.Path.home() / ".claude" / "tools" / "chatman.py"
SKILL_DIR = pathlib.Path.home() / ".claude" / "skills" / "chatman"
LAUNCHER = pathlib.Path.home() / ".local" / "bin" / "chatman"
CLAUDE_PROJECTS = pathlib.Path.home() / ".claude" / "projects"
PART_LINES = 2000


# ===========================================================================
# Корень проекта и его каталоги
# ===========================================================================
def git(*args, cwd=None) -> str:
    try:
        return subprocess.run(["git", *args], capture_output=True, text=True,
                              timeout=10, cwd=cwd).stdout.strip()
    except Exception:
        return ""


def project_root() -> pathlib.Path:
    """Корень репозитория, иначе текущий каталог. У проекта свой репозиторий."""
    top = git("rev-parse", "--show-toplevel")
    return pathlib.Path(top) if top else pathlib.Path.cwd()


ROOT = project_root()
CHATMAN_DIR = ROOT / ".chatman"
CHATLOG = ROOT / "chatlog"
RAW = CHATLOG / "raw"
INDEX = CHATLOG / "index"


def config() -> dict:
    p = CHATMAN_DIR / "config.json"
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception as exc:
            print(f"ВНИМАНИЕ: {p} не читается ({exc})", file=sys.stderr)
    return {}


def project_rules() -> str | None:
    p = CHATMAN_DIR / "rules.md"
    return p.read_text(encoding="utf-8") if p.exists() else None


def check_rules_sync() -> list[str]:
    """Сверка проектного канона с источниками, названными в config.

    Дублирование текста ржавеет: источник правят, копия остаётся прежней.
    Лечится не отказом от дублирования, а тем, что расхождение ВИДНО.
    """
    problems = []
    if project_rules() is None:
        problems.append(f"нет проектного канона: {CHATMAN_DIR / 'rules.md'} — "
                        f"заведите его командой `chatman init`")
    for path, anchors in (config().get("rules_anchors") or {}).items():
        p = ROOT / path
        if not p.exists():
            problems.append(f"нет источника правил: {path}")
            continue
        text = p.read_text(encoding="utf-8", errors="replace").lower()
        for a in anchors:
            if a.lower() not in text:
                problems.append(f"{path}: пропала опорная фраза «{a}» — "
                                f"сверьте .chatman/rules.md")
    return problems


def banner(short: str) -> None:
    """Напоминание в stderr: конвейеры чистые, но правило видно."""
    print(f"правила: {short}\n         полностью: chatman rules", file=sys.stderr)
    for p in check_rules_sync():
        print("ВНИМАНИЕ:", p, file=sys.stderr)


# ===========================================================================
# Общий разбор стенограммы — ОДИН на все команды
# ===========================================================================
def prompt_text(a: dict) -> str:
    """Текст врезки; вложения отмечаются, а не выбрасываются."""
    raw = a.get("prompt", "")
    if isinstance(raw, str):
        return raw
    out = []
    for b in raw or []:
        if not isinstance(b, dict):
            continue
        if b.get("type") == "text":
            out.append(b.get("text", ""))
        elif b.get("type") == "image":
            src = b.get("source") or {}
            out.append(f"[изображение {src.get('media_type', '?')}]")
    return "\n".join(x for x in out if x)


def queued_prompt(d: dict):
    """Врезка от человека или None (уведомления системы отсеиваются)."""
    if d.get("type") != "attachment":
        return None
    a = d.get("attachment") or {}
    if a.get("type") != "queued_command" or a.get("commandMode") != "prompt":
        return None
    if (a.get("origin") or {}).get("kind") != "human":
        return None
    return a


def queued_key(q: dict) -> tuple:
    """Ключ отсева повторов. ОДИН на export и на find — иначе номера разойдутся."""
    return (str(q.get("source_uuid")), prompt_text(q)[:80])


def human_prompt(d: dict):
    """(вид, текст, время) для распоряжения человека, иначе None."""
    q = queued_prompt(d)
    if q is not None:
        return "врезка", prompt_text(q), q.get("timestamp") or d.get("timestamp", "")
    if d.get("type") != "user" or not d.get("promptId"):
        return None
    content = (d.get("message") or {}).get("content")
    if isinstance(content, list) and any(
            isinstance(b, dict) and b.get("type") == "tool_result" for b in content):
        return None
    if isinstance(content, str):
        text = content
    else:
        text = "\n".join(b.get("text", "") for b in (content or [])
                         if isinstance(b, dict) and b.get("type") == "text")
    return ("ход", text, d.get("timestamp", "")) if text.strip() else None


def flat(content) -> str:
    if isinstance(content, str):
        return content
    out = []
    for b in content or []:
        if not isinstance(b, dict):
            continue
        if b.get("type") == "text":
            out.append(b.get("text", ""))
        elif b.get("type") == "tool_use":
            inp = b.get("input", {})
            out.append(f"[{b.get('name')}] {inp.get('command') or inp.get('file_path') or ''}")
        elif b.get("type") == "tool_result":
            out.append(flat(b.get("content")))
    return "\n".join(x for x in out if x)


def transcript_cwd(path: pathlib.Path) -> str:
    """Каталог, в котором велась сессия — берётся из самих записей.

    Имя каталога в ~/.claude/projects кодируется и может не совпасть с
    путём; поле `cwd` внутри записей — источник надёжнее.
    """
    try:
        with path.open(encoding="utf-8", errors="replace") as fh:
            for i, line in enumerate(fh):
                if i > 50:
                    break
                try:
                    d = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if d.get("cwd"):
                    return d["cwd"]
    except Exception:
        pass
    return ""


def own_transcripts(all_projects: bool = False) -> list[pathlib.Path]:
    """Стенограммы ТЕКУЩЕГО проекта. Чужие не берём — это была бы утечка."""
    if not CLAUDE_PROJECTS.exists():
        return []
    files = sorted(set(list(CLAUDE_PROJECTS.glob("*/*.jsonl"))
                       + list(CLAUDE_PROJECTS.glob("*.jsonl"))))
    if all_projects:
        return files
    root = str(ROOT.resolve())
    mine = []
    for f in files:
        cwd = transcript_cwd(f)
        if cwd and (cwd == root or cwd.startswith(root + os.sep)):
            mine.append(f)
    return mine


def profile_sessions(all_projects: bool = True) -> list[tuple[str, pathlib.Path, str]]:
    """(сессия, файл, cwd) из ПРОФИЛЯ. Приватная зона, ничего не пишется.

    Общего каталога логов не заводим: стенограммы уже лежат в профиле
    пользователя. Инструмент ходит по ним на месте — так контексты всех
    репозиториев доступны, а в публичный репозиторий не попадает ничего.
    """
    if not CLAUDE_PROJECTS.exists():
        return []
    out = []
    root = str(ROOT.resolve())
    for f in sorted(set(list(CLAUDE_PROJECTS.glob("*/*.jsonl"))
                        + list(CLAUDE_PROJECTS.glob("*.jsonl")))):
        cwd = transcript_cwd(f)
        if not all_projects and not (cwd == root or cwd.startswith(root + os.sep)):
            continue
        out.append((f.stem, f, cwd))
    return out


def live_events(items):
    for sid, path, _cwd in items:
        with open(path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                try:
                    yield sid, json.loads(line)
                except json.JSONDecodeError:
                    continue


def session_ids() -> list[str]:
    return sorted({pathlib.Path(p).name.split(".part-")[0]
                   for p in glob.glob(str(RAW / "*.part-*.jsonl"))})


def meta(sid: str) -> dict:
    p = CHATLOG / f"{sid}.meta.json"
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"session": sid}


def match_session(sid: str, want: str) -> bool:
    return bool(want) and (sid == want or sid.startswith(want))


def events(sids: list[str]):
    for sid in sids:
        for part in sorted(glob.glob(str(RAW / f"{sid}.part-*.jsonl"))):
            with open(part, encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    try:
                        yield sid, json.loads(line)
                    except json.JSONDecodeError:
                        continue


def pick_sessions(a) -> list[str]:
    sids = session_ids()
    if not sids:
        return []
    if getattr(a, "mine", False):
        cur = os.environ.get("CLAUDE_SESSION_ID", "")
        sids = [s for s in sids if match_session(s, cur)] or sids
    if getattr(a, "session", None):
        sids = [s for s in sids if match_session(s, a.session)]
    return sids


# ===========================================================================
# init — завести проект
# ===========================================================================
def cmd_init(a) -> int:
    name = a.name or ROOT.name
    CHATMAN_DIR.mkdir(parents=True, exist_ok=True)
    rules = CHATMAN_DIR / "rules.md"
    created = []
    if not rules.exists():
        rules.write_text(PROJECT_RULES_STUB.format(name=name), encoding="utf-8")
        created.append(str(rules.relative_to(ROOT)))
    cfg_path = CHATMAN_DIR / "config.json"
    if not cfg_path.exists():
        cfg_path.write_text(json.dumps({
            "project": name,
            "search_domain": ".",
            "rules_anchors": {},
        }, ensure_ascii=False, indent=1), encoding="utf-8")
        created.append(str(cfg_path.relative_to(ROOT)))
    # Указатель в самом проекте. Навык и ~/.claude/tools живут в профиле и
    # в новой среде их нет; репозиторий переживает смену машины, поэтому
    # ссылка «где взять» должна лежать в нём, а не только в профиле.
    pointer = CHATMAN_DIR / "README.md"
    if not pointer.exists():
        pointer.write_text(
            "# Инструмент проекта: chatman\n\n"
            "Стенограммы рабочих чатов, поиск с замером покрытия, канон.\n"
            "В репозитории его НЕТ намеренно: одна копия на пользователя,\n"
            "иначе копии расходятся по версиям.\n\n"
            f"Взять: {UPSTREAM}\n\n"
            "```bash\n"
            "python3 chatman.py install     # ~/.claude/tools + PATH + навык\n"
            "chatman doctor                 # проверить, что всё на месте\n"
            "chatman rules                  # канон: общий + этого проекта\n"
            "```\n\n"
            "**Как пользоваться — в докстринге самого файла:**\n"
            "`head -110 ~/.claude/tools/chatman.py`.\n\n"
            "Канон этого проекта — `rules.md` рядом; общая часть канона\n"
            "вшита в инструмент и печатается перед проектной.\n",
            encoding="utf-8")
        created.append(str(pointer.relative_to(ROOT)))

    print(f"проект: {name}\nкорень: {ROOT}")
    print("создано:" if created else "всё уже на месте")
    for c in created:
        print("   ", c)
    print("\nДальше:")
    print("  1) впишите канон проекта в .chatman/rules.md (причину у каждого правила)")
    print("  2) при желании укажите в .chatman/config.json опорные фразы:")
    print('       "rules_anchors": {"README.md": ["<фраза, которая обязана быть>"]}')
    print("  3) chatman export && git add .chatman chatlog && git commit")
    gi = ROOT / ".gitignore"
    txt = gi.read_text(encoding="utf-8", errors="replace") if gi.exists() else ""
    if "__pycache__" not in txt:
        print("\nв .gitignore стоит добавить: __pycache__/")
    return 0


# ===========================================================================
# export — выгрузка своей сессии
# ===========================================================================
def cmd_export(a) -> int:
    banner("стенограмма не перерабатывается (только нарезка и sha256); "
           "пишем ТОЛЬКО файлы своей сессии — главного чата нет")
    # Выгрузка — осознанное действие, а не умолчание: она ПУБЛИКУЕТ дословную
    # запись со всем, что было в выводе команд. Для чтения и поиска выгрузка
    # не нужна — `find` и `search` работают прямо по профилю.
    pub = git("remote", "get-url", "origin")
    print(f"ВНИМАНИЕ: выгрузка кладёт дословную запись в репозиторий"
          f"{' (' + pub + ')' if pub else ''}.\n"
          f"          Для чтения и поиска этого НЕ требуется: `chatman find`\n"
          f"          и `chatman search` читают профиль на месте.\n",
          file=sys.stderr)
    files = own_transcripts(a.all_projects)
    if not files:
        if not CLAUDE_PROJECTS.exists():
            print("стенограмм не найдено:", CLAUDE_PROJECTS, file=sys.stderr)
        else:
            print(f"нет стенограмм, чей cwd лежит внутри {ROOT}.\n"
                  f"Это защита от утечки: чужие проекты сюда не пишутся. "
                  f"Если нужно именно всё — `--all-projects`.", file=sys.stderr)
        return 1
    RAW.mkdir(parents=True, exist_ok=True)
    INDEX.mkdir(parents=True, exist_ok=True)
    branch_now = git("rev-parse", "--abbrev-ref", "HEAD")

    for f in files:
        sid = f.stem
        data = f.read_bytes()
        lines = data.splitlines(keepends=True)

        man_path = RAW / f"{sid}.manifest.json"
        man = json.loads(man_path.read_text(encoding="utf-8")) if man_path.exists() \
            else {"session": sid, "lines_exported": 0, "parts": []}
        new = lines[man["lines_exported"]:]
        while new:
            chunk, new = new[:PART_LINES], new[PART_LINES:]
            name = f"{sid}.part-{len(man['parts']) + 1:03d}.jsonl"
            (RAW / name).write_bytes(b"".join(chunk))  # дословно, как записано
            man["parts"].append({"file": name, "lines": len(chunk),
                                 "from": man["lines_exported"] + 1,
                                 "to": man["lines_exported"] + len(chunk),
                                 "sha256": hashlib.sha256(b"".join(chunk)).hexdigest()})
            man["lines_exported"] += len(chunk)
        man["lines_total"] = len(lines)
        man["bytes_total"] = len(data)
        man["sha256_full"] = hashlib.sha256(data).hexdigest()
        man_path.write_text(json.dumps(man, ensure_ascii=False, indent=1), encoding="utf-8")

        st = {"assistant": 0, "first": "", "last": "", "prompts": 0, "inserts": 0}
        prompts, seq, seen = [], 0, set()
        for b in lines:
            try:
                d = json.loads(b.decode("utf-8", "replace"))
            except Exception:
                continue
            # Нумерация ОБЯЗАНА совпадать с `find` (полный путь), иначе номер
            # из `find --prompts` покажет в `--context` чужое событие.
            q = queued_prompt(d)
            if q is not None:
                key = queued_key(q)
                if key in seen:
                    continue
                seen.add(key)
                seq += 1
            elif d.get("type") in ("user", "assistant"):
                seq += 1
                if d.get("type") == "assistant":
                    st["assistant"] += 1
            ts = d.get("timestamp", "")
            if ts:
                st["first"] = st["first"] or ts
                st["last"] = ts
            hp = human_prompt(d)
            if hp:
                kind, text, hts = hp
                prompts.append({"session": sid, "seq": seq, "ts": hts,
                                "kind": kind, "text": text})
                st["prompts"] += 1
                st["inserts"] += (kind == "врезка")

        meta_path = CHATLOG / f"{sid}.meta.json"
        old = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
        title = next((" ".join(p["text"].split())[:90] for p in prompts if p["text"].strip()), "")
        meta_path.write_text(json.dumps({
            "session": sid,
            "project": config().get("project", ROOT.name),
            "title": old.get("title") or title,   # задаётся однажды
            "note": old.get("note", ""),          # ручная пометка о рамке чата
            "branch": old.get("branch") or branch_now,
            "first": st["first"], "last": st["last"],
            "prompts": st["prompts"], "inserts": st["inserts"],
            "assistant_events": st["assistant"], "lines": len(lines),
        }, ensure_ascii=False, indent=1), encoding="utf-8")

        with (INDEX / f"{sid}.prompts.jsonl").open("w", encoding="utf-8") as fh:
            for p in prompts:
                fh.write(json.dumps(p, ensure_ascii=False) + "\n")
        print(f"{sid}: строк {len(lines)}, кусков {len(man['parts'])}, "
              f"распоряжений {st['prompts']} (врезок {st['inserts']})")

    print("\nГотово. Тронуты только файлы своей сессии — общих нет. Дальше:")
    print("  chatman sessions")
    print("  chatman find --prompts --grep '...'")
    print("  git add chatlog/ && git commit && git push   "
          "(при отказе: git pull --rebase && git push)")
    return 0


# ===========================================================================
# sessions — реестр, собранный на лету
# ===========================================================================
def cmd_sessions(a) -> int:
    sids = session_ids()
    if not sids:
        print("выгруженных сессий нет; сначала: chatman export", file=sys.stderr)
        return 1
    print(f"Проект: {config().get('project', ROOT.name)}  ({ROOT})")
    print(f"Сессий выгружено: {len(sids)}\n")
    for sid in sorted(sids, key=lambda s: meta(s).get("first", "")):
        m = meta(sid)
        print(f"  {sid[:8]}  {m.get('first', '?')[:16]} .. {m.get('last', '?')[:16]}  "
              f"ветка {m.get('branch', '?')}")
        print(f"            распоряжений {m.get('prompts', '?')} "
              f"(врезок {m.get('inserts', '?')}), строк {m.get('lines', '?')}")
        note = m.get("note") or m.get("title", "")
        if note:
            print(f"            рамка: {note}")
    print("\nРеестр собран на лету из *.meta.json — сводного файла нет, чтобы")
    print("чаты не соперничали за право переписать его последними.")
    print("Опираясь на находку из чужого чата, сверьте рамку и дату:")
    print("более позднее распоряжение отменяет более раннее.")
    return 0


# ===========================================================================
# repos — какие репозитории пользователя есть в профиле
# ===========================================================================
def cmd_repos(a) -> int:
    items = profile_sessions(all_projects=True)
    if not items:
        print(f"в профиле стенограмм нет: {CLAUDE_PROJECTS}", file=sys.stderr)
        return 1
    by_repo: dict[str, list] = {}
    for sid, path, cwd in items:
        by_repo.setdefault(cwd or "<без cwd>", []).append((sid, path))
    here = str(ROOT.resolve())
    print(f"Стенограммы в профиле: {CLAUDE_PROJECTS}")
    print("Ничего не выгружается — чтение на месте, приватная зона.\n")
    for cwd in sorted(by_repo):
        mark = "  <- здесь" if cwd == here else ""
        sess = by_repo[cwd]
        size = sum(p.stat().st_size for _s, p in sess)
        print(f"  {cwd}{mark}")
        print(f"      сессий {len(sess)}, {size/1024/1024:.2f} МБ")
        for sid, p in sess[:6]:
            print(f"        {sid[:8]}  {p.stat().st_size/1024:.0f} КБ")
        if len(sess) > 6:
            print(f"        … ещё {len(sess)-6}")
    print("\nИскать в другом репозитории:  chatman find --repo <часть пути> --prompts")
    return 0


# ===========================================================================
# find — чтение и поиск (только читает)
# ===========================================================================
def label(sid: str, seq: int, who: str, ts: str) -> str:
    """Метка источника. Печатается ВСЕГДА: цитата без источника —
    заготовка для чужого решения, выданного за наше."""
    return f"\n=== [{sid[:8]} · {seq}] {who} · {ts} ==="


def cmd_find(a) -> int:
    if not a.quiet:
        banner("цитата без метки сессии запрещена; позднее распоряжение "
               "отменяет более раннее; стенограмма не перерабатывается")
    # Источник: профиль (приватно, ничего не пишется) либо выгрузка в репо.
    live = None
    if a.exported:
        sids = pick_sessions(a)
        if not sids:
            print("выгрузки нет; уберите --exported или сделайте `chatman export`",
                  file=sys.stderr)
            return 1
    else:
        want = a.repo
        items = profile_sessions(all_projects=bool(want))
        if want:
            items = [t for t in items if want.lower() in (t[2] or "").lower()]
        if a.session:
            items = [t for t in items if match_session(t[0], a.session)]
        if a.mine:
            cur = os.environ.get("CLAUDE_SESSION_ID", "")
            items = [t for t in items if match_session(t[0], cur)] or items
        if not items:
            print(f"в профиле нет подходящих стенограмм"
                  f"{' для ' + want if want else f' для {ROOT}'}; см. `chatman repos`",
                  file=sys.stderr)
            return 1
        live = items
        sids = [t[0] for t in items]

    # Быстрый путь: распоряжения — из производного индекса (только у выгрузки).
    if a.exported and a.prompts and not a.range and a.context is None:
        rows, ok = [], True
        for sid in sids:
            p = INDEX / f"{sid}.prompts.jsonl"
            if not p.exists():
                ok = False
                break
            with p.open(encoding="utf-8") as fh:
                rows += [json.loads(x) for x in fh if x.strip()]
        if ok:
            rows.sort(key=lambda r: (r.get("ts", ""), r.get("session", "")))
            shown = 0
            for r in rows:
                if a.at and not r.get("ts", "").startswith(a.at):
                    continue
                text = r.get("text", "")
                if a.grep and a.grep.lower() not in text.lower():
                    continue
                who = "ПОЛЬЗОВАТЕЛЬ (врезка)" if r.get("kind") == "врезка" else "ПОЛЬЗОВАТЕЛЬ"
                print(label(r["session"], r.get("seq", 0), who, r.get("ts", "")))
                print(text if not a.width else text[: a.width])
                shown += 1
            if not shown:
                print("ничего не найдено", file=sys.stderr)
                return 1
            if len({r["session"] for r in rows}) > 1:
                print("\n— найдено в нескольких чатах; сверьте рамку: "
                      "chatman sessions", file=sys.stderr)
            return 0

    lo = hi = None
    if a.context is not None:
        lo, hi = a.context - a.around, a.context + a.around
    if a.range:
        lo, hi = a.range

    idx: dict[str, int] = {}
    shown = 0
    seen_queued = set()
    stream = live_events(live) if live is not None else events(sids)
    for sid, d in stream:
        t = d.get("type")
        q = queued_prompt(d)
        if q is not None:
            key = queued_key(q)
            if key in seen_queued:
                continue
            seen_queued.add(key)
            t = "user"
        elif t not in ("user", "assistant"):
            continue
        idx[sid] = idx.get(sid, 0) + 1
        n = idx[sid]
        if a.user and t != "user":
            continue
        if a.prompts:
            if t != "user":
                continue
            if q is None and not human_prompt(d):
                continue
        if lo is not None and not (lo <= n <= hi):
            continue
        ts = (q or {}).get("timestamp") or d.get("timestamp", "")
        if a.at and not ts.startswith(a.at):
            continue
        body = prompt_text(q) if q else flat((d.get("message") or {}).get("content"))
        if not body.strip():
            continue
        if a.grep and a.grep.lower() not in body.lower():
            continue
        who = ("ПОЛЬЗОВАТЕЛЬ (врезка)" if q else
               "ПОЛЬЗОВАТЕЛЬ" if t == "user" else "исполнитель")
        print(label(sid, n, who, ts))
        print(body if not a.width else body[: a.width])
        shown += 1

    if not shown:
        print("ничего не найдено", file=sys.stderr)
        return 1
    if len(sids) > 1:
        print("\n— искали по нескольким чатам; сверьте рамку: chatman sessions",
              file=sys.stderr)
    return 0


# ===========================================================================
# verify — дословность проверяема, а не обещана
# ===========================================================================
def cmd_verify(a) -> int:
    sids = pick_sessions(a) or session_ids()
    if not sids:
        print("выгруженных сессий нет", file=sys.stderr)
        return 1
    bad = 0
    for sid in sids:
        man_path = RAW / f"{sid}.manifest.json"
        if not man_path.exists():
            print(f"{sid[:8]}: манифеста нет", file=sys.stderr)
            bad += 1
            continue
        man = json.loads(man_path.read_text(encoding="utf-8"))
        h = hashlib.sha256()
        total = 0
        for part in man["parts"]:
            data = (RAW / part["file"]).read_bytes()
            if hashlib.sha256(data).hexdigest() != part["sha256"]:
                print(f"{sid[:8]}: кусок {part['file']} НЕ совпал с манифестом",
                      file=sys.stderr)
                bad += 1
            h.update(data)
            total += len(data)
        same = h.hexdigest() == man.get("sha256_full")
        print(f"{sid[:8]}: кусков {len(man['parts'])}, байт {total}, "
              f"склейка {'совпала' if same else 'НЕ совпала'} с sha256_full")
        bad += (not same)
    return 1 if bad else 0


# ===========================================================================
# search — поиск по корпусу с замером (авторский модуль пользователя проекта)
# ===========================================================================
HOMOGLYPHS = str.maketrans({
    "a": "а", "c": "с", "e": "е", "o": "о", "p": "р", "x": "х", "y": "у",
    "A": "А", "B": "В", "C": "С", "E": "Е", "H": "Н", "K": "К", "M": "М",
    "O": "О", "P": "Р", "T": "Т", "X": "Х",
})


@dataclass
class Coverage:
    files_total: int = 0
    files_read: int = 0
    bytes_total: int = 0
    bytes_read: int = 0
    skipped: list = field(default_factory=list)
    partial: list = field(default_factory=list)

    def pct_files(self) -> float:
        return 100.0 * self.files_read / self.files_total if self.files_total else 0.0

    def pct_bytes(self) -> float:
        return 100.0 * self.bytes_read / self.bytes_total if self.bytes_total else 0.0


def normalize(s: str, step: str) -> str:
    if "nfkc" in step:
        s = unicodedata.normalize("NFKC", s)
    if "case" in step:
        s = s.casefold()
    if "hyphen" in step:
        s = re.sub(r"[-­‐‑]\s*\n\s*", "", s)
    if "space" in step:
        s = re.sub(r"\s+", " ", s)
    if "homoglyph" in step:
        s = s.translate(HOMOGLYPHS)
    return s


def _decode(data: bytes):
    s = data.decode("utf-8", "replace")
    if not s:
        return ""
    return None if s.count("�") / max(1, len(s)) > 0.02 else s


def _printable_runs(data: bytes, minlen: int = 4) -> str:
    out, cur = [], bytearray()
    for b in data:
        if 32 <= b < 127 or b >= 0xC0 or (0x80 <= b < 0xC0 and cur):
            cur.append(b)
        else:
            if len(cur) >= minlen:
                out.append(bytes(cur).decode("utf-8", "replace"))
            cur = bytearray()
    if len(cur) >= minlen:
        out.append(bytes(cur).decode("utf-8", "replace"))
    return "\n".join(out)


def _from_ooxml(data: bytes, parts: str) -> str:
    z = zipfile.ZipFile(io.BytesIO(data))
    out = []
    for n in z.namelist():
        if re.search(parts, n):
            xml = z.read(n).decode("utf-8", "replace")
            xml = re.sub(r"</w:p>|</text:p>|</text:h>", "\n", xml)
            out.append(re.sub(r"<[^>]+>", "", xml))
    return "\n".join(out)


def extract(path: str, data: bytes, cov: Coverage, name: str):
    """Вернуть [(имя, текст)] или пометить пропуск с причиной."""
    ext = os.path.splitext(path)[1].lower()
    # Расширение — не доказательство формата; сигнатура важнее.
    if data[:2] == b"PK" and ext not in {".docx", ".odt", ".xlsx", ".xlsm"}:
        ext = ".zip"
    if data[:5] == b"%PDF-":
        ext = ".pdf"
    try:
        if ext == ".zip":
            out = []
            z = zipfile.ZipFile(io.BytesIO(data))
            for n in z.namelist():
                if not n.endswith("/"):
                    out += extract(n, z.read(n), cov, f"{name}!{n}")
            return out
        if ext == ".docx":
            return [(name, _from_ooxml(data, r"word/(document|footnotes|endnotes)\.xml$"))]
        if ext == ".odt":
            return [(name, _from_ooxml(data, r"^content\.xml$"))]
        if ext == ".pdf":
            from pypdf import PdfReader
            r = PdfReader(io.BytesIO(data))
            return [(name, "\n".join((p.extract_text() or "") for p in r.pages))]
        if ext in {".xlsx", ".xlsm"}:
            return [(name, _from_ooxml(data, r"^xl/(sharedStrings|worksheets/.*)\.xml$"))]
        if ext in {".png", ".jpg", ".jpeg", ".gif"}:
            cov.skipped.append((name, f"растровое изображение {ext}: нужен OCR, его нет"))
            return []
        txt = _decode(data)
        if txt is not None:
            return [(name, txt)]
        runs = _printable_runs(data)
        if runs:
            cov.partial.append((name, f"только извлечённые строки ({ext or 'без расширения'})"))
            return [(name, runs)]
        cov.skipped.append((name, "двоичный, печатных строк не найдено"))
        return []
    except Exception as exc:
        cov.skipped.append((name, f"{type(exc).__name__}: {exc}"))
        return []


def fuzzy_hits(text: str, pattern: str, d: int) -> int:
    if d <= 0:
        return 0
    lo, hi = len(pattern) - d, len(pattern) + d
    words = {w for w in re.findall(r"\w+", text) if lo <= len(w) <= hi}
    return len(difflib.get_close_matches(pattern, words, n=50,
                                         cutoff=1 - d / max(len(pattern), 1)))


SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv", "venv", ".mypy_cache"}


def cmd_search(a) -> int:
    domain = a.domain or config().get("search_domain") or "."
    domain = str((ROOT / domain).resolve()) if not os.path.isabs(domain) else domain
    step, d = a.step, a.fuzzy
    cov = Coverage()
    found = {p: {} for p in a.patterns}
    npats = [normalize(p, step) for p in a.patterns]
    for dp, dirs, fns in os.walk(domain):
        dirs[:] = [x for x in dirs if x not in SKIP_DIRS]
        for fn in sorted(fns):
            path = os.path.join(dp, fn)
            rel = os.path.relpath(path, domain)
            cov.files_total += 1
            try:
                size = os.path.getsize(path)
                cov.bytes_total += size
                data = open(path, "rb").read()
            except Exception as exc:
                cov.skipped.append((rel, f"не читается: {exc}"))
                continue
            pieces = extract(path, data, cov, rel)
            if not pieces:
                continue
            cov.files_read += 1
            cov.bytes_read += size
            for name, text in pieces:
                norm = normalize(text, step)
                for p, np_ in zip(a.patterns, npats):
                    n = norm.count(np_) + (fuzzy_hits(norm, np_, d) if d else 0)
                    if n:
                        found[p][name] = found[p].get(name, 0) + n

    L = [f"ПОИСК: {', '.join(a.patterns)}",
         f"  область [a; b] : {domain}",
         f"                   файлов {cov.files_total}, "
         f"{cov.bytes_total/1024/1024:.2f} МБ; архивы вскрыты рекурсивно",
         f"  шаг c          : {step}",
         f"  точность ±d    : {d} (расстояние редактирования; 0 = только точные)",
         f"  ПОКРЫТИЕ       : файлов {cov.pct_files():.1f}% "
         f"({cov.files_read}/{cov.files_total}), байт {cov.pct_bytes():.1f}%", ""]
    for p in a.patterns:
        hits = found[p]
        if hits:
            L.append(f"  «{p}»: НАЙДЕНО — {sum(hits.values())} вхождений "
                     f"в {len(hits)} файлах")
            for f_, c in sorted(hits.items(), key=lambda kv: -kv[1])[:6]:
                L.append(f"       {c:>5}×  {f_}")
            if len(hits) > 6:
                L.append(f"       … ещё {len(hits)-6} файлов")
        else:
            L.append(f"  «{p}»: НЕ НАЙДЕНО при покрытии {cov.pct_bytes():.1f}% байт")
    if cov.partial:
        L += ["", f"  ЧАСТИЧНОЕ ПОКРЫТИЕ ({len(cov.partial)}) — прочитано не полностью:"]
        for name, why in cov.partial[:8]:
            L.append(f"       {name}  —  {why}")
        if len(cov.partial) > 8:
            L.append(f"       … ещё {len(cov.partial)-8}")
    if cov.skipped:
        L += ["", f"  НЕ ПРОСМОТРЕНО ({len(cov.skipped)}) — здесь совпадение возможно:"]
        seen: dict[str, list] = {}
        for name, why in cov.skipped:
            seen.setdefault(why, []).append(name)
        for why, names in sorted(seen.items(), key=lambda kv: -len(kv[1])):
            L.append(f"       {len(names):>4} × {why}")
            for n in names[:3]:
                L.append(f"              {n}")
    print("\n".join(L))
    return 0


# ===========================================================================
# install / doctor — одна копия на пользователя, видна в каждом чате
# ===========================================================================
SKILL_MD = """\
---
name: chatman
description: Стенограммы рабочих чатов, поиск с замером покрытия и канон проекта. Используй, когда нужно вспомнить, что именно было сказано или решено в этом или прошлом чате; найти распоряжение пользователя среди выводов инструментов; выгрузить стенограмму в репозиторий; проверить её дословность; искать по корпусу файлов с честным отчётом о покрытии.
---

# chatman

Инструмент установлен: `~/.claude/tools/chatman.py` (и `chatman` на PATH).
**Руководство — в докстринге самого файла**, там же устройство врезок и
привязка к проекту: `head -110 ~/.claude/tools/chatman.py`.

Порядок применения:

```bash
chatman export                          # выгрузить свою сессию (дословно)
chatman sessions                        # какие чаты есть и о чём
chatman find --prompts --grep '...'     # найти распоряжение
chatman find --context 77 --around 3    # что было вокруг него
chatman verify                          # сверить дословность по sha256
chatman search <образец> --fuzzy 1      # поиск по корпусу с покрытием
chatman rules                           # канон: общий + проектный
chatman doctor                          # самопроверка
```

Главное, что нужно помнить при работе:

* стенограмма **не перерабатывается** — только нарезка и sha256;
* роль `user` несут и результаты инструментов, поэтому настоящие
  распоряжения отбирает `--prompts`; врезки (очередь внутрь хода) — тоже
  распоряжения, хотя роли `user` у них нет;
* цитата печатается с меткой `[сессия · номер]`; более позднее
  распоряжение отменяет более раннее;
* «не найдено» без покрытия ничего не значит.
"""


def cmd_install(a) -> int:
    src = pathlib.Path(__file__).resolve()
    HOME_TOOL.parent.mkdir(parents=True, exist_ok=True)
    if src != HOME_TOOL:
        shutil.copy2(src, HOME_TOOL)
    HOME_TOOL.chmod(0o755)
    print(f"инструмент: {HOME_TOOL}")

    LAUNCHER.parent.mkdir(parents=True, exist_ok=True)
    LAUNCHER.write_text(f'#!/bin/sh\nexec python3 "{HOME_TOOL}" "$@"\n', encoding="utf-8")
    LAUNCHER.chmod(0o755)
    print(f"пусковой файл: {LAUNCHER}")
    if str(LAUNCHER.parent) not in os.environ.get("PATH", "").split(":"):
        print(f"  ВНИМАНИЕ: {LAUNCHER.parent} не в PATH — добавьте в профиль:")
        print(f'    export PATH="{LAUNCHER.parent}:$PATH"')

    SKILL_DIR.mkdir(parents=True, exist_ok=True)
    (SKILL_DIR / "SKILL.md").write_text(SKILL_MD, encoding="utf-8")
    print(f"навык для чатов: {SKILL_DIR / 'SKILL.md'}")

    print("\nОдна копия на пользователя — намеренно: копия в каждом репозитории")
    print("расходится по версиям, и вчерашний замер перестаёт сходиться с")
    print("сегодняшним. В новом проекте: cd <корень> && chatman init")
    return 0


def cmd_doctor(a) -> int:
    ok = True
    print(f"chatman {VERSION}")
    print(f"  запущен из : {pathlib.Path(__file__).resolve()}")
    print(f"  корень     : {ROOT}" + ("" if (ROOT / ".git").exists()
                                      else "   (не git-репозиторий!)"))
    print(f"  проект     : {config().get('project', ROOT.name)}")

    installed = HOME_TOOL.exists()
    print(f"  установлен : {'да' if installed else 'НЕТ'}")
    if not installed:
        print(f"               взять: {UPSTREAM}")
        print(f"               затем: python3 chatman.py install")
    if installed and pathlib.Path(__file__).resolve() != HOME_TOOL:
        a_ = hashlib.sha256(pathlib.Path(__file__).resolve().read_bytes()).hexdigest()
        b_ = hashlib.sha256(HOME_TOOL.read_bytes()).hexdigest()
        if a_ != b_:
            ok = False
            print("  ВНИМАНИЕ: запущенная копия ОТЛИЧАЕТСЯ от установленной —")
            print("            это ровно та рассинхронизация, ради которой")
            print("            инструмент держат в одном месте. `chatman install`")
    print(f"  навык      : {'есть' if (SKILL_DIR / 'SKILL.md').exists() else 'нет'}")
    print(f"  на PATH    : {'да' if shutil.which('chatman') else 'нет'}")

    own = own_transcripts(False)
    print(f"  стенограмм этого проекта: {len(own)}")
    others = len(own_transcripts(True)) - len(own)
    if others:
        print(f"  чужих проектов рядом    : {others} (в этот репозиторий НЕ пишутся)")

    probs = check_rules_sync()
    if probs:
        ok = False
        print("  канон:")
        for p in probs:
            print("    ВНИМАНИЕ:", p)
    else:
        print("  канон      : проектный на месте, опорные фразы сходятся")

    # Копия в репозитории — не всегда лишняя: в репозитории-ИСТОЧНИКЕ она и
    # есть исходник, из которого ставят. Важно не наличие, а расхождение.
    local = ROOT / "tools" / "chatman.py"
    if local.exists() and installed:
        same = hashlib.sha256(local.read_bytes()).hexdigest() == \
            hashlib.sha256(HOME_TOOL.read_bytes()).hexdigest()
        print(f"  копия в репозитории: {local.relative_to(ROOT)} — "
              f"{'совпадает с установленной' if same else 'РАСХОДИТСЯ'}")
        if not same:
            ok = False
            print("            это и есть та рассинхронизация, ради которой")
            print("            инструмент держат в одном месте: `chatman install`")
    old = [x for x in ("export_chat.py", "read_chat.py", "search_report.py")
           if (ROOT / "tools" / x).exists()]
    if old:
        print("  устаревшие инструменты (слиты в chatman, можно удалить):",
              ", ".join(old))
    return 0 if ok else 1


# ===========================================================================
# CLI
# ===========================================================================
def cmd_rules(a) -> int:
    print(RULES_COMMON)
    pr = project_rules()
    if pr:
        print("=" * 75)
        print(pr)
    else:
        print("=" * 75)
        print(f"Проектного канона нет: {CHATMAN_DIR / 'rules.md'}")
        print("Заведите: chatman init")
    for p in check_rules_sync():
        print("ВНИМАНИЕ:", p, file=sys.stderr)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        prog="chatman",
        description=f"chatman {VERSION} — стенограммы, поиск и канон; один "
                    f"инструмент на все проекты. Руководство — в докстринге "
                    f"файла: head -110 {HOME_TOOL}",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Порядок: install (однократно) -> init (в новом проекте) -> "
               "export -> sessions -> find --prompts --grep -> find --context "
               "-> verify")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("rules", help="канон: общий (в теле) + проектный (.chatman/rules.md)")
    sub.add_parser("install", help="поставить себя в ~/.claude/tools, на PATH и в навыки")
    sub.add_parser("doctor", help="самопроверка: установка, привязка, канон, копии")
    sub.add_parser("sessions", help="реестр ВЫГРУЖЕННЫХ чатов проекта")
    sub.add_parser("repos", help="какие репозитории есть в профиле (чтение на месте)")

    i = sub.add_parser("init", help="завести проект: .chatman/rules.md и config.json")
    i.add_argument("--name", help="имя проекта (по умолчанию — имя каталога)")

    e = sub.add_parser("export", help="выгрузить СВОЮ сессию (дословно, дописыванием)")
    e.add_argument("--all-projects", action="store_true",
                   help="взять стенограммы ВСЕХ проектов (по умолчанию нет: утечка)")

    f = sub.add_parser("find", help="читать и искать по стенограммам этого проекта")
    f.add_argument("--grep", help="искать подстроку (без учёта регистра)")
    f.add_argument("--prompts", action="store_true",
                   help="только распоряжения человека (ходы и врезки)")
    f.add_argument("--user", action="store_true", help="только события с ролью user")
    f.add_argument("--session", help="сузить до сессии (можно префикс)")
    f.add_argument("--mine", action="store_true", help="только текущая сессия")
    f.add_argument("--range", nargs=2, type=int, metavar=("ОТ", "ДО"))
    f.add_argument("--context", type=int, metavar="N", help="событие N и соседние")
    f.add_argument("--around", type=int, default=2, help="сколько соседей для --context")
    f.add_argument("--at", help="префикс метки времени, например 2026-08-21T06")
    f.add_argument("--width", type=int, default=0, help="обрезать вывод (0 = целиком)")
    f.add_argument("--repo", metavar="ЧАСТЬ_ПУТИ",
                   help="искать в стенограммах ДРУГОГО репозитория из профиля")
    f.add_argument("--exported", action="store_true",
                   help="читать выгрузку chatlog/, а не профиль")
    f.add_argument("--quiet", action="store_true", help="без напоминания о правилах")

    v = sub.add_parser("verify", help="сверить дословность выгрузки по sha256")
    v.add_argument("--session", help="только эта сессия (можно префикс)")
    v.add_argument("--mine", action="store_true", help="только текущая сессия")

    s = sub.add_parser("search", help="поиск по корпусу с замером покрытия")
    s.add_argument("patterns", nargs="+")
    s.add_argument("--domain", help="где искать (по умолчанию — из config или корень)")
    s.add_argument("--step", default="nfkc,case,hyphen,space,homoglyph")
    s.add_argument("--fuzzy", type=int, default=0, metavar="d")

    a = ap.parse_args()
    return {"rules": cmd_rules, "install": cmd_install, "doctor": cmd_doctor,
            "init": cmd_init, "export": cmd_export, "sessions": cmd_sessions,
            "repos": cmd_repos, "find": cmd_find, "verify": cmd_verify,
            "search": cmd_search}[a.cmd](a)


if __name__ == "__main__":
    # Инструмент общего назначения обязан выживать в конвейере: `| head`
    # закрывает поток, и без этого Python валится трассировкой вместо
    # обычного для unix-утилиты молчаливого завершения.
    if hasattr(signal, "SIGPIPE"):
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    try:
        raise SystemExit(main())
    except BrokenPipeError:          # на платформах без SIGPIPE
        try:
            sys.stdout.close()
        finally:
            raise SystemExit(0)

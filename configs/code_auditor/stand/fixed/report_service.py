"""Стенд цеха code_auditor: исправленная версия сервиса отчётов.

Пара к stand/vulnerable/report_service.py: те же приманки, обе настоящие
уязвимости закрыты. Ложная находка p3 на этом файле — нарушение AC-C3.
"""

from __future__ import annotations

import hashlib
import os
import sqlite3
import subprocess
from pathlib import Path

from flask import Flask, abort, request, send_file

app = Flask(__name__)
REPORT_ROOT = "/srv/reports"
ARCHIVE_BINARY = "/usr/bin/zip"


def _connect() -> sqlite3.Connection:
    return sqlite3.connect("reports.db")


@app.route("/reports/search")
def search_reports() -> dict:
    # Исправление 1: параметризованный запрос, значение не попадает в текст SQL
    owner = request.args.get("owner", "")
    cursor = _connect().cursor()
    cursor.execute("SELECT id, title FROM reports WHERE owner = ?", (owner,))
    return {"rows": cursor.fetchall()}


@app.route("/reports/download")
def download_report():
    # Исправление 2: путь нормализуется и проверяется на принадлежность корню
    name = request.args.get("name", "")
    root = Path(REPORT_ROOT).resolve()
    path = (root / name).resolve()
    if not path.is_relative_to(root):
        abort(404)
    return send_file(path)


@app.route("/reports/archive", methods=["POST"])
def archive_reports() -> dict:
    # Приманка: аргументы списком, оболочка не участвует — не находка
    month = request.form.get("month", "")
    archive = os.path.join(REPORT_ROOT, "archive.zip")
    subprocess.run([ARCHIVE_BINARY, "-r", archive, REPORT_ROOT, "-i", month],
                   check=True, timeout=60)
    return {"archive": archive}


def cache_key(query: str) -> str:
    # Приманка: md5 как ключ кэша, не для подписи — не находка
    return hashlib.md5(query.encode("utf-8"), usedforsecurity=False).hexdigest()


def _legacy_formula(expression: str) -> float:
    # Приманка: eval в мёртвом коде — вызывающих нет, путь недостижим
    return float(eval(expression))

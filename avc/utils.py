from __future__ import annotations

import base64
import csv
import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd
import requests

from avc.logger import get_logger

if TYPE_CHECKING:
    from types import TracebackType
    from typing import Any, Self

    from avc.models import PyrusEntry

logger = get_logger("avc")


@dataclass(slots=True)
class Result:
    ok: bool = True
    message: str | None = None

    def __bool__(self) -> bool:
        return self.ok


def pretty_print(data: Any) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def find_project_root() -> Path:
    marker_files = ("pyproject.toml", ".git")
    path = Path.cwd()
    for parent in [path] + list(path.parents):
        if any((parent / marker).exists() for marker in marker_files):
            return parent
    raise FileNotFoundError("Project root not found")


def get_processed_tasks(robot_log_path: Path) -> list[str]:
    if not robot_log_path.exists():
        return []
    df = pd.read_csv(robot_log_path, delimiter=";", header=None)
    uploaded_tasks = list(set(list(df.loc[~df[0].isna(), 0])))
    return uploaded_tasks


def attach_network_drive(remote_path: Path) -> None:
    if remote_path.exists():
        logger.info("Network drive is already attached")
        return

    webdav_url = os.environ["WEBDAV_URL"]
    user = os.environ["WEBDAV_USER"]
    password = os.environ["WEBDAV_PASSWORD"]

    logger.info("Checking if Cloud is running")
    encoded = base64.b64encode(f"{user}:{password}".encode("utf-8")).decode(
        "utf-8"
    )
    headers = {"Authorization": f"Basic {encoded}"}
    response = requests.head(
        webdav_url,
        headers=headers,
    )
    status_code = response.status_code
    if not (status_code >= 200 and status_code < 300):
        raise RuntimeError(
            f"{webdav_url!r} is not accessible with a code {status_code!r}"
        )
    logger.info(f"Status code: {status_code}")

    logger.info("Attaching network folder")

    args = [
        "net",
        "use",
        "N:",
        webdav_url,
        f"/user:{user}",
        f'"{password}"',
        "/persistent:yes",
    ]
    res = subprocess.run(
        args,
        capture_output=True,
        text=True,
    )

    logger.info(f"Command line: {' '.join(args)!r}")
    logger.info(f"Stdout: {res.stdout.strip()!r}")
    logger.info(f"Stderr: {res.stderr.strip()!r}")

    if not remote_path.exists():
        raise RuntimeError(f"Not accessible: {remote_path.as_posix()!r}")


class LogWriter:
    def __init__(self, file_path: Path) -> None:
        self.file_path: Path = file_path
        self.file_path.parent.mkdir(exist_ok=True, parents=True)

        self.headers: list[str] = [
            "Ссылка",
            "№ проекта",
            "Инициатор",
            "Контрагент",
            "БИН/ИИН контрагента",
            "Плательщик",
            "Банк",
            "Сумма",
            "Валюта",
            "Дата счета на оплату",
            "Желаемая дата оплаты",
            "Путь",
            "Найдено в Pyrus",
            "Загружено в Pyrus",
            "Перенесено в сетевую папку",
            "Заметки",
        ]

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        _: type[BaseException] | None,
        __: BaseException | None,
        ___: TracebackType | None,
    ) -> bool:
        if self.file_path.exists():
            df = pd.read_csv(self.file_path, sep=";", header=None)
            df = df.drop_duplicates()
            df.to_csv(
                self.file_path,
                sep=";",
                index=False,
                header=False,
                encoding="utf-8",
            )
            df.to_excel(
                self.file_path.with_suffix(".xlsx"),
                index=False,
                header=self.headers,
            )
        return False

    def append_record(
        self,
        pdf_file_path: Path,
        note: str,
        entry: PyrusEntry | None = None,
        found_in_pyrus: bool = False,
        uploaded_to_pyrus: bool = False,
        moved_file: bool = False,
    ) -> None:
        url = f"https://pyrus.com/t#id{entry.task_id}" if entry else ""
        row = [
            url,
            entry.project_id if entry else "",
            entry.initiator_name if entry else "",
            entry.contragent if entry else "",
            entry.contragent_bin if entry else "",
            entry.payer if entry else "",
            entry.bank if entry else "",
            entry.amount if entry else "",
            entry.currency if entry else "",
            entry.invoice_date if entry else "",
            entry.desired_date if entry else "",
            pdf_file_path,
            "Да" if found_in_pyrus else "Нет",
            "Да" if uploaded_to_pyrus else "Нет",
            "Да" if moved_file else "Нет",
            note,
        ]

        with open(self.file_path, "a", encoding="utf-8") as f:
            writer = csv.writer(f, delimiter=";")
            writer.writerow(row)

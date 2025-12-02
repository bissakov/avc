from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from dotenv import load_dotenv

from avc.logger import get_logger
from avc.models import CONTRAGENT_CATALOG
from avc.pdf_parser import extract_payment_order
from avc.pyrus_client import Credentials, get_active_entries
from avc.pyrus_selenium import PyrusWebClient
from avc.utils import (
    LogWriter,
    Result,
    find_project_root,
    get_processed_tasks,
)

if TYPE_CHECKING:
    from collections.abc import Generator

    from avc.models import PyrusEntry
    from avc.pdf_parser import PaymentOrder


load_dotenv()


logger = get_logger("avc")


def pay_files_iter(
    remote_path: Path, data_files_folder: Path
) -> Generator[tuple[Path, Path]]:
    for item in remote_path.iterdir():
        name = item.name
        if not (item.is_dir() and name[0].isdigit()):
            continue

        for network_file_path in item.glob("*.pdf"):
            folder = data_files_folder / network_file_path.parent.name
            folder.mkdir(exist_ok=True, parents=True)
            local_file_path = folder / network_file_path.name
            shutil.copy2(network_file_path, local_file_path)
            yield network_file_path, local_file_path


import os
from pathlib import Path


def find_project_manual(projects_parent_path: Path, project_id: str, max_depth: int = 10) -> Path | None:
    def _search_recursive(current_path: str, depth: int = 0) -> Path | None:
        if depth > max_depth:
            return None
        # print(f"Current depth: {depth}")

        try:
            with os.scandir(current_path) as entries:
                for entry in entries:
                    if not entry.is_dir(follow_symlinks=False):
                        continue

                    if project_id in entry.name:
                        return Path(entry.path)

                    result = _search_recursive(entry.path, depth + 1)
                    if result:
                        return result
        except (OSError, PermissionError):
            pass

        return None

    return _search_recursive(str(projects_parent_path))



def resolve_network_paths(
    order: PaymentOrder, project_id: str, contragent: str, year: str
) -> tuple[Path | None, Result]:
    projects_parent_path = Path(CONTRAGENT_CATALOG[order.payer]["folder_path"])
    if not projects_parent_path.name:
        logger.error(
            f"Payer's {order.payer!r} folder not found in 'N:/Общие диски'"
        )
        return None, Result(
            ok=False,
            message=f"Не найдена папка для плательщика {order.payer!r} в 'N:/Общие диски'",
        )

    try:
        project_id_year = str(int(project_id[-2::]) + 2000)
    except Exception as e:
        logger.error(f"Не удалось получить год из номера проекта: {project_id}")
        logger.error(e)
        logger.exception(e)
        return None, Result(
            ok=False,
            message=f"Не удалось получить год из номера проекта: {project_id}",
        )

    projects_parent_path = projects_parent_path / project_id_year
    if not projects_parent_path.exists():
        return None, Result(
            ok=False,
            message=f"Не найдена папка года {year} для плательщика {order.payer!r} в {projects_parent_path.as_posix()!r}",
        )

    # try:
    #     project_path = next(
    #         (x for x in projects_parent_path.rglob(f"*{project_id}*")), None
    #     )
    # except OSError as e:
    #     logger.error(e)
    #     project_path = find_project_manual(projects_parent_path, project_id, max_depth=2)

    project_path = find_project_manual(projects_parent_path, project_id, max_depth=2)

    if not project_path:
        # project_path = projects_parent_path / project_id
        # supplier_path = project_path / "3. Поставщик"

        logger.info(
            f"Project {project_id!r} folder in {project_path!r} not found"
        )

        return None, Result(
            ok=False,
            message=f"Не найдена папка проекта {project_id} для плательщика {order.payer!r} в {projects_parent_path.as_posix()!r}",
        )
    else:
        logger.info(f"Found folder: {project_path!r}")
        supplier_path = next(
            (
                x
                for x in project_path.rglob("*поставщик*", case_sensitive=False)
            ),
            None,
        )
        if not supplier_path:
            logger.info(
                f"Поставщик folder in {project_path!r} does not exist."
            )
            return None, Result(
                ok=False,
                message=f"Не найдена папка поставщика для плательщика {order.payer!r} в {project_path.as_posix()!r}",
            )
        else:
            logger.info(f"Found folder: {supplier_path!r}")

    payment_order_folder = next(
        (x for x in supplier_path.iterdir() if order.iin in x.name.lower()),
        None,
    )

    if not payment_order_folder:
        contragent = contragent.replace('"', "")

        result_folder = (
            supplier_path
            / f"{contragent}, {order.iin}"
            / "Финансовые документы"
        )
        logger.info(f"Folder not found. Creating it instead {result_folder.as_posix()!r}")
        result_folder.mkdir(exist_ok=True, parents=True)
    else:
        logger.info(f"Folder found. Attempting to find 'Финансовые документы' in {payment_order_folder.as_posix()!r}")
        result_folder = next(
            (x for x in payment_order_folder.iterdir() if "фин" in x.name.lower()),
            None,
        )
        if not result_folder:
            logger.info(
                f"Финансовые документы folder in {payment_order_folder.as_posix()!r} does not exist. Creating instead"
            )
            result_folder = payment_order_folder / "Финансовые документы"
            result_folder.mkdir(exist_ok=True, parents=True)

    return result_folder, Result()


def find_entry(
    entries: list[PyrusEntry], order: PaymentOrder
) -> tuple[PyrusEntry | None, str | None]:
    found_entries: list[PyrusEntry] = []
    for entry in entries:
        if entry.payer != order.payer:
            continue
        contragent_bin = entry.contragent_bin or entry.contragent_bin2
        found = contragent_bin == order.iin and entry.amount == order.amount
        if found:
            found_entries.append(entry)

    message = None
    if len(found_entries) > 1:
        logger.info("Attempting to narrow down the search...")
        candidates = ", ".join(
            [f"https://pyrus.com/t#id{e.task_id}" for e in found_entries]
        )
        message = (
            "Невозможно определить задачу для вложения платежного поручения. "
            f"Возможные кандидаты: {candidates}"
        )
        found_entries = [
            e
            for e in found_entries
            if e.account_id and e.account_id in order.payment_purpose
        ]

    logger.info(f"Found count: {len(found_entries)}")
    if not found_entries:
        return None, message

    found_entry = found_entries[0]
    return found_entry, None


def process_payment_file(
    local_file_path: Path,
    network_file_path: Path,
    client: PyrusWebClient,
    entries: list[PyrusEntry],
    log_writer: LogWriter,
    now: datetime,
    processed_tasks: list[str],
) -> Result:
    order = extract_payment_order(local_file_path, now)

    if not order:
        note = f"Не удалось извлечь данные из {network_file_path.as_posix()!r}"
        logger.warning(
            f"Payment order has not been extracted: {network_file_path.as_posix()!r}"
        )
        log_writer.append_record(pdf_file_path=network_file_path, note=note)
        return Result(ok=False, message=note)
    logger.info(f"Extracted order: {order!r}")

    entry, message = find_entry(entries, order)
    if not entry:
        note = "Не удалось найти задачу в Pyrus для платежного поручения"
        if message:
            note += " " + message
        logger.error(note)
        log_writer.append_record(pdf_file_path=network_file_path, note=note)
        return Result(ok=False, message=note)
    logger.info(f"Found entry: {entry!r}")

    url = f"https://pyrus.com/t#id{entry.task_id}"
    logger.info(f"Found entry: {url}")
    if url in processed_tasks:
        logger.info("Previously uploaded task, skipping")
        return Result()

    # # TODO: Use only when testing
    # log_writer.append_record(
    #     pdf_file_path=network_file_path,
    #     entry=entry,
    #     found_in_pyrus=True,
    #     uploaded_to_pyrus=False,
    #     moved_file=True,
    #     note="Успех",
    # )
    # return Result()

    note = client.upload_file(
        task_id=entry.task_id,
        file_path=local_file_path,
    )

    if not entry.project_id:
        note = f"{note or ''}Задача без № проекта. Конечный путь для переноса файла неизвестен"
        logger.error(note)
        log_writer.append_record(
            pdf_file_path=network_file_path,
            entry=entry,
            note=note,
            found_in_pyrus=True,
            uploaded_to_pyrus=True,
        )
        return Result(ok=False, message=note)

    payment_order_folder, result = resolve_network_paths(
        order,
        project_id=entry.project_id,
        contragent=entry.contragent or order.benificiary,
        year=str(now.year)
    )
    if not result:
        note = (
            result.message
            or "Не найдена папка для плательщика {order.payer!r} в 'N:/Общие диски'"
        )
        logger.error(note)
        log_writer.append_record(
            pdf_file_path=network_file_path,
            entry=entry,
            note=note,
            found_in_pyrus=True,
            uploaded_to_pyrus=True,
        )
        return Result(ok=False, message=note)

    assert payment_order_folder, "payment_order_folder is None"

    logger.info(
        f"Attempting to move {network_file_path.name!r} to {payment_order_folder.as_posix()!r}"
    )
    dst_path = payment_order_folder / network_file_path.name
    shutil.move(network_file_path, dst_path)
    logger.info(f"File moved: {dst_path.as_posix()!r}")

    log_writer.append_record(
        pdf_file_path=dst_path,
        entry=entry,
        found_in_pyrus=True,
        uploaded_to_pyrus=True if not note else False,
        moved_file=True,
        note=note or "Успех",
    )

    return Result()


def run(project_folder: Path | None = None) -> None:
    logger.info("Starting AVC robot...")

    remote_path = Path(os.environ["REMOTE_PATH"]) / "F. Платежи"
    logger.info(f"Using remote path: {remote_path.as_posix()!r}")
    if not remote_path.exists():
        logger.error("Network drive is not attached")
        return

    if not project_folder:
        project_folder = find_project_root()

    # now = datetime(2025, 10, 31)
    now = datetime.now()

    resources_folder = project_folder / "resources"
    data_folder = project_folder / "data"
    data_folder.mkdir(exist_ok=True)
    driver_path = resources_folder / "chromedriver.exe"
    chrome_path = resources_folder / "chrome-win64" / "chrome.exe"
    data_files_folder = (
        data_folder / "files" / now.strftime("%Y-%m") / now.strftime("%d-%m-%Y")
    )
    data_files_folder.mkdir(exist_ok=True, parents=True)
    robot_log_path = (
        data_folder
        / "logs"
        / now.strftime("%Y-%m")
        / f"{now.strftime('%Y.%m.%d')}.csv"
    )

    processed_tasks = get_processed_tasks(robot_log_path)

    creds = Credentials(
        email=os.environ["PYRUS_EMAIL"],
        password=os.environ["PYRUS_PASSWORD"],
        person_id=int(os.environ["PYRUS_PERSON_ID"]),
    )
    logger.info(f"Using Pyrus account: {creds.email!r}")

    client = PyrusWebClient(driver_path=driver_path, chrome_path=chrome_path)
    log_writer = LogWriter(robot_log_path)

    entries = get_active_entries(creds=creds)

    with client, log_writer:
        client.login()

        for idx, (network_file_path, local_file_path) in enumerate(
            pay_files_iter(remote_path, data_files_folder)
        ):
            logger.info(
                f"#{idx:02} processing file: {local_file_path.as_posix()!r}"
            )
            result = process_payment_file(
                local_file_path=local_file_path,
                network_file_path=network_file_path,
                client=client,
                entries=entries,
                log_writer=log_writer,
                now=now,
                processed_tasks=processed_tasks,
            )
            logger.info(f"Result: {result!r}")


if __name__ == "__main__":
    run()

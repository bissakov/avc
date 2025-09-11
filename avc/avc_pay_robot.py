from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from dotenv import load_dotenv

from avc.logger import get_logger
from avc.models import CONTRAGENT_CATALOG
from avc.pdf_parser import extract_payment_order
from avc.pyrus_client import Credentials, get_active_entries
from avc.pyrus_selenium import PyrusWebClient
from avc.utils import find_project_root

if TYPE_CHECKING:
    from collections.abc import Generator

    from avc.models import PyrusEntry
    from avc.pdf_parser import PaymentOrder


load_dotenv()


logger = get_logger("avc")


@dataclass(slots=True)
class Result:
    ok: bool = True
    message: str | None = None

    def __bool__(self) -> bool:
        return self.ok


def pay_files_iter(remote_path: Path) -> Generator[Path]:
    for item in remote_path.iterdir():
        name = item.name
        if not (item.is_dir() and name[0].isdigit()):
            continue

        for file in item.glob("*.pdf"):
            days_old = (
                datetime.now() - datetime.fromtimestamp(file.stat().st_mtime)
            ).days
            if days_old > 7:
                continue
            yield file


def resolve_network_paths(
    order: PaymentOrder, project_id: str, contragent: str
) -> tuple[Path | None, Result]:
    projects_parent_path = Path(CONTRAGENT_CATALOG[order.payer]["folder_path"])
    if not projects_parent_path.name:
        logger.error(f"Payer's {order.payer!r} folder not found in 'N:/Общие диски'")
        return None, Result(
            ok=False,
            message=f"Не найдена папка для плательщика {order.payer!r} в 'N:/Общие диски'",
        )

    project_path = next(
        (x for x in projects_parent_path.rglob(f"*{project_id}*")), None
    )
    if not project_path:
        project_path = projects_parent_path / project_id
        supplier_path = project_path / "3. Поставщик"

        logger.info(
            f"Folders {(project_path, supplier_path)!r} do not exist. Creating it instead..."
        )

        project_path.mkdir(exist_ok=True, parents=True)
        supplier_path.mkdir(exist_ok=True, parents=True)
    else:
        logger.info(f"Found folder: {project_path!r}")
        supplier_path = next(
            (x for x in project_path.rglob("*поставщик*", case_sensitive=False)),
            None,
        )
        if not supplier_path:
            supplier_path = project_path / "3. Поставщик"
            logger.info(
                f"Folder {supplier_path!r} does not exist. Creating it instead..."
            )
            supplier_path.mkdir(exist_ok=True, parents=True)
        else:
            logger.info(f"Found folder: {supplier_path!r}")

    payment_order_folder = next(
        (x for x in supplier_path.iterdir() if order.iin in x.name),
        None,
    )

    if not payment_order_folder:
        contragent = contragent.replace('"', "")
        payment_order_folder = (
            supplier_path / f"{contragent}, {order.iin}" / "Финансовые документы"
        )
        payment_order_folder.mkdir(exist_ok=True, parents=True)

    return payment_order_folder, Result()


def find_entry(entries: list[PyrusEntry], order: PaymentOrder) -> PyrusEntry | None:
    found_entries: list[PyrusEntry] = []
    for entry in entries:
        found = (
            entry.payer == order.payer
            and entry.contragent_bin == order.iin
            and entry.amount == order.amount
        )
        if found:
            found_entries.append(entry)

    if len(found_entries) > 1:
        logger.info("Attempting to narrow down the search...")
        found_entries = [
            e
            for e in found_entries
            if e.account_id and e.account_id in order.payment_purpose
        ]

    logger.info(f"Found count: {len(found_entries)}")
    if not found_entries:
        return None

    found_entry = found_entries[0]
    return found_entry


def process_payment_file(
    file_path: Path, client: PyrusWebClient, entries: list[PyrusEntry]
) -> Result:
    order = extract_payment_order(file_path)

    if not order:
        note = f"Не удалось извлечь данные из {file_path.as_posix()!r}"
        logger.warning(
            f"Payment order has not been extracted: {file_path.as_posix()!r}"
        )
        return Result(ok=False, message=note)
    logger.info(f"Extracted order: {order!r}")

    entry = find_entry(entries, order)
    if not entry:
        note = "Не удалось найти задачу в Pyrus для платежного поручения"
        logger.error(note)
        return Result(ok=False, message=note)
    logger.info(f"Found entry: {entry!r}")

    url = f"https://pyrus.com/t#id{entry.task_id}"
    logger.info(f"Found entry: {url}")

    _ = client.upload_file(
        task_id=entry.task_id,
        file_path=file_path,
    )

    if not entry.project_id:
        note = "Задача без № проекта. Конечный путь для переноса файла неизвестен"
        logger.error(note)
        return Result(ok=False, message=note)

    payment_order_folder, result = resolve_network_paths(
        order,
        project_id=entry.project_id,
        contragent=entry.contragent or order.benificiary,
    )
    if not result:
        note = (
            result.message
            or "Не найдена папка для плательщика {order.payer!r} в 'N:/Общие диски'"
        )
        logger.error(note)
        return Result(ok=False, message=note)

    assert payment_order_folder, "payment_order_folder is None"

    logger.info(
        f"Attempting to move {file_path.name!r} to {payment_order_folder.as_posix()!r}"
    )
    dst_path = payment_order_folder / file_path.name
    shutil.copy(file_path, dst_path)
    logger.info(f"File moved: {dst_path.as_posix()!r}")

    return Result()


def run(project_folder: Path | None = None) -> None:
    if not project_folder:
        project_folder = find_project_root()

    resources_folder = project_folder / "resources"
    driver_path = resources_folder / "chromedriver.exe"
    chrome_path = resources_folder / "chrome-win64" / "chrome.exe"

    logger.info("Starting AVC robot...")

    creds = Credentials(
        email=os.environ["PYRUS_EMAIL"],
        password=os.environ["PYRUS_PASSWORD"],
        person_id=int(os.environ["PYRUS_PERSON_ID"]),
    )
    logger.info(f"Using Pyrus account: {creds.email!r}")

    remote_path = Path(os.environ["REMOTE_PATH"]) / "F. Платежи"
    logger.info(f"Using remote path: {remote_path.as_posix()!r}")

    client = PyrusWebClient(driver_path=driver_path, chrome_path=chrome_path)

    entries = get_active_entries(creds=creds)

    # with open("entries.json", "r", encoding="utf-8") as f:
    #     data: DataT = json.load(f)
    # req_entries = data.get("Forms", [])
    # logger.info(f"Found {len(req_entries)} entries")
    # persons = data["ScopeCache"]["Persons"]

    # TODO: Logging to a file

    with client:
        client.login()

        for idx, file_path in enumerate(pay_files_iter(remote_path)):
            logger.info(f"Processing file #{idx:02}: {file_path.as_posix()!r}")
            result = process_payment_file(
                file_path=file_path, client=client, entries=entries
            )
            logger.info(f"Result: {result!r}")


if __name__ == "__main__":
    run()

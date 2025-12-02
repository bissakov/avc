from __future__ import annotations

import re
from datetime import datetime
from difflib import get_close_matches
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple

import pdfplumber

from avc.logger import get_logger
from avc.models import CONTRAGENT_CATALOG

if TYPE_CHECKING:
    from collections.abc import Generator

    Tables = list[list[list[str | None]]]

logger = get_logger("avc")


RE_WHITESPACE = re.compile(r"\s+")
RE_IIN = re.compile(r"\b\d{12}\b")


class PaymentOrder(NamedTuple):
    days_old: int
    payer: str
    benificiary: str
    amount: float
    value_date: datetime
    iin: str
    payment_purpose: str


def clean_cell(text: str) -> str:
    if not text:
        return ""
    text = text.replace("\n", " ")
    text = RE_WHITESPACE.sub(" ", text).strip()
    return text


def cells_iter(table: list[list[str | None]]) -> Generator[str]:
    for row in table:
        for cell in row:
            if not cell:
                continue
            cell = clean_cell(cell)
            yield cell


def get_cell(tables: Tables, t_idx: int, r_idx: int, c_idx: int) -> str:
    if 0 <= t_idx < len(tables):
        table = tables[t_idx]
        if 0 <= r_idx < len(table):
            row = table[r_idx]
            if 0 <= c_idx < len(row):
                return row[c_idx] or ""
    return ""


def str_to_float(s: str) -> float:
    return float(s.replace(",", ".").replace(" ", ""))


def normalize(name: str) -> str:
    return (
        name.replace('"', "")
        .replace("ТОО", "")
        .replace(".", "")
        .strip()
        .lower()
    )


def match_payer(payer: str) -> str:
    logger.debug(f"Matching payer: {payer!r}")

    norm_payer = normalize(payer)
    norm_contragents = {normalize(c): c for c in CONTRAGENT_CATALOG.keys()}

    matches = get_close_matches(
        norm_payer, norm_contragents.keys(), n=1, cutoff=0.6
    )
    if matches:
        res = norm_contragents[matches[0]]
        logger.debug(f"Matched payer: {res!r}")
        return res
    logger.error(f"Contragent match not found for payer: {payer!r}")
    raise ValueError("Contragent match not found")


def process_halyk_bank(
    tables: Tables,
) -> tuple[str, str, float, datetime, str, str]:
    logger.debug("Detected 'Народный Банк' format")

    payer = get_cell(tables, 0, 0, 0)
    if not payer:
        raise ValueError("Payer cell 0-0-0 not found")
    payer = RE_WHITESPACE.sub(" ", payer).split(":")[-1].strip()

    benificiary = get_cell(tables, 1, 0, 0)
    if not benificiary:
        raise ValueError("Beneficiary cell 1-0-0 not found")
    benificiary = RE_WHITESPACE.sub(" ", benificiary).split(":")[-1].strip()

    amount_str = get_cell(tables, 0, 3, 0)
    if not amount_str:
        raise ValueError("Amount cell 0-3-0 not found")
    amount_str = (
        items[1] if len((items := amount_str.split("\n"))) > 1 else items[0]
    )
    amount = str_to_float(amount_str)

    value_date_str = get_cell(tables, 0, 1, 1)
    if not value_date_str:
        raise ValueError("Value date cell 0-1-1 not found")

    value_date_str = (
        items[1] if len((items := value_date_str.split("\n"))) > 1 else items[0]
    )
    value_date = datetime.strptime(value_date_str, "%d.%m.%Y")

    iin = get_cell(tables, 1, 1, 0)
    if not iin:
        raise ValueError("IIN cell 1-1-0 not found")
    iin_match = RE_IIN.search(iin)
    if not iin_match:
        raise ValueError("IIN not found by regex search")
    iin = iin_match.group(0)

    payment_purpose = get_cell(tables, 3, 0, 0)
    if not payment_purpose:
        payment_purpose = get_cell(tables, 2, 0, 0)
        if not payment_purpose:
            raise ValueError("payment_purpose cell 3-0-0 or 2-0-0 not found")
    try:
        payment_purpose = payment_purpose.split("\n", maxsplit=1)[1].strip()
    except IndexError:
        payment_purpose = ""

    return payer, benificiary, amount, value_date, iin, payment_purpose


def process_bereke_bank(
    tables: Tables,
) -> tuple[str, str, float, datetime, str, str]:
    logger.debug("Detected 'Bereke Bank' format")

    payer = get_cell(tables, 0, 0, 0)
    if not payer:
        raise ValueError("Payer cell 0-0-0 not found")
    payer = payer.split("Отправитель денег\n", maxsplit=1)[-1].split(
        "\nИИН", maxsplit=1
    )[0]

    benificiary = get_cell(tables, 0, 0, 0)
    if not benificiary:
        raise ValueError("Benificiary cell 0-0-0 not found")
    benificiary = benificiary.split("Бенефициар\n", maxsplit=1)[-1].split(
        "\nИИН", maxsplit=1
    )[0]
    benificiary = benificiary.replace("\n", " ")

    amount_str = get_cell(tables, 1, 0, 2)
    if not amount_str:
        raise ValueError("Amount cell 1-0-2 not found")
    amount_str = amount_str.split("\n")[1]
    amount = str_to_float(amount_str)

    try:
        value_date_str = get_cell(tables, 0, 3, 2)
        if not value_date_str:
            raise ValueError("Value date cell 0-3-2 not found")
        value_date = datetime.strptime(value_date_str, "%d.%m.%Y")
    except ValueError:
        value_date_str = get_cell(tables, 0, 3, 3)
        if not value_date_str:
            raise ValueError("Value date cell 0-3-2 not found")
        value_date = datetime.strptime(value_date_str, "%d.%m.%Y")

    row = get_cell(tables, 0, 0, 0)
    if not row:
        raise ValueError("IIN cell 0-0-0 not found")
    benificiary_idx = row.find("Бенефициар")
    row = row[benificiary_idx::]
    iin_match = RE_IIN.search(row)
    if not iin_match:
        raise ValueError("IIN not found by regex search")
    iin = iin_match.group(0)

    payment_purpose = get_cell(tables, 0, 1, 0)
    if not payment_purpose:
        raise ValueError("IIN cell 0-1-0 not found")
    payment_purpose = payment_purpose.split("\n", maxsplit=1)[1].strip()

    return payer, benificiary, amount, value_date, iin, payment_purpose


def process_swift_bank(
    tables: Tables,
) -> tuple[str, str, float, datetime, str, str]:
    logger.debug("Detected 'Swift' format")

    payer = get_cell(tables, 0, 0, 0)
    if not payer:
        raise ValueError("Payer cell 0-0-0 not found")
    payer = payer.split("Отправитель денег:\n", maxsplit=1)[-1].split(
        ",", maxsplit=1
    )[0]
    payer = payer.replace(" RESPUBLIKA KAZAKHSTAN", "")

    benificiary = get_cell(tables, 2, 0, 0)
    if not benificiary:
        raise ValueError("Benificiary cell 2-0-0 not found")
    benificiary = benificiary.split("Бенефициар:\n", maxsplit=1)[-1]

    amount_str = get_cell(tables, 1, 1, 1)
    if not amount_str:
        raise ValueError("Amount cell 1-1-1 not found")
    amount_str = amount_str.split("Сумма:\n", maxsplit=1)[-1]
    amount = str_to_float(amount_str)

    value_date_str = get_cell(tables, 0, 2, 2)
    if not value_date_str:
        raise ValueError("Value date cell 0-2-2 not found")
    value_date_str = value_date_str.split("\n")[1]
    value_date = datetime.strptime(value_date_str, "%d.%m.%Y")

    iin = get_cell(tables, 2, 1, 1)
    if not iin:
        raise ValueError("IIN cell 2-1-1 not found")
    iin = iin.split("БИН: ", maxsplit=1)[-1]

    payment_purpose = get_cell(tables, 4, 0, 0)
    if not payment_purpose:
        raise ValueError("IIN cell 4-0-0 not found")
    payment_purpose = payment_purpose.split("\n", maxsplit=1)[1].strip()

    return payer, benificiary, amount, value_date, iin, payment_purpose


def extract_payment_order(file: Path, now: datetime) -> PaymentOrder | None:
    logger.debug(f"Extracting payment order from file: {file.as_posix()!r}")

    benificiary = None
    amount = None
    value_date = None
    iin = None
    payer = None
    payment_purpose = None

    with pdfplumber.open(file) as pdf:
        page = pdf.pages[0]
        tables = page.extract_tables()

        try:
            if "Народный" in get_cell(tables, 0, 2, 0):
                payer, benificiary, amount, value_date, iin, payment_purpose = (
                    process_halyk_bank(tables)
                )
            elif "Bereke" in get_cell(tables, 0, 0, 0):
                payer, benificiary, amount, value_date, iin, payment_purpose = (
                    process_bereke_bank(tables)
                )
            elif "SWIFT" in tables[1][0][-1]:
                payer, benificiary, amount, value_date, iin, payment_purpose = (
                    process_swift_bank(tables)
                )
            else:
                return None
        except Exception as e:
            logger.error(e)
            logger.exception(e)
            return None

    if not benificiary or not amount or not value_date or not iin or not payer:
        logger.error(
            f"Failed to extract one of the values: {benificiary=!r}, {amount=!r}, {value_date=!r}, {iin=!r}, {payer=!r}"
        )
        raise ValueError("One of the values is unset")

    payer = match_payer(payer)
    logger.debug(f"Final matched payer: {payer!r}")

    value_date = value_date.replace(hour=5)
    logger.debug(f"Normalized value date: {value_date!r}")

    days_old = (now - datetime.fromtimestamp(file.stat().st_mtime)).days

    order = PaymentOrder(
        payer=payer,
        benificiary=benificiary,
        amount=amount,
        value_date=value_date,
        iin=iin,
        days_old=days_old,
        payment_purpose=payment_purpose,
    )
    logger.debug(f"Extracted order: {order!r}")

    return order

from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, NamedTuple, cast

import requests

from avc.logger import get_logger
from avc.models import (
    FIELD_COLUMN_MAPPING,
    MAX_ITEM_COUNT,
    PayloadBuilder,
    PyrusEntry,
)

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Any

    from avc.models import PyrusPayload
    from avc.my_types.misc import ParsedEntry
    from avc.my_types.payload import (
        DataT,
        PersonT,
        PyrusAmountFieldT,
        PyrusDateFieldT,
        PyrusEntryT,
        PyrusItemsFieldT,
        PyrusStrValuesFieldT,
        PyrusTextFieldT,
        PyrusValueFieldT,
    )
    from avc.pdf_parser import PaymentOrder


logger = get_logger("avc")


class Credentials(NamedTuple):
    email: str
    password: str
    person_id: int


def get_active_entries(creds: Credentials) -> list[PyrusEntry]:
    with requests.Session() as session:
        pyrus_login(session, creds)
        logger.info("Pyrus login successful")

        builder = PayloadBuilder()
        payload = (
            builder.stage("5").active_only(True).max_item_count(1000).resolve()
        )
        data = get_entry_data(session, payload)

    persons = data["ScopeCache"]["Persons"]
    logger.info(f"Found {len(persons)} persons")

    entries = [
        parse_entry(req_entry=req_entry, persons=persons)
        for req_entry in data.get("Forms", [])
    ]
    logger.info(f"Found {len(entries)} entries")

    with open(
        f"data/entries/entries_{int(datetime.now().timestamp())}.json",
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(data, f, ensure_ascii=False)
    return entries


def parse_entry(req_entry: PyrusEntryT, persons: list[PersonT]) -> PyrusEntry:
    tmp: dict[str, Any] = {}
    task_id = req_entry["TaskId"]

    for field in req_entry["Fields"]:
        fid = field.get("FieldId")

        if fid == 55:
            field = cast("PyrusTextFieldT", field)
            tmp["Этап"] = field["Text"]
        elif fid == 157:
            field = cast("PyrusTextFieldT", field)
            tmp["№ счета на оплату"] = field["Text"]
        elif fid == 45:
            field = cast("PyrusTextFieldT", field)
            tmp["Краткое описание"] = field["Text"]
        elif fid == 5:
            field = cast("PyrusValueFieldT", field)
            tmp["Инициатор ID"] = field["Value"]
        elif fid == 48:
            field = cast("PyrusAmountFieldT", field)
            tmp["Сумма"] = field["Amount"]
        elif fid == 3:
            field = cast("PyrusItemsFieldT", field)
            tmp["Плательщик"] = field["Items"][0]["Values"][0]
        elif fid == 7:
            field = cast("PyrusItemsFieldT", field)
            tmp["Группа платежей"] = field["Items"][0]["Values"][0]
        elif fid == 47:
            field = cast("PyrusItemsFieldT", field)
            tmp["Назначение платежа"] = field["Items"][0]["Values"][2]
        elif fid == 90:
            field = cast("PyrusItemsFieldT", field)
            tmp["КБК"] = field["Items"][0]["Values"][1]
        elif fid == 59:
            field = cast("PyrusDateFieldT", field)
            pyrus_ts = field["Date"]
            ts = int(pyrus_ts[6:-2]) / 1000
            dt = datetime.fromtimestamp(ts)
            tmp["Дата счета на оплату"] = dt
        elif fid == 116:
            field = cast("PyrusDateFieldT", field)
            pyrus_ts = field["Date"]
            ts = int(pyrus_ts[6:-2]) / 1000
            dt = datetime.fromtimestamp(ts)
            tmp["Желаемая дата оплаты"] = dt
        else:
            if fid in FIELD_COLUMN_MAPPING:
                field = cast("PyrusItemsFieldT", field)
                items = field["Items"]
                items = cast("list[PyrusStrValuesFieldT]", items)
                values = items[0]["Values"]

                for value, column in zip(values, FIELD_COLUMN_MAPPING[fid]):
                    if column in tmp or not value:
                        continue
                    tmp[column] = value
    data = cast("ParsedEntry", cast(object, tmp))

    initiator_id = data["Инициатор ID"]
    for person in persons:
        if not (
            person["Id"] == initiator_id
            or person.get("ManagerId") == initiator_id
        ):
            continue
        first_name = person.get("FirstName", person.get("AltFirstName"))
        last_name = person.get("LastName", person.get("AltLastName"))
        if first_name and last_name:
            initiator_name = f"{first_name} {last_name}"
        elif first_name and not last_name:
            initiator_name = first_name
        elif not first_name and last_name:
            initiator_name = last_name
        else:
            initiator_name = None

        data["Инициатор"] = initiator_name
        break

    entry = PyrusEntry(
        task_id=task_id,
        stage=data["Этап"],
        project_id=data.get("Номер Проекта"),
        initiator_id=initiator_id,
        initiator_name=data["Инициатор"],
        contragent=data.get("Контрагент"),
        contragent_bin=data.get("БИН/ИИН"),
        payer=data["Плательщик"],
        payment_group=data.get("Группа платежей"),
        payment_purpose=data.get("Назначение платежа"),
        kbk=data.get("КБК"),
        kbe=data.get("КБе"),
        country=data.get("Страна резидентства"),
        email=data.get("Почта"),
        phone_number=data.get("Телефон"),
        account_number=data.get("Номер счета"),
        bank=data.get("Банк"),
        bik=data.get("БИК"),
        amount=data.get("Сумма"),
        currency=data.get("Валюта"),
        invoice_date=data.get("Дата счета на оплату"),
        desired_date=data.get("Желаемая дата оплаты"),
        contract_info=data.get("Наименование договора"),
        description=data.get("Краткое описание"),
        account_id=data.get("№ счета на оплату"),
    )
    return entry


def pyrus_login(session: requests.Session, creds: Credentials) -> None:
    json_data = {
        "Email": creds.email,
        "Region": 0,
        "PersonId": creds.person_id,
        "Password": creds.password,
        "Language": "ru-RU",
    }
    logger.debug(f"Pyrus login with data: {json_data!r}")

    response = session.post(
        "https://accounts.pyrus.com/auth/check-pwd", json=json_data
    )
    logger.debug(f"Pyrus login response: {response.status_code!r}")
    response.raise_for_status()


def get_entry_data(session: requests.Session, payload: PyrusPayload) -> DataT:
    payload_json = payload.to_dict()
    logger.debug(f"Getting entry list with payload: {payload_json!r}")

    response = session.post(
        "https://pyrus.com/Services/ClientServiceV2.svc/GetForms",
        json=payload_json,
    )
    logger.debug(f"Get entry list response: {response.status_code!r}")

    response.raise_for_status()

    content = response.content.decode("utf-8-sig")
    data = json.loads(content)
    data: DataT = data.get("d", {})
    return data


def get_entries(
    session: requests.Session, payload: PyrusPayload
) -> list[PyrusEntryT]:
    data = get_entry_data(session, payload)
    entries = data.get("Forms", [])
    return entries


def find_entry(
    session: requests.Session, order: PaymentOrder
) -> PyrusEntryT | None:
    builder = PayloadBuilder()

    payload = (
        builder.stage("5")
        .payer_id(order.payer)
        .dt_range(
            order.value_date - timedelta(days=7),
            order.value_date,
        )
        .amount(order.amount)
        .resolve()
    )
    entries = get_entries(session, payload)
    logger.debug(f"{builder!r}")
    logger.info(f"Found {len(entries)} entries")

    if 1 < len(entries) <= MAX_ITEM_COUNT:
        builder.reset()
        payload = (
            builder.stage("5")
            .payer_id(order.payer)
            .dt_range(
                order.value_date - timedelta(days=7),
                order.value_date,
            )
            .amount(order.amount)
            .iin(order.iin)
            .resolve()
        )
        entries = get_entries(session, payload)
        logger.debug(f"{builder!r}")
        logger.info(f"Found {len(entries)} entries")

        if 1 < len(entries) <= MAX_ITEM_COUNT:
            builder.reset()
            payload = (
                builder.stage("5")
                .payer_id(order.payer)
                .dt_range(
                    order.value_date - timedelta(days=7),
                    order.value_date,
                )
                .amount(order.amount)
                .contragent_iin(order.iin)
                .resolve()
            )
            entries = get_entries(session, payload)
            logger.debug(f"{builder!r}")
            logger.info(f"Found {len(entries)} entries")

    return None if not entries else entries[0]


def upload_payment_order(session: requests.Session, file_path: Path) -> str:
    params = {
        "asdefault": "false",
    }
    with file_path.open("rb") as f:
        files = {
            "file0": (file_path.name, f, "application/pdf"),
        }
        response = session.post(
            "https://files.pyrus.com/services/upload/0.0/upload",
            params=params,
            files=files,
        )
        response.raise_for_status()
        data = response.json()
        guid = data.get("guid")
    return guid


person_cache_sign: str = "cWXxSgAAAACxwxEAfFwQAHyVDAD3rwwAwjMJAAh8EQAWshIAg5MNAE4pCQBR6Q0AflwQAOGPCQAp+wsAoZsLAA2lDgBk5Q4APAELAApDEgCRQg8AHmsSAFuCCwAr+wsAlJsLADfOEQAXpAkATa0LAIibCwAYKgsAqj8MAL10CAD5GBIAxBgNAGJ7EgBoNQoA56sOAJWbCwD6Xg8A2WwNAAsUEADnjgwAZTIJAAkUEAByqQ4A+4sMAMTGCwCHmwsANoENAIbGEgDeqA8AMKoPADN3CAAhaxIA6c0SAI2bCwBfeQgA0J0QAD3EEgBnRhAALBQQAJ6OEgDDjxIAKKoPACRmDwCPjBEAuHcSAM9sEACPxBAASxQQAH48EgB/PBIAOMwRAFIUEACupA4A0F0MAIBODAAfFBAAgP4MAHOpDgCa2xEA2YUNACV3CABQFBAAvyINABsUEABOeQgAIpkJAAB6CgAvqg8AF3cIAAd4EAAXFBAA0VgLAJYaEgDV+xEACBQQAPgzCgBheQgATBQQAMM7EQDoExAADBQQAEcUEAAeFBAAuj8MAO1eDwArFBAANqoPACAUEAAqlhAA8l4PAEoUEAAiFBAAGhQQAA0UEAAhFBAANaoPABgUEAAlFBAA46gPAPzHCQAqFBAAKRQQAEgUEAAyqg8ANKoPACcUEAA3qg8AK6oPADGqDwDqZw8AChQQABQUEAAdFBAAKmYPANflEgBt5RIAbOUSANbeEgDo2xIA2doSACHXEgDN1hIA2s0SAOnMEgCnzBIAn8wSAA7IEgD6xxIA98cSAPbHEgCExhIAwbQSAFS0EgDPrhIAjawSAHOqEgBuqhIAiJ0SAIadEgCLmRIAfpkSAKGXEgDelRIAl5USAHeTEgAejxIARYsSAFyIEgD7hhIARIYSADWGEgAyhhIAjIQSAEiBEgDrgBIAbYASAEV8EgAXdxIAUW8SADRuEgBIVRIAJlQSAA=="
compact_form_cache_sign: str = "EDvxSgAAAADWThQAUpcWAA=="


def save_task(
    session: requests.Session, task_id: int, guid: str, file_name: str
) -> None:
    json_data = {
        "req": {
            "Params": {
                "TaskId": task_id,
                "Form": {
                    "TemplateId": 1330902,
                    "Fields": [
                        {
                            "__type": "FormFieldFiles:http://schemas.datacontract.org/2004/07/Papirus.BackEnd.Forms",
                            "FieldId": 113,
                            "NewFiles": [
                                {
                                    "Type": 0,
                                    "Guid": guid,
                                    "Name": file_name,
                                    "status": 6,
                                },
                            ],
                            "ExistingFiles": [],
                        },
                    ],
                },
                "RemovedApprovalIdsBySteps": [
                    [],
                    [],
                    [],
                    [],
                    [],
                ],
                "RerequestedApprovalIdsBySteps": [
                    [],
                    [],
                    [],
                    [],
                    [],
                ],
                "AddedApprovalIdsBySteps": [
                    [],
                    [],
                    [],
                    [],
                    [],
                ],
            },
            "TaskId": task_id,
            "ClientId": "a10242ce-0b84-42ec-8976-1347c625d28d",
            "PersonCacheSign": person_cache_sign,
            "ProjectCacheSign": "AAAAAAAAAAA=",
            "CompactFormCacheSign": compact_form_cache_sign,
            "Locale": 1,
            "ApiSign": "4O//9y0ncN5e+gQ=",
            "TimeZoneSpan": 300,
            "SkipCounters": False,
            "AccountId": 1164209,
            "PersonProjectStamp": "|=1.1258525036|",
        },
    }
    response = session.post(
        "https://pyrus.com/Services/ClientServiceV2.svc/AddTaskComment",
        json=json_data,
    )
    response.raise_for_status()
    # content = response.content.decode("utf-8-sig")
    # data = json.loads(content)
    # print(json.dumps(data, ensure_ascii=False, indent=2))

    json_data = {
        "req": {
            "TaskId": task_id,
            "TakeQueueOnSteps": None,
            "IncludeSimilarTasksNotes": False,
            "IsAutomatic": True,
            "PersonCacheSign": person_cache_sign,
            "ProjectCacheSign": "AAAAAAAAAAA=",
            "CompactFormCacheSign": compact_form_cache_sign,
            "Locale": 1,
            "ApiSign": "4O//9y0ncN5e+gQ=",
            "TimeZoneSpan": 300,
            "SkipCounters": False,
            "AccountId": 1164209,
            "SkipPersonProjects": True,
        },
    }

    response = session.post(
        "https://pyrus.com/Services/ClientServiceV2.svc/GetTask",
        json=json_data,
    )
    response.raise_for_status()


def approve_task(session: requests.Session, task_id: int) -> None:
    json_data = {
        "req": {
            "Params": {
                "TaskId": task_id,
                "ApproveType": 1,
                "Category": 0,
                "CloseType": 1,
                "Form": {
                    "TemplateId": 1330902,
                    "Fields": [],
                },
                "RemovedApprovalIdsBySteps": [
                    [],
                    [],
                    [],
                    [],
                    [],
                ],
                "RerequestedApprovalIdsBySteps": [
                    [],
                    [],
                    [],
                    [],
                    [],
                ],
                "AddedApprovalIdsBySteps": [
                    [],
                    [],
                    [],
                    [],
                    [],
                ],
            },
            "TaskId": task_id,
            "ClientId": "1d8ec835-3587-4e81-93f0-bf0690c025a6",
            "PersonCacheSign": person_cache_sign,
            "ProjectCacheSign": "AAAAAAAAAAA=",
            "CompactFormCacheSign": compact_form_cache_sign,
            "Locale": 1,
            "ApiSign": "4O//9y0ncN5e+gQ=",
            "TimeZoneSpan": 300,
            "SkipCounters": False,
            "AccountId": 1164209,
            "PersonProjectStamp": "|=1.1258525036|",
        },
    }
    response = session.post(
        "https://pyrus.com/Services/ClientServiceV2.svc/AddTaskComment",
        json=json_data,
    )
    response.raise_for_status()

    # content = response.content.decode("utf-8-sig")
    # data = json.loads(content)
    # print(json.dumps(data, ensure_ascii=False, indent=2))

    json_data = {
        "req": {
            "TaskId": task_id,
            "TakeQueueOnSteps": None,
            "IncludeSimilarTasksNotes": False,
            "IsAutomatic": True,
            "PersonCacheSign": person_cache_sign,
            "ProjectCacheSign": "AAAAAAAAAAA=",
            "CompactFormCacheSign": "eJADSwAAAADWThQAUpcWAA==",
            "Locale": 1,
            "ApiSign": "4O//9y0ncN5e+gQ=",
            "TimeZoneSpan": 300,
            "SkipCounters": False,
            "AccountId": 1164209,
            "SkipPersonProjects": True,
        },
    }

    response = session.post(
        "https://pyrus.com/Services/ClientServiceV2.svc/GetTask",
        json=json_data,
    )
    response.raise_for_status()

import logging as log
import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, NamedTuple

import requests
from dotenv import load_dotenv

from avc.models import PayloadBuilder
from avc.pyrus_client import (
    Credentials,
    get_contract_id,
    get_entry_data,
    parse_entry,
    pyrus_login,
)

load_dotenv()


def run() -> None:
    creds = Credentials(
        email=os.environ["PYRUS_EMAIL"],
        password=os.environ["PYRUS_PASSWORD"],
        person_id=int(os.environ["PYRUS_PERSON_ID"]),
    )

    with requests.Session() as session:
        pyrus_login(session, creds)
        log.info("Pyrus login successful")

        contract_id = get_contract_id(
            session, contragent_bin="960129450142", contract_number="24-141 "
        )
        print(contract_id)

        if not contract_id:
            raise Exception()

        builder = PayloadBuilder()
        payload = (
            builder.active_only(False)
            .max_item_count(1)
            .contract(contract_id)
            .resolve()
        )
        data = get_entry_data(session, payload)

    persons = data["ScopeCache"]["Persons"]
    log.info(f"Found {len(persons)} persons")

    entry = parse_entry(req_entry=data.get("Forms", [])[0], persons=persons)

    print(entry)


if __name__ == "__main__":
    run()

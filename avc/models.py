from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, NamedTuple, override

if TYPE_CHECKING:
    from datetime import datetime
    from typing import Any, Self

    from avc.my_types.misc import ContragentCatalogItem
    from avc.my_types.payload import (
        CatalogItemT,
        CatalogValueT,
        DateValueT,
        MoneyValueT,
        PyrusFilterT,
        PyrusPayloadInnerT,
        PyrusPayloadT,
        TextValueT,
        ValueT,
    )


MAX_ITEM_COUNT = 50


CONTRAGENT_CATALOG: dict[str, "ContragentCatalogItem"] = {
    'ТОО "AVC Group"': {
        "payer_id": 109941218,
        "folder_path": r"N:\Общие диски\02. AVC Group\01. Проекты AVCG",
    },
    'ТОО "AVC Production"': {
        "payer_id": 109941219,
        "folder_path": r"N:\Общие диски\03. AVC Production\01. Проекты AVCP",
    },
    'ТОО "AVC Групп"': {
        "payer_id": 109941220,
        "folder_path": r"N:\Общие диски\01. AVC Групп\01. Проекты AVCГ",
    },
    'ТОО "Примус Групп"': {
        "payer_id": 109941221,
        "folder_path": r"N:\Общие диски\04. Примус Групп\01. Проекты PR",
    },
    'ТОО "ГринТехСнаб"': {
        "payer_id": 109941222,
        "folder_path": r"N:\Общие диски\05. ГринТехСнаб\01. Проекты ГТС",
    },
    'ТОО "ЭОН Энерго"': {
        "payer_id": 109941224,
        "folder_path": r"N:\Общие диски\06. ЭОН Энерго\01. Проекты EON",
    },
    'ТОО "CES Kazakhstan"': {
        "payer_id": 109941225,
        "folder_path": r"N:\Общие диски\07. CES\01. Проекты CES",
    },
    'ТОО "C-NRG (Синерджи)"': {
        "payer_id": 109941226,
        "folder_path": r"N:\Общие диски\09. C-NRG\01. Проекты C-NRG",
    },
    'ТОО "VC Services"': {
        "payer_id": 109941227,
        "folder_path": r"N:\Общие диски\08. VC Services\01. Проекты VC Services",
    },
    'ТОО "Digital Enterprise"': {
        "payer_id": 109941228,
        "folder_path": r"N:\Общие диски\10. DE\01. Проекты DE",
    },
    'ТОО "First Service"': {
        "payer_id": 121842770,
        "folder_path": r"N:\Общие диски\11. First Service\01. Проекты FS",
    },
    'ТОО "First Delivery"': {
        "payer_id": 121842772,
        "folder_path": r"N:\Общие диски\12. First Delivery\01. Проекты FD",
    },
    'ТОО "Стройтэкс KZ"': {
        "payer_id": 128047636,
        "folder_path": r"N:\Общие диски\14. Стройтэкс\01. Проекты",
    },
    "ТОО AVC Group. Филиал г. Атырау": {
        "payer_id": 109941223,
        "folder_path": r"N:\Общие диски\02. AVC Group\01. Проекты AVCG",
    },
    "Прочие": {"payer_id": 121893841, "folder_path": ""},
    'Частный фонд "Благотворительный фонд AVC"': {
        "payer_id": 158618409,
        "folder_path": "",
    },
    'ТОО "SK Trans Logistics"': {"payer_id": 159105559, "folder_path": ""},
    'ТОО "Refoil"': {
        "payer_id": 163661023,
        "folder_path": r"N:\Общие диски\13. Refoil\01. Проекты",
    },
    'ТОО "Veiron (Вейрон)"': {"payer_id": 165612864, "folder_path": ""},
    'ТОО "ДЖС Аналитикс Казахстан"': {"payer_id": 166533221, "folder_path": ""},
    'ТОО "Top Chemicals"': {"payer_id": 167153910, "folder_path": ""},
    'ТОО "Private Security"': {"payer_id": 168822146, "folder_path": ""},
    "ТОО СИСТЕМОТЕХНИКА": {"payer_id": 168822147, "folder_path": ""},
}

CURATOR_MAPPING = {
    'ТОО "AVC Групп"': "Куралай Куанова",
    'ТОО "AVC Group"': "Самал Жаманкулова",
    'ТОО "AVC Production"': "Салтанат Дарханкызы",
    'ТОО "CES Kazakhstan"': "Бухгалтерия 07",
    'ТОО "ЭОН Энерго"': "Айжан Байбусинова",
    'ТОО "Примус Групп"': "Жанар Джангалиева",
    'ТОО "ГринТехСнаб"': "Жанар Джангалиева",
    'ТОО "VC Services"': "Раушан Лекерова",
    'ТОО "C-NRG (Синерджи)"': "Самал Жаманкулова",
    'ТОО "Digital Enterprise"': "Бухгалтерия 10",
    'ТОО "First Service"': "Раушан Лекерова",
    'ТОО "First Delivery"': "Раушан Лекерова",
    'ТОО "Refoil"': "Айжан Байбусинова",
    'ТОО "Стройтэкс KZ"': "Айжан Байбусинова",
    'ТОО "Veiron (Вейрон)"': "Зарина Баширова",
    "Keremet Property": "Раушан Лекерова",
    'ТОО "ДЖС Аналитикс Казахстан"': "Зарина Баширова",
    'ТОО "Top Chemicals"': "Зарина Баширова",
    'ТОО "Private Security"': "Раушан Лекерова",
    "ТОО СИСТЕМОТЕХНИКА": "Айжан Байбусинова",
}

FIELD_COLUMN_MAPPING = {
    10: [
        "№",
        "Номер Проекта",
        "Старый номер",
        "Компания исполнитель",
        "Статус",
        "Автор проекта",
        "Бухгалтер",
        "Наименование проекта",
        "Заказчик проекта",
        "Кладовщик",
        "Куратор проекта",
    ],
    28: [
        "№",
        "Код",
        "Контрагент",
        "БИН/ИИН",
        "КБе",
        "Страна резидентства",
        "Назначение платежа",
        "Почта",
        "Телефон",
    ],
    30: [
        "№",
        "Код",
        "Контрагент",
        "БИН/ИИН",
        "Основной счет",
        "Номер счета",
        "Банк",
        "БИК",
    ],
    39: [
        "№",
        "Код",
        "Контрагент",
        "БИН/ИИН",
        "Наименование договора",
    ],
    96: ["№", "Валюта", "Группа платежей"],
}


@dataclass
class TextValue:
    field_id: int
    text: str
    type: str = "FormFieldString:http://schemas.datacontract.org/2004/07/Papirus.BackEnd.Forms"

    def to_dict(self) -> TextValueT:
        return {
            "__type": self.type,
            "FieldId": self.field_id,
            "Text": self.text,
        }


@dataclass
class CatalogItem:
    id: int

    def to_dict(self) -> CatalogItemT:
        return {"Id": self.id}


@dataclass
class CatalogValue:
    field_id: int
    items: list[CatalogItem] = field(default_factory=list)
    type: str = "FormFieldCatalogItem:http://schemas.datacontract.org/2004/07/Papirus.BackEnd.Forms"

    def to_dict(self) -> CatalogValueT:
        return {
            "__type": self.type,
            "FieldId": self.field_id,
            "Items": [it.to_dict() for it in self.items],
        }


@dataclass
class MoneyValue:
    field_id: int
    amount: float | int
    type: str = "FormFieldMoney:http://schemas.datacontract.org/2004/07/Papirus.BackEnd.Forms"

    def to_dict(self) -> MoneyValueT:
        return {
            "__type": self.type,
            "FieldId": self.field_id,
            "Amount": self.amount,
        }


@dataclass
class DateValue:
    field_id: int
    dt: str
    type: str = "FormFieldDate:http://schemas.datacontract.org/2004/07/Papirus.BackEnd.Forms"

    def to_dict(self) -> DateValueT:
        return {"__type": self.type, "FieldId": self.field_id, "Date": self.dt}


Value = TextValue | MoneyValue | DateValue | CatalogValue


@dataclass
class PyrusFilter:
    field_id: int
    operator_id: int
    values: list[Value] = field(default_factory=list)

    def to_dict(self) -> PyrusFilterT:
        serialized_values: list[ValueT] = []
        for v in self.values:
            serialized_values.append(v.to_dict())
        return {
            "FieldId": self.field_id,
            "OperatorId": self.operator_id,
            "Values": serialized_values,
        }


@dataclass
class PyrusPayloadInner:
    project_id: int = 1330902
    template_id: int = 1330902
    active_only: bool = False
    max_item_count: int = MAX_ITEM_COUNT
    filters: list[PyrusFilter] = field(default_factory=list)
    timezone_span: int = 300
    sort_mode: int = 0
    with_register_settings: bool = True
    person_cache_sign: str = "cWXxSgAAAACxwxEAfFwQAHyVDAD3rwwAwjMJAAh8EQAWshIAg5MNAE4pCQBR6Q0AflwQAOGPCQAp+wsAoZsLAA2lDgBk5Q4APAELAApDEgCRQg8AHmsSAFuCCwAr+wsAlJsLADfOEQAXpAkATa0LAIibCwAYKgsAqj8MAL10CAD5GBIAxBgNAGJ7EgBoNQoA56sOAJWbCwD6Xg8A2WwNAAsUEADnjgwAZTIJAAkUEAByqQ4A+4sMAMTGCwCHmwsANoENAIbGEgDeqA8AMKoPADN3CAAhaxIA6c0SAI2bCwBfeQgA0J0QAD3EEgBnRhAALBQQAJ6OEgDDjxIAKKoPACRmDwCPjBEAuHcSAM9sEACPxBAASxQQAH48EgB/PBIAOMwRAFIUEACupA4A0F0MAIBODAAfFBAAgP4MAHOpDgCa2xEA2YUNACV3CABQFBAAvyINABsUEABOeQgAIpkJAAB6CgAvqg8AF3cIAAd4EAAXFBAA0VgLAJYaEgDV+xEACBQQAPgzCgBheQgATBQQAMM7EQDoExAADBQQAEcUEAAeFBAAuj8MAO1eDwArFBAANqoPACAUEAAqlhAA8l4PAEoUEAAiFBAAGhQQAA0UEAAhFBAANaoPABgUEAAlFBAA46gPAPzHCQAqFBAAKRQQAEgUEAAyqg8ANKoPACcUEAA3qg8AK6oPADGqDwDqZw8AChQQABQUEAAdFBAAKmYPANflEgBt5RIAbOUSANbeEgDo2xIA2doSACHXEgDN1hIA2s0SAOnMEgCnzBIAn8wSAA7IEgD6xxIA98cSAPbHEgCExhIAwbQSAFS0EgDPrhIAjawSAHOqEgBuqhIAiJ0SAIadEgCLmRIAfpkSAKGXEgDelRIAl5USAHeTEgAejxIARYsSAFyIEgD7hhIARIYSADWGEgAyhhIAjIQSAEiBEgDrgBIAbYASAEV8EgAXdxIAUW8SADRuEgBIVRIAJlQSAA=="
    project_cache_sign: str = "AAAAAAAAAAA="
    compact_form_cache_sign: str = "EDvxSgAAAADWThQAUpcWAA=="
    locale: int = 1
    api_sign: str = "4O//9y0ncN5e+gQ="
    skip_counters: bool = True
    account_id: int = 1164209
    person_project_stamp: str = "|=1.1257323280|"

    def to_dict(self) -> PyrusPayloadInnerT:
        return {
            "ProjectId": self.project_id,
            "TemplateId": self.template_id,
            "ActiveOnly": self.active_only,
            "MaxItemCount": self.max_item_count,
            "Filters": [f.to_dict() for f in self.filters],
            "TimeZoneSpan": self.timezone_span,
            "SortMode": self.sort_mode,
            "WithRegisterSettings": self.with_register_settings,
            "PersonCacheSign": self.person_cache_sign,
            "ProjectCacheSign": self.project_cache_sign,
            "CompactFormCacheSign": self.compact_form_cache_sign,
            "Locale": self.locale,
            "ApiSign": self.api_sign,
            "SkipCounters": self.skip_counters,
            "AccountId": self.account_id,
            "PersonProjectStamp": self.person_project_stamp,
        }


@dataclass
class PyrusPayload:
    req: PyrusPayloadInner = field(default_factory=PyrusPayloadInner)

    def to_dict(self) -> PyrusPayloadT:
        return {"req": self.req.to_dict()}


class PayloadBuilder:
    def __init__(self):
        self._active_only: bool = True
        self._max_item_count: int = MAX_ITEM_COUNT
        self._filters: list[PyrusFilter] = []

        self.repr: str = "PayloadBuilder("

    def reset(self) -> None:
        self._active_only = True
        self._max_item_count = 5
        self._filters.clear()

    def max_item_count(self, max_item_count: int) -> Self:
        self._max_item_count = max_item_count
        self.repr += f"max_item_count={max_item_count!r}, "
        return self

    def active_only(self, active_only: bool) -> Self:
        self._active_only = active_only
        self.repr += f"active_only={active_only!r}, "
        return self

    def stage(self, stage: str) -> Self:
        self._filters.append(
            PyrusFilter(
                field_id=55,
                operator_id=4,
                values=[TextValue(field_id=55, text=stage)],
            )
        )
        self.repr += f"stage={stage!r}, "
        return self

    def iin(self, iin: str) -> Self:
        self._filters.append(
            PyrusFilter(
                field_id=29,
                operator_id=6,
                values=[TextValue(field_id=29, text=iin)],
            )
        )
        self.repr += f"iin={iin!r}, "
        return self

    def contragent_iin(self, iin: str) -> Self:
        self._filters.append(
            PyrusFilter(
                field_id=27,
                operator_id=6,
                values=[TextValue(field_id=27, text=iin)],
            )
        )
        self.repr += f"contragent_iin={iin!r}, "
        return self

    def amount(self, amount: float) -> Self:
        if amount.is_integer():
            amount = int(amount)
        self._filters.append(
            PyrusFilter(
                field_id=48,
                operator_id=1,
                values=[MoneyValue(field_id=48, amount=amount)],
            )
        )
        self.repr += f"amount={amount!r}, "
        return self

    def payer_id(self, payer: str) -> Self:
        payer_id = CONTRAGENT_CATALOG[payer]["payer_id"]
        self._filters.append(
            PyrusFilter(
                field_id=3,
                operator_id=4,
                values=[
                    CatalogValue(field_id=3, items=[CatalogItem(id=payer_id)])
                ],
            )
        )
        self.repr += f"payer_id={payer_id!r} ({payer!r}), "
        return self

    def dt(self, dt: datetime) -> Self:
        ts = int(dt.timestamp() * 1000)
        pyrus_ts = f"/Date({ts})/"
        value = DateValue(field_id=116, dt=pyrus_ts)

        self._filters.append(
            PyrusFilter(
                field_id=116,
                operator_id=5,
                values=[value, value],
            )
        )
        self.repr += f"dt={dt.isoformat()!r}, "
        return self

    def dt_range(self, from_dt: datetime, to_dt: datetime) -> Self:
        from_ts = int(from_dt.timestamp() * 1000)
        to_ts = int(to_dt.timestamp() * 1000)

        self._filters.append(
            PyrusFilter(
                field_id=116,
                operator_id=5,
                values=[
                    DateValue(field_id=116, dt=f"/Date({from_ts})/"),
                    DateValue(field_id=116, dt=f"/Date({to_ts})/"),
                ],
            )
        )
        self.repr += (
            f"dt_range=({from_dt.isoformat()!r}, {to_dt.isoformat()!r}), "
        )
        return self

    def contract(self, contract_id: int) -> Self:
        self._filters.append(
            PyrusFilter(
                field_id=39,
                operator_id=4,
                values=[
                    CatalogValue(
                        field_id=39, items=[CatalogItem(id=contract_id)]
                    )
                ],
            )
        )
        self.repr += f"contract_id={contract_id!r}, "
        return self

    @override
    def __repr__(self) -> str:
        return self.repr.rstrip(", ") + ")"

    def resolve(self) -> PyrusPayload:
        payload = PyrusPayload(
            req=PyrusPayloadInner(
                active_only=self._active_only,
                max_item_count=self._max_item_count,
                filters=list(self._filters),
            )
        )
        return payload


class PyrusEntry(NamedTuple):
    task_id: int
    stage: str
    project_id: str | None
    initiator_id: int
    initiator_name: str | None
    contragent: str | None
    contragent_bin: str | None
    contragent2: str | None
    contragent_bin2: str | None
    payer: str
    payment_group: str | None
    payment_purpose: str | None
    kbk: str | None
    kbe: str | None
    country: str | None
    email: str | None
    phone_number: str | None
    account_number: str | None
    bank: str | None
    bik: str | None
    amount: float | None
    currency: str | None
    invoice_date: datetime | None
    desired_date: datetime | None
    contract_info: str
    description: str
    account_id: str


@dataclass(slots=True)
class OrderLog:
    url: str | None = None
    project_id: str | None = None
    initiator_name: str | None = None
    contragent: str | None = None
    contragent_bin: str | None = None
    payer: str | None = None
    bank: str | None = None
    amount: float | None = None
    currency: str | None = None
    invoice_date: str | None = None
    desired_date: str | None = None
    file_path: str | None = None
    found_pyrus: bool = False
    uploaded_pyrus: bool = False
    moved_file: bool = False
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "Ссылка": self.url,
            "№ проекта": self.project_id,
            "Инициатор": self.initiator_name,
            "Контрагент": self.contragent,
            "БИН/ИИН контрагента": self.contragent_bin,
            "Плательщик": self.payer,
            "Банк": self.bank,
            "Сумма": self.amount,
            "Валюта": self.currency,
            "Дата счета на оплату": self.invoice_date,
            "Желаемая дата оплаты": self.desired_date,
            "Путь": self.file_path,
            "Найдено в Pyrus": "Да" if self.found_pyrus else "Нет",
            "Загружено в Pyrus": "Да" if self.uploaded_pyrus else "Нет",
            "Перенесено в сетевую папку": "Да" if self.moved_file else "Нет",
            "Заметки": self.note,
        }

from datetime import datetime
from typing import TypedDict


class ContragentCatalogItem(TypedDict):
    payer_id: int
    folder_path: str


ParsedEntry = TypedDict(
    "ParsedEntry",
    {
        "Этап": str,
        "Инициатор ID": int,
        "Инициатор": str | None,
        "Плательщик": str,
        "Группа платежей": str,
        "Назначение платежа": str,
        "КБК": str,
        "Сумма": float,
        "Дата счета на оплату": datetime,
        "Желаемая дата оплаты": datetime,
        "№": str,
        "Номер Проекта": str,
        "Компания исполнитель": str,
        "Статус": str,
        "Автор проекта": str,
        "Бухгалтер": str,
        "Наименование проекта": str,
        "Заказчик проекта": str,
        "Кладовщик": str,
        "Куратор проекта": str,
        "Код": str,
        "Контрагент": str,
        "БИН/ИИН": str,
        "Контрагент2": str,
        "БИН/ИИН2": str,
        "КБе": str,
        "Страна резидентства": str,
        "Почта": str,
        "Телефон": str,
        "Основной счет": str,
        "Номер счета": str,
        "Банк": str,
        "БИК": str,
        "Наименование договора": str,
        "Валюта": str,
        "№ счета на оплату": str,
        "Краткое описание": str,
    },
)

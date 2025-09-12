from __future__ import annotations

import os
from time import sleep
from typing import TYPE_CHECKING

from pywinauto import Application
from pywinauto.mouse import move
from selenium.common.exceptions import WebDriverException
from selenium.webdriver import ActionChains, Chrome, ChromeOptions, Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait

from avc.logger import get_logger

if TYPE_CHECKING:
    from pathlib import Path
    from types import TracebackType
    from typing import Self

    from selenium.webdriver.chrome.webdriver import WebDriver
    from pywinauto import WindowSpecification

logger = get_logger("avc")


def get_center(element: WindowSpecification) -> tuple[int, int]:
    rect = element.rectangle()
    center = rect.mid_point()
    return center.x, center.y


class PyrusWebClient:
    def __init__(
        self, driver_path: Path | str, chrome_path: Path | str
    ) -> None:
        self.driver_path: str = str(driver_path)
        self.chrome_path: str = str(chrome_path)

        self._driver: WebDriver | None = None
        self._wait: WebDriverWait[WebDriver] | None = None
        self._actions: ActionChains | None = None
        self._app: Application | None = None
        self._win: WindowSpecification | None = None

    @property
    def driver(self) -> WebDriver:
        if self._driver:
            return self._driver

        service = Service(executable_path=self.driver_path)
        options = ChromeOptions()
        options.binary_location = self.chrome_path
        prefs = {"profile.default_content_setting_values.notifications": 2}
        options.add_experimental_option("prefs", prefs)
        options.add_argument("--start-maximized")
        options.add_experimental_option("excludeSwitches", ["enable-logging"])
        options.add_argument("--log-level=3")
        options.add_argument("--force-renderer-accessibility")
        self._driver = Chrome(service=service, options=options)
        return self._driver

    @property
    def wait(self) -> WebDriverWait[WebDriver]:
        if self._wait:
            return self._wait
        self._wait = WebDriverWait(self.driver, 10)
        return self._wait

    @property
    def actions(self) -> ActionChains:
        if self._actions:
            return self._actions
        self._actions = ActionChains(self.driver)
        return self._actions

    @property
    def app(self) -> Application:
        if self._app:
           return self._app
        self._app = Application(backend="uia").connect(title_re="Заявка.+")
        return self._app

    @property
    def win(self) -> WindowSpecification:
        if self._win:
            return self._win
        self._win = self.app.window(title_re="Заявка.+")
        return self._win

    def login(self) -> None:
        login_url = os.environ["PYRUS_LOGIN_URL"]
        email = os.environ["PYRUS_EMAIL"]
        password = os.environ["PYRUS_PASSWORD"]

        self.driver.get(login_url)
        login_field = self.wait.until(
            ec.element_to_be_clickable((By.ID, "p_email"))
        )
        login_field.send_keys(email)
        continue_btn = self.wait.until(
            ec.element_to_be_clickable(
                (By.CSS_SELECTOR, 'button[data-test-id="submitEmailButton"]')
            )
        )
        continue_btn.click()
        password_field = self.wait.until(
            ec.element_to_be_clickable(
                (By.CSS_SELECTOR, 'input[data-test-id="inputPassword"]')
            )
        )
        password_field.send_keys(password)
        self.actions.pause(1).send_keys(Keys.ENTER).pause(3).perform()

    def upload_file(
        self,
        task_id: int,
        file_path: Path,
    ) -> bool:
        url = f"https://pyrus.com/t#id{task_id}"
        self.driver.get(url)

        form_expanded = False
        while not form_expanded:
            match = self.driver.find_elements(
                By.CSS_SELECTOR, ".sideBySideRightContent"
            )
            if not match:
                sleep(.5)
                continue
            sidebar = match[0]
            class_names = str(sidebar.get_property("className")) or ""
            form_expanded = "sideBySideRightContent_expanded" in class_names
            if form_expanded:
                break
            self.actions.send_keys("f").perform()

        self.wait.until(
            ec.presence_of_element_located(
                (
                    By.XPATH,
                    "(//span[text() = '5. Вложение платежного поручения']//ancestor::div[2])[1]//div[text() = 'Загрузить файл']/following::input[1]",
                )
            )
        ).send_keys(str(file_path))

        # sleep(1)
        #
        # try:
        #     save_btn = self.driver.find_element(
        #         By.CSS_SELECTOR,
        #         "#layout > div > div.sideBySideRightContent.sideBySideRightContent_expanded > div > div.sideBySideSubheader > div.sideBySideSubheader__topSection > div > button.button.sideBySideDecision__button.sideBySideDecision__button_simple.button_theme_green > span",
        #     )
        #     save_btn.click()
        # except Exception as e:
        #     logger.error(e)
        #     raise e
        #
        #
        # sleep(5)
        #
        # try:
        #     approve_btn = self.driver.find_element(
        #         By.CSS_SELECTOR,
        #         "#layout > div > div.sideBySideRightContent.sideBySideRightContent_expanded > div > div.sideBySideSubheader > div.sideBySideSubheader__topSection > div > div > div > div.sideBySideDecision__decision.sideBySideDecision__decision_dropdown > div.sideBySideDecision__button.sideBySideDecision__button_basic.sideBySideDecision__button_approve > div.sideBySideDecision__buttonTitle.sideBySideDecision__buttonTitle_active",
        #     )
        # except Exception as e:
        #     logger.error(e)
        #     raise e
        #
        # self.actions.move_to_element(approve_btn).pause(1).click().perform()

        self.win.set_focus()
        save_btn = self.win.child_window(title="Сохранить", control_type="Text")
        save_btn.click_input()
        logger.info(f"Task {task_id} saved")

        sleep(1)

        approve_btn = self.win.child_window(title="Утвердить", control_type="Text")
        move(coords=get_center(approve_btn))
        approve_btn.click_input()
        logger.info(f"Task {task_id} approved")

        sleep(5)

        return True

    def is_driver_running(self) -> bool:
        try:
            self.driver.title
            return True
        except WebDriverException:
            return False

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        _: type[BaseException] | None,
        __: BaseException | None,
        ___: TracebackType | None,
    ) -> bool:
        if self._driver:
            self._driver.quit()
            self._driver = None
        if self._actions:
            self._actions = None
        if self._wait:
            self._wait = None
        return False


def driver_init(driver_path: Path, chrome_path: Path) -> WebDriver:
    service = Service(executable_path=str(driver_path))
    options = ChromeOptions()
    options.binary_location = str(chrome_path)
    prefs = {"profile.default_content_setting_values.notifications": 2}
    options.add_experimental_option("prefs", prefs)
    options.add_argument("--start-maximized")
    options.add_experimental_option("excludeSwitches", ["enable-logging"])
    options.add_argument("--log-level=3")

    driver = Chrome(service=service, options=options)
    return driver


def pyrus_login_selenium(
    driver: WebDriver,
    wait: WebDriverWait[WebDriver],
    actions: ActionChains,
    login_url: str,
    email: str,
    password: str,
) -> None:
    driver.get(login_url)
    login_field = wait.until(ec.element_to_be_clickable((By.ID, "p_email")))
    login_field.send_keys(email)
    continue_btn = wait.until(
        ec.element_to_be_clickable(
            (By.CSS_SELECTOR, 'button[data-test-id="submitEmailButton"]')
        )
    )
    continue_btn.click()
    password_field = wait.until(
        ec.element_to_be_clickable(
            (By.CSS_SELECTOR, 'input[data-test-id="inputPassword"]')
        )
    )
    password_field.send_keys(password)
    actions.pause(1).send_keys(Keys.ENTER).pause(5).perform()


def pyrus_upload_file(
    driver: WebDriver,
    wait: WebDriverWait[WebDriver],
    actions: ActionChains,
    task_id: int,
    file_path: Path,
) -> bool:
    url = f"https://pyrus.com/t#id{task_id}"
    driver.get(url)

    sleep(5)

    form_expanded = False
    while not form_expanded:
        sidebar = driver.find_element(
            By.CSS_SELECTOR, ".sideBySideRightContent"
        )
        class_names = str(sidebar.get_property("className")) or ""
        form_expanded = "sideBySideRightContent_expanded" in class_names
        if form_expanded:
            break
        actions.send_keys("f").perform()

    wait.until(
        ec.presence_of_element_located(
            (
                By.XPATH,
                "(//span[text() = '5. Вложение платежного поручения']//ancestor::div[2])[1]//div[text() = 'Загрузить файл']/following::input[1]",
            )
        )
    ).send_keys(str(file_path))

    sleep(1)

    try:
        save_btn = driver.find_element(
            By.CSS_SELECTOR,
            "#layout > div > div.sideBySideRightContent.sideBySideRightContent_expanded > div > div.sideBySideSubheader > div.sideBySideSubheader__topSection > div > button.button.sideBySideDecision__button.sideBySideDecision__button_simple.button_theme_green > span",
        )
        save_btn.click()
    except Exception as e:
        logger.error(e)
        raise e

    logger.info(f"Task {task_id} saved")

    sleep(5)

    try:
        approve_btn = driver.find_element(
            By.CSS_SELECTOR,
            "#layout > div > div.sideBySideRightContent.sideBySideRightContent_expanded > div > div.sideBySideSubheader > div.sideBySideSubheader__topSection > div > div > div > div.sideBySideDecision__decision.sideBySideDecision__decision_dropdown > div.sideBySideDecision__button.sideBySideDecision__button_basic.sideBySideDecision__button_approve > div.sideBySideDecision__buttonTitle.sideBySideDecision__buttonTitle_active",
        )
    except Exception as e:
        logger.error(e)
        raise e

    actions.move_to_element(approve_btn).pause(1).click().perform()

    logger.info(f"Task {task_id} approved")

    return True


# https://pyrus.com/t#rg1330902?ao=true&tz=300&tst55=5&fo=false&sm=0&fd=false

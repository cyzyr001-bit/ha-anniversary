"""纪念日集成配置流程。"""
from __future__ import annotations

from datetime import date
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from . import lunar
from .calc import parse_date
from .const import (
    CALENDAR_LUNAR,
    CALENDAR_OPTIONS,
    CALENDAR_SOLAR,
    CONF_CALENDAR,
    CONF_DATE,
    CONF_DAY,
    CONF_DISPLAY_MODE,
    CONF_IS_LEAP_MONTH,
    CONF_MONTH,
    CONF_NAME,
    CONF_PERIOD,
    CONF_STYLE,
    CONF_UPDATE_INTERVAL,
    CONF_YEAR,
    DEFAULT_NAME,
    DEFAULT_UPDATE_INTERVAL,
    DISPLAY_ABSOLUTE,
    DISPLAY_OPTIONS,
    DOMAIN,
    MAX_UPDATE_INTERVAL,
    MIN_UPDATE_INTERVAL,
    PERIOD_NONE,
    PERIOD_OPTIONS,
    STYLE_DAY,
    STYLE_OPTIONS,
)


def _select(options: dict[str, str]) -> selector.SelectSelector:
    return selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=[
                selector.SelectOptionDict(value=value, label=label)
                for value, label in options.items()
            ],
            mode=selector.SelectSelectorMode.DROPDOWN,
        )
    )


def _month_options() -> dict[str, str]:
    return {str(month): f"{month}月" for month in range(1, 13)}


def _day_options() -> dict[str, str]:
    return {str(day): f"{day}日" for day in range(1, 32)}


def _ref_parts(data: dict[str, Any]) -> tuple[int, int, int]:
    """读取当前日期分量，兼容旧版单个 date 字段。"""
    if all(key in data for key in (CONF_YEAR, CONF_MONTH, CONF_DAY)):
        try:
            return (
                int(data[CONF_YEAR]),
                int(data[CONF_MONTH]),
                int(data[CONF_DAY]),
            )
        except (TypeError, ValueError):
            pass
    if data.get(CONF_DATE):
        try:
            ref = parse_date(data[CONF_DATE])
            return ref.year, ref.month, ref.day
        except (TypeError, ValueError):
            pass
    today = date.today()
    return today.year, today.month, today.day


def _build_schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    data = defaults or {}
    year, month, day = _ref_parts(data)
    return vol.Schema(
        {
            vol.Required(
                CONF_NAME, default=data.get(CONF_NAME, DEFAULT_NAME)
            ): str,
            vol.Required(CONF_YEAR, default=year): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=lunar.MIN_YEAR,
                    max=lunar.MAX_YEAR,
                    step=1,
                    mode=selector.NumberSelectorMode.BOX,
                    unit_of_measurement="年",
                )
            ),
            vol.Required(CONF_MONTH, default=str(month)): _select(
                _month_options()
            ),
            vol.Required(CONF_DAY, default=str(day)): _select(_day_options()),
            vol.Required(
                CONF_CALENDAR, default=data.get(CONF_CALENDAR, CALENDAR_SOLAR)
            ): _select(CALENDAR_OPTIONS),
            vol.Required(
                CONF_DISPLAY_MODE,
                default=data.get(CONF_DISPLAY_MODE, DISPLAY_ABSOLUTE),
            ): _select(DISPLAY_OPTIONS),
            vol.Required(
                CONF_STYLE, default=data.get(CONF_STYLE, STYLE_DAY)
            ): _select(STYLE_OPTIONS),
            vol.Required(
                CONF_PERIOD, default=data.get(CONF_PERIOD, PERIOD_NONE)
            ): _select(PERIOD_OPTIONS),
            vol.Optional(
                CONF_IS_LEAP_MONTH,
                default=bool(data.get(CONF_IS_LEAP_MONTH, False)),
            ): selector.BooleanSelector(),
            vol.Required(
                CONF_UPDATE_INTERVAL,
                default=int(
                    data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
                ),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=MIN_UPDATE_INTERVAL,
                    max=MAX_UPDATE_INTERVAL,
                    step=1,
                    mode=selector.NumberSelectorMode.BOX,
                    unit_of_measurement="秒",
                )
            ),
        }
    )


def _validate(user_input: dict[str, Any]) -> dict[str, Any]:
    """校验并规范化用户输入。"""
    name = str(user_input.get(CONF_NAME, "")).strip()
    if not name:
        raise ValueError("invalid_name")

    try:
        year = int(user_input[CONF_YEAR])
        month = int(user_input[CONF_MONTH])
        day = int(user_input[CONF_DAY])
    except (KeyError, TypeError, ValueError) as err:
        raise ValueError("invalid_date") from err

    if not (
        lunar.MIN_YEAR <= year <= lunar.MAX_YEAR
        and 1 <= month <= 12
        and 1 <= day <= 31
    ):
        raise ValueError("invalid_date")

    calendar = user_input.get(CONF_CALENDAR, CALENDAR_SOLAR)
    if calendar not in CALENDAR_OPTIONS:
        calendar = CALENDAR_SOLAR
    is_leap_month = bool(user_input.get(CONF_IS_LEAP_MONTH, False)) and (
        calendar == CALENDAR_LUNAR
    )

    if calendar == CALENDAR_LUNAR:
        if day > 30:
            raise ValueError("invalid_date")
        try:
            lunar.lunar_to_solar_safe(year, month, day, is_leap_month)
        except ValueError as err:
            raise ValueError("invalid_date") from err
    else:
        try:
            date(year, month, day)
        except ValueError as err:
            raise ValueError("invalid_date") from err

    try:
        interval = int(user_input.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL))
    except (TypeError, ValueError) as err:
        raise ValueError("invalid_interval") from err
    if not MIN_UPDATE_INTERVAL <= interval <= MAX_UPDATE_INTERVAL:
        raise ValueError("invalid_interval")

    return {
        CONF_NAME: name,
        CONF_YEAR: year,
        CONF_MONTH: month,
        CONF_DAY: day,
        CONF_CALENDAR: calendar,
        CONF_DISPLAY_MODE: user_input.get(CONF_DISPLAY_MODE, DISPLAY_ABSOLUTE),
        CONF_STYLE: user_input.get(CONF_STYLE, STYLE_DAY),
        CONF_PERIOD: user_input.get(CONF_PERIOD, PERIOD_NONE),
        CONF_IS_LEAP_MONTH: is_leap_month,
        CONF_UPDATE_INTERVAL: interval,
    }


class AnniversaryConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """通过 UI 添加一个纪念日传感器。"""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                data = _validate(user_input)
            except ValueError as err:
                errors["base"] = str(err)
            else:
                return self.async_create_entry(title=data[CONF_NAME], data=data)

        return self.async_show_form(
            step_id="user",
            data_schema=_build_schema(user_input),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        return AnniversaryOptionsFlow()


class AnniversaryOptionsFlow(config_entries.OptionsFlow):
    """编辑已有纪念日传感器。"""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        entry = self.config_entry
        current = {**entry.data, **entry.options}
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                data = _validate(user_input)
            except ValueError as err:
                errors["base"] = str(err)
            else:
                self.hass.config_entries.async_update_entry(
                    entry, title=data[CONF_NAME]
                )
                return self.async_create_entry(title="", data=data)

        return self.async_show_form(
            step_id="init",
            data_schema=_build_schema(user_input or current),
            errors=errors,
        )

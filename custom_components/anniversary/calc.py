"""纪念日传感器核心计算：目标日期、倒计时与显示格式。"""
from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, datetime, time
from typing import Any

from . import lunar
from .const import (
    CALENDAR_LUNAR,
    CONF_CALENDAR,
    CONF_DATE,
    CONF_DAY,
    CONF_DISPLAY_MODE,
    CONF_IS_LEAP_MONTH,
    CONF_MONTH,
    CONF_PERIOD,
    CONF_STYLE,
    CONF_YEAR,
    DISPLAY_ABSOLUTE,
    PERIOD_MONTH,
    PERIOD_NONE,
    PERIOD_YEAR,
    STYLE_DAY,
    STYLE_YMD,
    STYLE_YMDHMS,
)


@dataclass(frozen=True)
class AnniversaryResult:
    """一次计算的结果。"""

    value: int | str
    target_date: date
    signed_seconds: int
    days: int
    style: str
    period: str
    calendar: str
    display_mode: str
    is_numeric: bool


def parse_date(value: Any) -> date:
    """把 date/datetime/ISO 字符串统一成 date（用于兼容旧配置）。"""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    return date.fromisoformat(text[:10])


def _safe_date(year: int, month: int, day: int) -> date:
    """构造日期，日期超出当月天数时取当月最后一天。"""
    last = calendar.monthrange(year, month)[1]
    return date(year, month, min(day, last))


def _add_months_date(value: date, months: int) -> date:
    """给日期加月份，保持“尽量同一天”的规则。"""
    total = value.year * 12 + (value.month - 1) + months
    year, month0 = divmod(total, 12)
    month = month0 + 1
    return _safe_date(year, month, value.day)


def _add_months_datetime(value: datetime, months: int) -> datetime:
    """给日期时间加月份，保持“尽量同一天、同一时刻”的规则。"""
    total = value.year * 12 + (value.month - 1) + months
    year, month0 = divmod(total, 12)
    month = month0 + 1
    last = calendar.monthrange(year, month)[1]
    return value.replace(year=year, month=month, day=min(value.day, last))


def _date_parts(start: date, end: date) -> tuple[int, int, int]:
    """返回两个日期之间的整年/整月/剩余天数（end >= start）。"""
    if end < start:
        start, end = end, start
    years = end.year - start.year
    months = end.month - start.month
    if end.day < start.day:
        months -= 1
    if months < 0:
        years -= 1
        months += 12
    anchor = _add_months_date(start, years * 12 + months)
    days = (end - anchor).days
    return years, months, days


def _datetime_parts(
    start: datetime, end: datetime
) -> tuple[int, int, int, int, int, int]:
    """精确的日历时长：年/月/日/时/分/秒（end >= start）。"""
    if end < start:
        start, end = end, start
    years = end.year - start.year
    months = end.month - start.month
    if end.day < start.day:
        months -= 1
    if months < 0:
        years -= 1
        months += 12
    anchor = _add_months_datetime(start, years * 12 + months)
    # 月末夹取（例如 1/31 + 1 月 = 2/28）可能让 anchor 超过 end，回退一个月。
    while anchor > end and (years > 0 or months > 0):
        months -= 1
        if months < 0:
            months += 12
            years -= 1
        anchor = _add_months_datetime(start, years * 12 + months)
    delta = end - anchor
    days = delta.days
    hours, rem = divmod(delta.seconds, 3600)
    minutes, seconds = divmod(rem, 60)
    return years, months, days, hours, minutes, seconds


def _fmt_parts(
    values: list[int], suffixes: list[str], zero_text: str
) -> str:
    """格式化时间分量，省略最前面的 0，但保留第一个非零之后的所有分量。"""
    if all(value == 0 for value in values):
        return zero_text
    index = 0
    while index < len(values) - 1 and values[index] == 0:
        index += 1
    return "".join(
        f"{value}{suffix}"
        for value, suffix in zip(values[index:], suffixes[index:])
    )


def _solar_target(ref: date, period: str, today: date) -> date:
    """计算阳历目标日期。"""
    if period == PERIOD_NONE:
        return ref

    # 周期事件的起点不能早于用户填写的日期；未来日期直接作为第一次事件。
    if ref > today:
        return ref

    if period == PERIOD_YEAR:
        for offset in range(3):
            candidate = _safe_date(today.year + offset, ref.month, ref.day)
            if candidate >= today:
                return candidate
        return _safe_date(today.year + 1, ref.month, ref.day)

    if period == PERIOD_MONTH:
        year, month = today.year, today.month
        for _ in range(3):
            candidate = _safe_date(year, month, ref.day)
            if candidate >= today:
                return candidate
            month += 1
            if month > 12:
                month = 1
                year += 1
        return _safe_date(year, month, ref.day)

    return ref


def _lunar_target(
    year: int, month: int, day: int, period: str, today: date, prefer_leap: bool
) -> date:
    """计算农历目标日期。year/month/day 按农历解释。"""
    base = lunar.lunar_to_solar_safe(year, month, day, prefer_leap)

    if period == PERIOD_NONE:
        return base

    if base > today:
        return base

    today_lunar_year, today_lunar_month, _, _ = lunar.solar_to_lunar(today)

    if period == PERIOD_YEAR:
        for offset in range(3):
            target_year = today_lunar_year + offset
            if target_year > lunar.MAX_YEAR:
                break
            candidate = lunar.lunar_to_solar_safe(
                target_year, month, day, prefer_leap
            )
            if candidate >= today:
                return candidate
        target_year = min(today_lunar_year + 1, lunar.MAX_YEAR)
        return lunar.lunar_to_solar_safe(target_year, month, day, prefer_leap)

    if period == PERIOD_MONTH:
        target_year, target_month = today_lunar_year, today_lunar_month
        for _ in range(24):
            if target_year > lunar.MAX_YEAR:
                break
            candidate = lunar.lunar_to_solar_safe(
                target_year, target_month, day, prefer_leap
            )
            if candidate >= today:
                return candidate
            target_month += 1
            if target_month > 12:
                target_month = 1
                target_year += 1
        target_year = min(today_lunar_year + 1, lunar.MAX_YEAR)
        return lunar.lunar_to_solar_safe(
            target_year, today_lunar_month, day, prefer_leap
        )

    return base


def _format_text(
    style: str, now: datetime, target: date, signed_seconds: int
) -> str:
    """把倒计时格式化为中文文本（不含正负号）。"""
    if style == STYLE_YMD:
        years, months, days = _date_parts(now.date(), target)
        return _fmt_parts([years, months, days], ["年", "月", "日"], "0日")
    if style == STYLE_YMDHMS:
        target_dt = datetime.combine(target, time.min, tzinfo=now.tzinfo)
        years, months, days, hours, minutes, seconds = _datetime_parts(
            now, target_dt
        )
        return _fmt_parts(
            [years, months, days, hours, minutes, seconds],
            ["年", "月", "日", "时", "分", "秒"],
            "0秒",
        )
    return ""


def _ref_parts(config: dict[str, Any]) -> tuple[int, int, int]:
    """读取参考日期：优先新字段 year/month/day，兼容旧字段 date。"""
    if all(key in config for key in (CONF_YEAR, CONF_MONTH, CONF_DAY)):
        return (
            int(config[CONF_YEAR]),
            int(config[CONF_MONTH]),
            int(config[CONF_DAY]),
        )
    ref = parse_date(config[CONF_DATE])
    return ref.year, ref.month, ref.day


def compute(config: dict[str, Any], now: datetime) -> AnniversaryResult:
    """根据配置和当前时间计算传感器状态。"""
    ref_year, ref_month, ref_day = _ref_parts(config)
    calendar_type = config.get(CONF_CALENDAR, "solar")
    period = config.get(CONF_PERIOD, PERIOD_NONE)
    style = config.get(CONF_STYLE, STYLE_DAY)
    if style not in (STYLE_YMD, STYLE_YMDHMS, STYLE_DAY):
        style = STYLE_DAY
    display_mode = config.get(CONF_DISPLAY_MODE, DISPLAY_ABSOLUTE)
    prefer_leap = bool(config.get(CONF_IS_LEAP_MONTH, False))
    today = now.date()

    if calendar_type == CALENDAR_LUNAR:
        target = _lunar_target(
            ref_year, ref_month, ref_day, period, today, prefer_leap
        )
    else:
        target = _solar_target(
            date(ref_year, ref_month, ref_day), period, today
        )

    target_dt = datetime.combine(target, time.min, tzinfo=now.tzinfo)
    signed_seconds = int((target_dt - now).total_seconds())
    days = (target - today).days
    absolute = display_mode == DISPLAY_ABSOLUTE

    if style == STYLE_DAY:
        value: int | str = abs(days) if absolute else days
        is_numeric = True
    else:
        text = _format_text(style, now, target, signed_seconds)
        if signed_seconds < 0 and not absolute:
            text = "-" + text
        value = text
        is_numeric = False

    return AnniversaryResult(
        value=value,
        target_date=target,
        signed_seconds=signed_seconds,
        days=days,
        style=style,
        period=period,
        calendar=calendar_type,
        display_mode=display_mode,
        is_numeric=is_numeric,
    )

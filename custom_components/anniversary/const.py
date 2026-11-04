"""纪念日集成常量。"""
from __future__ import annotations

DOMAIN = "anniversary"
DEFAULT_NAME = "纪念日"

CONF_NAME = "name"
# 旧版本使用单个 date 字段；新版本使用 year/month/day，保留 date 以兼容已有条目
CONF_DATE = "date"
CONF_YEAR = "year"
CONF_MONTH = "month"
CONF_DAY = "day"
CONF_CALENDAR = "calendar"
CONF_IS_LEAP_MONTH = "is_leap_month"
CONF_DISPLAY_MODE = "display_mode"
CONF_STYLE = "style"
CONF_PERIOD = "period"
CONF_UPDATE_INTERVAL = "update_interval"

CALENDAR_SOLAR = "solar"
CALENDAR_LUNAR = "lunar"
CALENDAR_OPTIONS: dict[str, str] = {
    CALENDAR_SOLAR: "阳历",
    CALENDAR_LUNAR: "农历",
}

DISPLAY_ABSOLUTE = "absolute"
DISPLAY_SIGNED = "signed"
DISPLAY_OPTIONS: dict[str, str] = {
    DISPLAY_ABSOLUTE: "绝对值（始终显示正数）",
    DISPLAY_SIGNED: "带符号（过期后显示负数）",
}

STYLE_YMD = "ymd"
STYLE_YMDHMS = "ymdhms"
STYLE_DAY = "day"
STYLE_OPTIONS: dict[str, str] = {
    STYLE_YMD: "年月日（文本）",
    STYLE_YMDHMS: "年月日时分秒（文本）",
    STYLE_DAY: "日（数字）",
}
NUMERIC_STYLES = {STYLE_DAY}

PERIOD_NONE = "none"
PERIOD_YEAR = "year"
PERIOD_MONTH = "month"
PERIOD_OPTIONS: dict[str, str] = {
    PERIOD_NONE: "无（固定日期倒计时）",
    PERIOD_YEAR: "年（生日、周年纪念）",
    PERIOD_MONTH: "月（发薪日等每月事件）",
}

DEFAULT_UPDATE_INTERVAL = 3600
MIN_UPDATE_INTERVAL = 1
MAX_UPDATE_INTERVAL = 86400

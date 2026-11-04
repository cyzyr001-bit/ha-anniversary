"""农历与公历互转（1900-2100）。

数据表为常见的 1900-2100 年农历年编码表，数据来源为香港天文台公布的
公历/农历对照表。这里只实现纪念日所需的年/月/日互转，不包含节气、
干支、宜忌等扩展信息。

编码说明（每个年份一个 16 位整数）：
- bit 0-3   闰月月份，0 表示无闰月
- bit 4-15  1-12 月的大小月，1 表示 30 天，0 表示 29 天
- bit 16    闰月大小，1 表示 30 天，0 表示 29 天
"""
from __future__ import annotations

from datetime import date, timedelta

MIN_YEAR = 1900
MAX_YEAR = 2100

# 1900-2100 年农历数据
LUNAR_INFO: tuple[int, ...] = (
    0x04BD8, 0x04AE0, 0x0A570, 0x054D5, 0x0D260, 0x0D950, 0x16554, 0x056A0, 0x09AD0, 0x055D2,  # 1900-1909
    0x04AE0, 0x0A5B6, 0x0A4D0, 0x0D250, 0x1D255, 0x0B540, 0x0D6A0, 0x0ADA2, 0x095B0, 0x14977,  # 1910-1919
    0x04970, 0x0A4B0, 0x0B4B5, 0x06A50, 0x06D40, 0x1AB54, 0x02B60, 0x09570, 0x052F2, 0x04970,  # 1920-1929
    0x06566, 0x0D4A0, 0x0EA50, 0x06E95, 0x05AD0, 0x02B60, 0x186E3, 0x092E0, 0x1C8D7, 0x0C950,  # 1930-1939
    0x0D4A0, 0x1D8A6, 0x0B550, 0x056A0, 0x1A5B4, 0x025D0, 0x092D0, 0x0D2B2, 0x0A950, 0x0B557,  # 1940-1949
    0x06CA0, 0x0B550, 0x15355, 0x04DA0, 0x0A5B0, 0x14573, 0x052B0, 0x0A9A8, 0x0E950, 0x06AA0,  # 1950-1959
    0x0AEA6, 0x0AB50, 0x04B60, 0x0AAE4, 0x0A570, 0x05260, 0x0F263, 0x0D950, 0x05B57, 0x056A0,  # 1960-1969
    0x096D0, 0x04DD5, 0x04AD0, 0x0A4D0, 0x0D4D4, 0x0D250, 0x0D558, 0x0B540, 0x0B6A0, 0x195A6,  # 1970-1979
    0x095B0, 0x049B0, 0x0A974, 0x0A4B0, 0x0B27A, 0x06A50, 0x06D40, 0x0AF46, 0x0AB60, 0x09570,  # 1980-1989
    0x04AF5, 0x04970, 0x064B0, 0x074A3, 0x0EA50, 0x06B58, 0x05AC0, 0x0AB60, 0x096D5, 0x092E0,  # 1990-1999
    0x0C960, 0x0D954, 0x0D4A0, 0x0DA50, 0x07552, 0x056A0, 0x0ABB7, 0x025D0, 0x092D0, 0x0CAB5,  # 2000-2009
    0x0A950, 0x0B4A0, 0x0BAA4, 0x0AD50, 0x055D9, 0x04BA0, 0x0A5B0, 0x15176, 0x052B0, 0x0A930,  # 2010-2019
    0x07954, 0x06AA0, 0x0AD50, 0x05B52, 0x04B60, 0x0A6E6, 0x0A4E0, 0x0D260, 0x0EA65, 0x0D530,  # 2020-2029
    0x05AA0, 0x076A3, 0x096D0, 0x04AFB, 0x04AD0, 0x0A4D0, 0x1D0B6, 0x0D250, 0x0D520, 0x0DD45,  # 2030-2039
    0x0B5A0, 0x056D0, 0x055B2, 0x049B0, 0x0A577, 0x0A4B0, 0x0AA50, 0x1B255, 0x06D20, 0x0ADA0,  # 2040-2049
    0x14B63, 0x09370, 0x049F8, 0x04970, 0x064B0, 0x168A6, 0x0EA50, 0x06AA0, 0x1A6C4, 0x0AAE0,  # 2050-2059（2057 已按香港天文台表校正）
    0x092E0, 0x0D2E3, 0x0C960, 0x0D557, 0x0D4A0, 0x0DA50, 0x05D55, 0x056A0, 0x0A6D0, 0x055D4,  # 2060-2069（2060 已按香港天文台表校正）
    0x052D0, 0x0A9B8, 0x0A950, 0x0B4A0, 0x0B6A6, 0x0AD50, 0x055A0, 0x0ABA4, 0x0A5B0, 0x052B0,  # 2070-2079
    0x0B273, 0x06930, 0x07337, 0x06AA0, 0x0AD50, 0x14B55, 0x04B60, 0x0A570, 0x054E4, 0x0D160,  # 2080-2089
    0x0E968, 0x0D520, 0x0DAA0, 0x16AA6, 0x056D0, 0x04AE0, 0x0A9D4, 0x0A2D0, 0x0D150, 0x0F252,  # 2090-2099
    0x0D520,  # 2100
)

_BASE_SOLAR = date(1900, 1, 31)  # 农历 1900 年正月初一


def _check_year(year: int) -> None:
    if not MIN_YEAR <= year <= MAX_YEAR:
        raise ValueError(f"农历年份超出支持范围 {MIN_YEAR}-{MAX_YEAR}: {year}")


def leap_month(year: int) -> int:
    """返回该农历年的闰月月份，0 表示无闰月。"""
    _check_year(year)
    return LUNAR_INFO[year - MIN_YEAR] & 0xF


def leap_days(year: int) -> int:
    """返回该农历年闰月的天数（29/30），无闰月返回 0。"""
    if leap_month(year) == 0:
        return 0
    return 30 if LUNAR_INFO[year - MIN_YEAR] & 0x10000 else 29


def month_days(year: int, month: int) -> int:
    """返回农历某年某月（非闰月）的天数。"""
    _check_year(year)
    if not 1 <= month <= 12:
        raise ValueError(f"农历月份无效: {month}")
    return 30 if LUNAR_INFO[year - MIN_YEAR] & (0x10000 >> month) else 29


def year_days(year: int) -> int:
    """返回农历某年的总天数。"""
    _check_year(year)
    info = LUNAR_INFO[year - MIN_YEAR]
    total = 29 * 12
    for bit in range(15, 3, -1):
        if info & (1 << bit):
            total += 1
    return total + leap_days(year)


def solar_to_lunar(solar: date) -> tuple[int, int, int, bool]:
    """公历 -> 农历，返回 (年, 月, 日, 是否闰月)。"""
    if solar < _BASE_SOLAR:
        raise ValueError(f"日期早于农历数据起点 {_BASE_SOLAR}: {solar}")
    offset = (solar - _BASE_SOLAR).days
    year = MIN_YEAR
    while year <= MAX_YEAR and offset >= year_days(year):
        offset -= year_days(year)
        year += 1
    if year > MAX_YEAR:
        raise ValueError(f"日期超出农历数据范围: {solar}")

    leap = leap_month(year)
    month = 1
    is_leap = False
    while month <= 12:
        days = month_days(year, month)
        if offset < days:
            break
        offset -= days
        if leap == month:
            days = leap_days(year)
            if offset < days:
                is_leap = True
                break
            offset -= days
        month += 1
    if month > 12:
        # 正常不会发生；兜底为下一年的正月初一
        return year + 1, 1, 1, False
    return year, month, offset + 1, is_leap


def lunar_month_days(year: int, month: int, is_leap: bool = False) -> int:
    """返回农历某年某月（可指定闰月）的天数。"""
    if is_leap:
        if leap_month(year) != month:
            raise ValueError(f"{year} 年没有闰 {month} 月")
        return leap_days(year)
    return month_days(year, month)


def lunar_to_solar(year: int, month: int, day: int, is_leap: bool = False) -> date:
    """农历 -> 公历。"""
    _check_year(year)
    if not 1 <= month <= 12:
        raise ValueError(f"农历月份无效: {month}")
    max_day = lunar_month_days(year, month, is_leap)
    if not 1 <= day <= max_day:
        raise ValueError(f"农历日期无效: {year}-{month}-{day}（该月共 {max_day} 天）")

    offset = 0
    for y in range(MIN_YEAR, year):
        offset += year_days(y)
    leap = leap_month(year)
    for m in range(1, month):
        offset += month_days(year, m)
        if leap == m:
            offset += leap_days(year)
    if is_leap:
        offset += month_days(year, month)
    offset += day - 1
    return _BASE_SOLAR + timedelta(days=offset)


def lunar_to_solar_safe(
    year: int, month: int, day: int, prefer_leap: bool = False
) -> date:
    """农历转公历，自动处理闰月不存在、月小（三十）等情况。

    - prefer_leap=True 且该年确实有闰 month 时使用闰月，否则使用普通月；
    - day 超过该月天数时，取该月最后一天（例如二月三十 -> 二月廿九）。
    """
    use_leap = bool(prefer_leap and leap_month(year) == month)
    max_day = lunar_month_days(year, month, use_leap)
    return lunar_to_solar(year, month, min(day, max_day), use_leap)

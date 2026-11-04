"""纪念日传感器实体。"""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)
from homeassistant.util import dt as dt_util

from .calc import AnniversaryResult, compute
from .const import (
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    STYLE_DAY,
)

_LOGGER = logging.getLogger(__name__)


class AnniversaryCoordinator(DataUpdateCoordinator[AnniversaryResult]):
    """按配置的间隔重新计算倒计时。"""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.entry = entry
        self.config: dict[str, Any] = {**entry.data, **entry.options}
        interval = int(
            self.config.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
        )
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{entry.entry_id}",
            update_interval=timedelta(seconds=interval),
        )

    async def _async_update_data(self) -> AnniversaryResult:
        return compute(self.config, dt_util.now())


class AnniversarySensor(
    CoordinatorEntity[AnniversaryCoordinator], SensorEntity
):
    """一个纪念日传感器。"""

    _attr_icon = "mdi:calendar-heart"
    _attr_should_poll = False

    def __init__(
        self, coordinator: AnniversaryCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_name = entry.title
        self._attr_unique_id = entry.entry_id

    @property
    def native_value(self) -> int | str | None:
        return self.coordinator.data.value

    @property
    def native_unit_of_measurement(self) -> str | None:
        return "天" if self.coordinator.data.style == STYLE_DAY else None

    @property
    def state_class(self) -> SensorStateClass | None:
        if self.coordinator.data.is_numeric:
            return SensorStateClass.MEASUREMENT
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data
        return {
            "target_date": data.target_date.isoformat(),
            "signed_seconds": data.signed_seconds,
            "days": data.days,
            "period": data.period,
            "calendar": data.calendar,
            "display_mode": data.display_mode,
            "style": data.style,
            "is_past": data.signed_seconds < 0,
        }


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """创建传感器。"""
    coordinator = AnniversaryCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    async_add_entities([AnniversarySensor(coordinator, entry)])

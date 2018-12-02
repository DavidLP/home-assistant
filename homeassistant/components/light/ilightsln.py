"""
Support for LimitlessLED bulbs.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/light.limitlessled/
"""
import asyncio
import logging

import voluptuous as vol

from homeassistant.const import CONF_HOST, CONF_PORT, STATE_ON, STATE_UNAVAILABLE
from homeassistant.components.light import (
    ATTR_BRIGHTNESS, ATTR_COLOR_TEMP, SUPPORT_BRIGHTNESS, SUPPORT_WHITE_VALUE, SUPPORT_COLOR_TEMP, Light, PLATFORM_SCHEMA)
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.restore_state import RestoreEntity

REQUIREMENTS = ['ilightsln==0.0.1']

_LOGGER = logging.getLogger(__name__)

# Validation of the user's configuration
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_HOST): cv.string,
    vol.Optional(CONF_PORT, default=50000): cv.positive_int,
})


# PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
#     vol.Required(CONF_HOST): cv.string,
#     vol.Optional(CONF_PORT, default=50000): cv.port,
#     vol.Required(CONF_LIGHTS):  vol.All(cv.ensure_list, [
#         {
#             vol.Required(CONF_NAME): cv.string,
#             vol.Optional(CONF_TYPE, default=DEFAULT_LED_TYPE):
#                 vol.In(LED_TYPE),
#             vol.Required(CONF_NUMBER): cv.positive_int,
#             vol.Optional(CONF_FADE, default=DEFAULT_FADE): cv.boolean,
#         }
#     ]),
# })

LED_TYPE = ['dimmer',  # on/off/dimmable
            'white'  # on/off/dimmable/white value
            ]

SUPPORT_LED_WHITE = (SUPPORT_BRIGHTNESS | SUPPORT_WHITE_VALUE)
SUPPORT_LED_DIMMER = SUPPORT_BRIGHTNESS


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Initialize the ILightSln gateway"""

    from ilightsln import ilightsln

    # Setup connection with gateway
    gateway = ilightsln.ILightSln(host=config.get(CONF_HOST), port=config.get(CONF_PORT),
                                  loop=hass.loop)
    await gateway.async_create_connection()
    await gateway.async_add_lights_from_gateway()  # use lights stored on gateway
    try:
        await asyncio.wait_for(gateway.lights_initialized.wait(), 5)
    except asyncio.TimeoutError:
        _LOGGER.error('Initialization of lights failed')
        return
    if not gateway.lights:
        _LOGGER.error('No lights stored on gateway')
        return
    async_add_entities([ILightSln(l) for l in gateway.lights])


class ILightSln(Light, RestoreEntity):
    """Representation of a ILightSln light """

    def __init__(self, light):
        """Initialize a group."""
        self._supported = SUPPORT_BRIGHTNESS | SUPPORT_WHITE_VALUE
        self._light = light

    async def async_added_to_hass(self):
        """Handle entity about to be added to hass event."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state:
            self._light.on = (last_state.state == STATE_ON)
            self._light.available = not (last_state.state == STATE_UNAVAILABLE)
            self._light.brightness = last_state.attributes.get('brightness')
            # self._light.temperature = last_state.attributes.get('color_temp')

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._light.available

    @property
    def name(self):
        """Return the name of the light."""
        return self._light.name

    @property
    def should_poll(self):
        """Polling needed."""
        return True

    async def async_turn_on(self, **kwargs):
        """Turn on light."""
#         if ATTR_COLOR_TEMP in kwargs:
#             self._light.color_temp = kwargs[ATTR_COLOR_TEMP]

        if ATTR_BRIGHTNESS in kwargs:
            brightness = self._map_int_value(kwargs[ATTR_BRIGHTNESS], 0, 255,
                                             self._light._gateway._MIN_BRIGHTNESS,
                                             self._light._gateway._MAX_BRIGHTNESS)
            self._light.brightness = brightness

        await self._light.async_turn_on()
        self.async_schedule_update_ha_state()  # not sure if needed

    async def async_turn_off(self, **kwargs):
        """Turn off light."""
#         if ATTR_COLOR_TEMP in kwargs:
#             self._light.color_temp = kwargs[ATTR_COLOR_TEMP]

        if ATTR_BRIGHTNESS in kwargs:
            brightness = self._map_int_value(kwargs[ATTR_BRIGHTNESS], 0, 255,
                                             self._light._gateway._MIN_BRIGHTNESS,
                                             self._light._gateway._MAX_BRIGHTNESS)
            self._light.brightness = brightness

        await self._light.async_turn_off()
        self.async_schedule_update_ha_state()  # not sure if needed

    @property
    def is_on(self):
        """Return true if device is on."""
        return self._light.on

    @property
    def brightness(self):
        """Return the brightness property."""
        brightness = self._map_int_value(self._light.brightness,
                                         self._light._gateway._MIN_BRIGHTNESS,
                                         self._light._gateway._MAX_BRIGHTNESS,
                                         0, 255)
        return brightness

#     @property
#     def color_temp(self):
#         """Return the temperature property."""
#         return self._light.color_temp

    @property
    def supported_features(self):
        """Flag supported features."""
        return self._supported

    def _map_int_value(self, value, min_val, max_val, min_val_new, max_val_new):
        ''' Maps an integer value from linear range [min_val, max_val] to [min_val_new, max_val_new] '''
        return int(float(value - min_val) / (max_val - min_val) * (max_val_new - min_val_new) + min_val_new)

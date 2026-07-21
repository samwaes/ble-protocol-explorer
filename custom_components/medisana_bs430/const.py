"""Constants for the Medisana BS430 integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "medisana_bs430"
PLATFORMS: Final = ["sensor", "button"]

INTEGRATION_VERSION: Final = "0.5.1"
BUILD_COMMIT: Final = "95973306946f3aa03b41aebf745fdf248ddd5784"

CONF_ADDRESS: Final = "address"
CONF_PROFILE_MAP: Final = "profile_map"
CONF_IMPORT_HISTORY: Final = "import_history"
CONF_RETAIN_DIAGNOSTICS: Final = "retain_diagnostics"

DEFAULT_IMPORT_HISTORY: Final = True
DEFAULT_RETAIN_DIAGNOSTICS: Final = True

PRIMARY_PROFILE_ID: Final = 1
MIN_PROFILE_ID: Final = 1
MAX_PROFILE_ID: Final = 8
PROFILE_NAME_KEY_PREFIX: Final = "profile_name_"

MANUFACTURER: Final = "Medisana"
MODEL: Final = "BS430"

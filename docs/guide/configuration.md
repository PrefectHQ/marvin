# Configuration

Marvin has many configurable settings that can be loaded from `marvin.settings`.

## Setting values
All settings can be configured via environment variable using the pattern `MARVIN_<name of setting>`. For example, to set the log level, set `MARVIN_LOG_LEVEL=DEBUG` and verify that `marvin.settings.log_level == 'DEBUG'`. Settings can also be set at runtime through assignment (e.g. `marvin.settings.log_level = 'DEBUG'`) but this is not recommended because some code might haved loaded configuration on import and consequently never pick up the updated value.

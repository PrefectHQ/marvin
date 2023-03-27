# Configuration

Marvin has many configurable settings that can be loaded from `marvin.settings`.

## Setting values
All settings can be configured via environment variable using the pattern `MARVIN_<name of setting>`. For example, to set the log level, set `MARVIN_LOG_LEVEL=DEBUG` and verify that `marvin.settings.log_level == 'DEBUG'`. Settings can also be set at runtime through assignment (e.g. `marvin.settings.log_level = 'DEBUG'`) but this is not recommended because some code might haved loaded configuration on import and consequently never pick up the updated value.

## Important settings

### Global
#### Log level
Set the log level
```
MARVIN_LOG_LEVEL=INFO
```
#### Verbose mode
Logs extra information, especially when the log level is `DEBUG`. 
```
MARVIN_VERBOSE=true
```

### OpenAI
#### API key
Set your OpenAI API key
```
MARVIN_OPENAI_API_KEY=
```
Marvin will also respect this global variable
```
OPENAI_API_KEY=
```

#### Model name

Choose the OpenAI model.
```
MARVIN_OPENAI_MODEL_NAME='gpt-4'
```

### Database

#### Database connection URL
Set the database connection URL. Must be a fully-qualified URL. Marvin supports both Postgres and SQLite.

```
MARVIN_DATABASE_CONNECTION_URL=
```
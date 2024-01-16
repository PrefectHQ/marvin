# Settings

Marvin makes use of Pydantic's `BaseSettings` to configure, load, and change behavior.

## Environment Variables
All settings are configurable via environment variables like `MARVIN_<setting name>`.

Please set Marvin specific settings in `~/.marvin/.env`. One exception being `OPENAI_API_KEY`, which may be as a global env var on your system and it will be picked up by Marvin.

!!! example "Setting Environment Variables"
    For example, in your `~/.marvin/.env` file you could have:
    ```shell
    MARVIN_LOG_LEVEL=INFO
    MARVIN_OPENAI_CHAT_COMPLETIONS_MODEL=gpt-4
    MARVIN_OPENAI_API_KEY='sk-my-api-key'
    ```
    Settings these values will let you avoid setting an API key every time. 

## Runtime Settings
A runtime settings object is accessible via `marvin.settings` and can be used to access or update settings throughout the package.

!!! example "Mutating settings at runtime"
    For example, to access or change the LLM model used by Marvin at runtime:
    ```python
    import marvin

    marvin.settings.openai_chat_completions_model = 'gpt-4'
    ```


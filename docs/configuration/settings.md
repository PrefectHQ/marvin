# Settings

Marvin makes use of Pydantic's `BaseSettings` to configure, load, and change behavior.

## Environment Variables
All settings are configurable via environment variables like `MARVIN_<setting name>`.

!!! example "Setting Environment Variables"
    For example, in an `.env` file or in your shell config file you might have:
    ```shell
    MARVIN_LOG_LEVEL=DEBUG
    MARVIN_LLM_MODEL=gpt-4
    MARVIN_LLM_TEMPERATURE=0
    MARVIN_OPENAI_API_KEY='sk-my-api-key'
    ```
    Settings these values will let you avoid setting an API key every time. 

## Runtime Settings
A runtime settings object is accessible via `marvin.settings` and can be used to access or update settings throughout the package.

!!! example "Mutating settings at runtime"
    For example, to access or change the LLM model used by Marvin at runtime:
    ```python
    import marvin

    marvin.settings.llm_model # 'gpt-4'

    marvin.settings.llm_model = 'gpt-3.5-turbo'

    marvin.settings.llm_model # 'gpt-3.5-turbo'
    ```


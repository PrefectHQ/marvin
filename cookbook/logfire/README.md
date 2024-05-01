## using logfire with marvin

[logfire](https://github.com/pydantic/logfire?tab=readme-ov-file#pydantic-logfire--uncomplicated-observability) is brand new (Apr 2024) and is an observability tool for python applications - [otel](https://opentelemetry.io/docs/what-is-opentelemetry/)-based tracing, metrics, and logging. its pretty [awesome](https://docs.pydantic.dev/logfire/#pydantic-logfire-the-observability-platform-you-deserve).

they also happen to wrap OpenAI pretty well out of the box! see `hello.py` for a simple example.

### setup
```conosle
pip install marvin
```
> [!NOTE]
> optionally, if you want to try out the fastapi integration
> ```console
> pip install 'logfire[fastapi]' uvicorn
> ```

login to logfire
```console
logfire auth
```

### usage
use of marvin should be no different than any other library. check out [logfire's documentation](https://docs.pydantic.dev/logfire/#pydantic-logfire-the-observability-platform-you-deserve) for more information.


### examples
```console
gh repo clone prefecthq/marvin && cd marvin
uvicorn cookbook.logfire.demo_app:app
```

in another terminal
```console
python cookbook/logfire/send_demo_request.py
```

check out the api docs at http://localhost:8000/docs or your logfire dashboard to see the traces and logs like:

<p align="center">
  <img src="/docs/assets/images/docs/examples/logfire-span.jpeg" alt="logfire span"/>
</p>

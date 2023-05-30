FROM prefecthq/prefect:2-python3.10

WORKDIR /app

RUN python -m venv venv
ENV VIRTUAL_ENV=/app/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN pip install git+https://github.com/PrefectHQ/marvin.git#egg=marvin[chromadb]

RUN pip uninstall uvloop -y

RUN marvin database upgrade -y

COPY setup.py /app/examples/slackbot/community_bot/setup.py

COPY entrypoint.sh /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]

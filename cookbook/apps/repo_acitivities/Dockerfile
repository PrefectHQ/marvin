FROM python:3.12-slim

WORKDIR /app

RUN pip install uv
RUN uv venv
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
RUN . .venv/bin/activate

RUN apt-get update && \
    apt-get install -y git build-essential && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY . /app

RUN uv pip install -r requirements.txt
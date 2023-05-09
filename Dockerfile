FROM python:3.9

ARG MARVIN_OPENAI_API_KEY
ENV MARVIN_OPENAI_API_KEY=$MARVIN_OPENAI_API_KEY

WORKDIR /marvin

COPY . .

RUN pip install ".[dev,chromadb]"

RUN pip uninstall uvloop -y

CMD ["pytest", "-v", "-m", "not llm"]

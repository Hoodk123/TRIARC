FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml ./
COPY orchestrator ./orchestrator
COPY configs ./configs

RUN pip install --no-cache-dir --timeout 120 --retries 5 .

ENTRYPOINT ["triarc"]
CMD ["run", "add JWT auth to this Flask app and write tests"]

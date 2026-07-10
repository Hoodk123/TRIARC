FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml ./
COPY orchestrator ./orchestrator
COPY configs ./configs

RUN pip install --no-cache-dir --timeout 120 --retries 5 .

EXPOSE 8080

ENTRYPOINT ["triarc"]
CMD ["serve", "--host", "0.0.0.0", "--port", "8080"]

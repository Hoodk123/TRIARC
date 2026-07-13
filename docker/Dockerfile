FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml ./
COPY orchestrator ./orchestrator
COPY configs ./configs

RUN pip install --no-cache-dir --timeout 120 --retries 5 .

# No EXPOSE 8080 needed for headless execution scripts
# Change default to run the agent against the specific challenge paths
ENTRYPOINT ["triarc"]
CMD ["run-task", "--input", "/input/tasks.json", "--output", "/output/results.json"]
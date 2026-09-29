FROM python:3.12-slim

WORKDIR /workspace
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
COPY data ./data
RUN pip install --no-cache-dir .

CMD ["embodied-labs", "run"]

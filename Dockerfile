FROM python:3.11-slim AS builder

WORKDIR /build
COPY pyproject.toml README.md ./
COPY src/ ./src/

RUN pip install --no-cache-dir --prefix=/install .


FROM python:3.11-slim AS runtime

COPY --from=builder /install /usr/local

ENV PYTHONUNBUFFERED=1

RUN useradd --no-create-home --shell /bin/false appuser
USER appuser

CMD ["ac-infinity-mcp"]

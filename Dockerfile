FROM python:3.11.15-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=8080

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements-runtime.txt ./
RUN python -m pip install --no-cache-dir -r requirements-runtime.txt
COPY app ./app
COPY verity ./verity
COPY verity-architecture.html ./verity-architecture.html
COPY pyproject.toml README.md agents-cli-manifest.yaml ./
RUN python -m pip install --no-cache-dir --no-deps .

RUN useradd --create-home --uid 10001 verity \
    && chown -R verity:verity /app
USER 10001

CMD ["sh", "-c", "exec uvicorn app.fast_api_app:app --host 0.0.0.0 --port ${PORT}"]

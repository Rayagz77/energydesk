# syntax=docker/dockerfile:1
# Image du worker EnergyDesk (multi-stage, utilisateur non privilegie).
ARG PYTHON_IMAGE=python:3.12-slim

FROM ${PYTHON_IMAGE} AS builder
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /build
COPY requirements.txt .
RUN python -m venv /opt/venv \
 && /opt/venv/bin/pip install --upgrade pip \
 && /opt/venv/bin/pip install -r requirements.txt

FROM ${PYTHON_IMAGE} AS runtime
LABEL org.opencontainers.image.title="energydesk-worker" \
      org.opencontainers.image.description="Worker asynchrone EnergyDesk (notifications)" \
      org.opencontainers.image.source="https://github.com/rayagz77/energydesk"
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PATH="/opt/venv/bin:$PATH"
RUN groupadd --system --gid 10001 app \
 && useradd --system --uid 10001 --gid app --no-create-home --shell /usr/sbin/nologin app
WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY worker ./worker
USER 10001:10001
EXPOSE 9100
HEALTHCHECK --interval=20s --timeout=3s --start-period=20s --retries=3 \
  CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:9100/healthz', timeout=2).status == 200 else 1)"]
CMD ["python", "-m", "worker.main"]

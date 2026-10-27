# syntax=docker/dockerfile:1.7
#
# Bitcoin Solo Miner Monitor: web UI built in one stage, Python app in a small final image.
#   docker build -t bsmm .
#   docker run -d --name bsmm --network host -v bsmm-data:/data bsmm
#
# Finding miners needs to see your LAN. On Linux use --network host (see docker-compose.yml). With port mapping
# (-p 8420:8420) everything works except automatic scanning, where you type your range (e.g. 192.168.1.0/24).

# ---- 1. the web interface ------------------------------------------------------------------------------------
FROM node:22-alpine AS web
WORKDIR /app/web
COPY web/package.json web/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY web/ ./
# vite.config.ts writes the bundle to ../src/bsmm/web (that is where the Python package expects it)
RUN npm run build:fast

# ---- 2. the Python wheel -------------------------------------------------------------------------------------
FROM python:3.12-slim AS wheel
WORKDIR /app
RUN pip install --no-cache-dir build==1.2.2.post1
COPY pyproject.toml README.md LICENSE ./
COPY src/ ./src/
COPY --from=web /app/src/bsmm/web/ ./src/bsmm/web/
RUN python -m build --wheel --outdir /dist

# ---- 3. runtime ----------------------------------------------------------------------------------------------
FROM python:3.12-slim
LABEL org.opencontainers.image.title="Bitcoin Solo Miner Monitor" \
      org.opencontainers.image.description="Dashboard, API and MCP server for solo Bitcoin miners" \
      org.opencontainers.image.source="https://github.com/smokeysrh/bitcoin-solo-miner-monitor" \
      org.opencontainers.image.licenses="MIT"
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    BSMM_IN_DOCKER=1 \
    BSMM_DATA_DIR=/data \
    BSMM_HOST=0.0.0.0 \
    BSMM_PORT=8420
RUN useradd --system --create-home --uid 10001 bsmm && mkdir /data && chown bsmm /data
COPY --from=wheel /dist/*.whl /tmp/
RUN pip install /tmp/*.whl && rm /tmp/*.whl
USER bsmm
VOLUME /data
EXPOSE 8420
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import os,urllib.request as u; u.urlopen('http://127.0.0.1:%s/api/v1/health' % os.environ.get('BSMM_PORT','8420'), timeout=4)"
ENTRYPOINT ["bsmm"]
CMD ["serve"]

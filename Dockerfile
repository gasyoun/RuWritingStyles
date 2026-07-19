# syntax=docker/dockerfile:1

FROM node:24-alpine AS frontend-builder
WORKDIR /web
COPY web/package*.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

FROM python:3.11-slim AS wheel-builder
WORKDIR /src
RUN python -m pip install --no-cache-dir build
COPY pyproject.toml setup.py MANIFEST.in README.md LICENSE ./
COPY src/ ./src/
COPY ClaudeStyles/ ./ClaudeStyles/
COPY styles/ ./styles/
COPY schemas/ ./schemas/
COPY knowledge/ ./knowledge/
COPY evals/ ./evals/
COPY examples/ ./examples/
COPY model_policy.yml ./
COPY --from=frontend-builder /web/dist ./web/dist
RUN python -m build --wheel

FROM python:3.11-slim
COPY --from=wheel-builder /src/dist/*.whl /tmp/
RUN python -m pip install --no-cache-dir /tmp/*.whl && rm -f /tmp/*.whl
COPY docker-entrypoint.sh /usr/local/bin/rws-entrypoint
RUN chmod 0755 /usr/local/bin/rws-entrypoint

ENV RWS_WORKSPACE=/data \
    RWS_INPUT_ROOT=/data \
    RWS_BIND_HOST=0.0.0.0 \
    PORT=8000
WORKDIR /data
VOLUME ["/data"]
EXPOSE 8000
ENTRYPOINT ["/usr/local/bin/rws-entrypoint"]
CMD ["python", "-m", "ruwritingstyles.api"]

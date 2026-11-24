# syntax=docker/dockerfile:1

# --- frontend: build the Blockly editor -------------------------------------
FROM node:22-alpine AS web

WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

# --- build: produce a wheel that already contains the SPA -------------------
FROM python:3.11-slim AS build

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /src
RUN pip install "poetry>=2.0,<3.0"
COPY pyproject.toml README.md ./
COPY src ./src
COPY --from=web /web/dist ./src/robotstudio/web_dist
RUN poetry build --format wheel

# --- runtime ----------------------------------------------------------------
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    ROBOTSTUDIO_WORKSPACE=/workspace

WORKDIR /app
COPY --from=build /src/dist/*.whl /tmp/
RUN pip install --no-cache-dir /tmp/*.whl && rm -f /tmp/*.whl

VOLUME ["/workspace"]
EXPOSE 8000

CMD ["robotstudio", "serve", "--host", "0.0.0.0", "--port", "8000"]

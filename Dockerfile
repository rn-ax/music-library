FROM python:3.14-slim
COPY --from=ghcr.io/astral-sh/uv:0.13.6 /uv /usr/local/bin/uv
RUN apt-get update \
    && apt-get install --no-install-recommends -y ffmpeg libchromaprint-tools \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev
COPY beets/ /etc/beets/
ARG APP_VERSION=dev
ENV PATH="/app/.venv/bin:$PATH" \
    VIRTUAL_ENV="/app/.venv" \
    APP_VERSION=$APP_VERSION
EXPOSE 8337
CMD ["beet", "-c", "/etc/beets/config.yaml", "web"]

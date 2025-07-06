FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS build

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_PYTHON_DOWNLOADS=0

WORKDIR /app

RUN rm -f /etc/apt/apt.conf.d/docker-clean \
    && apt-get update \
    && apt-get install -y git

RUN --mount=type=cache,target=.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev

COPY . /app

RUN --mount=type=cache,target=.cache/uv \
    uv sync --locked --no-dev --no-editable

ADD https://github.com/fastfetch-cli/fastfetch/releases/download/2.42.0/fastfetch-linux-amd64.deb /app
ADD https://github.com/homeport/termshot/releases/download/v0.5.0/termshot_0.5.0_linux_amd64.tar.gz /app
RUN tar xzf termshot_0.5.0_linux_amd64.tar.gz

FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

RUN useradd -Ums /bin/sh appuser
COPY --from=build --chown=appuser:appuser --chmod=700 \
    /app/main.py /app/termshot /app/fastfetch-linux-amd64.deb \
    /app/logs /app/
COPY --from=build /usr/bin/git /usr/bin/git
COPY --from=build --chown=appuser:appuser --chmod=700 \
    /app/.venv \
    /app/.venv
COPY --from=build --chown=appuser:appuser --chmod=700 \
    /app/cogs \
    /app/cogs
RUN dpkg -i /app/fastfetch-linux-amd64.deb && rm /app/fastfetch-linux-amd64.deb

USER appuser
WORKDIR /app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

ENTRYPOINT ["python", "main.py"]

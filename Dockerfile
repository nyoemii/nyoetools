FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=COPY

WORKDIR /app

RUN apt-get update && apt-get install -y wget tar
RUN wget https://github.com/fastfetch-cli/fastfetch/releases/download/2.42.0/fastfetch-linux-amd64.deb && dpkg -i fastfetch-linux-amd64.deb
RUN wget https://github.com/homeport/termshot/releases/download/v0.5.0/termshot_0.5.0_linux_amd64.tar.gz && tar xzf termshot_0.5.0_linux_amd64.tar.gz

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project

ADD . /app

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked

RUN adduser -u 5678 --disabled-password --gecos "" appuser && chown -R appuser /app
USER appuser

ENTRYPOINT ["uv", "run", "main.py"]
# The image of the Veil GitHub Action. It is built once and published. The Action installs nothing at run time.
# The base images are pinned to a digest. A new digest is a change that a person reviews.
FROM ghcr.io/astral-sh/uv:0.12.1@sha256:cf4eedcaa81655197f625739489effcbe71b61ceb1506f332c3facae5deceded AS uv

FROM python:3.12-slim@sha256:b18b261e1b4974b4f321451ad5251ded85abb22c2b8b262da527dda1d031ab30

ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    UV_PROJECT_ENVIRONMENT=/usr/local \
    UV_LINK_MODE=copy

# The repo provider runs git as a child process.
RUN apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=uv /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src ./src

ENTRYPOINT ["python", "-m", "veil.shells.github_action.main"]

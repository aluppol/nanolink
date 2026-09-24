FROM python:3.12-slim@sha256:2f17fc044b579bab302c2e8054d3a686e2cb9a83de48e70534b94cd8ebbe06a9 AS build
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_NO_CACHE_DIR=1
RUN python -m venv /opt/venv
COPY requirements.lock /tmp/requirements.lock
RUN /opt/venv/bin/pip install --require-hashes --no-deps -r /tmp/requirements.lock \
 && /opt/venv/bin/pip uninstall --yes pip

FROM python:3.12-slim@sha256:2f17fc044b579bab302c2e8054d3a686e2cb9a83de48e70534b94cd8ebbe06a9 AS runtime
LABEL org.opencontainers.image.source="https://github.com/aluppol/nanolink" \
      org.opencontainers.image.licenses="AGPL-3.0-only" \
      org.opencontainers.image.description="NanoLink write side: API gateway, create-URL worker, notifier, migrations"
ENV PATH=/opt/venv/bin:$PATH \
    PYTHONPATH=/app/src \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
RUN python -m pip uninstall --yes pip \
 && useradd --system --uid 10001 --no-create-home --shell /usr/sbin/nologin nanolink
COPY --from=build /opt/venv /opt/venv
COPY src /app/src
WORKDIR /app
USER 10001:10001
EXPOSE 8000
CMD ["python", "-m", "nanolink.entrypoints.gateway"]

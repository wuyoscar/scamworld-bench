# ScamWorld runtime image: the package, the tasks with their websites, Playwright's Chromium, fonts for every script the
# websites use; no keys. Build from the repository root; the image carries the tasks in tasks/ (all of them in the released
# image, the 20 samples in a fresh clone):
#   docker build -f deploy/docker/Dockerfile -t scamworld:1.1 .
# Run (keys come from the environment or a mounted file, never from the image; outputs go to the /runs volume):
#   docker run --rm scamworld:1.1 tasks
#   docker run --rm --network host -v "$PWD/results:/runs" scamworld:1.1 run shop-01 --model M --base-url http://localhost:8000/v1
FROM python:3.12.14-slim-bookworm@sha256:392307d22300de8b5986851a12d9176dfc0fc073e65bf6523ebd7dcbeb23564e
COPY --from=ghcr.io/astral-sh/uv:0.9.7 /uv /usr/local/bin/uv
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    UV_PROJECT_ENVIRONMENT=/opt/venv UV_PYTHON_DOWNLOADS=never UV_LINK_MODE=copy PATH=/opt/venv/bin:$PATH \
    SCAMWORLD_HOME=/scamworld SCAMWORLD_ENV_FILE=/config/.env SCAMWORLD_OPENWEIGHTS_ENV_FILE=/config/.env.openweights

# 1. System packages and fonts (the websites use Latin, CJK, Arabic, Thai, Indic and other scripts; git is imported by AgentLab).
RUN apt-get update \
 && apt-get install -y --no-install-recommends git ca-certificates fonts-noto-core fonts-noto-cjk fonts-noto-color-emoji fonts-freefont-ttf \
 && rm -rf /var/lib/apt/lists/*

# 2. Runtime dependencies from uv.lock (no analysis/dev groups), Chromium for Playwright 1.44, offline NLTK data.
WORKDIR /scamworld
COPY pyproject.toml uv.lock .python-version README.md ./
COPY vendor/ vendor/
RUN uv sync --frozen --no-default-groups --no-install-project \
 && python -m playwright install --with-deps chromium \
 && chmod -R a+rX /ms-playwright \
 && python -m nltk.downloader -d /usr/local/share/nltk_data punkt_tab \
 && chmod -R a+rX /usr/local/share/nltk_data \
 && rm -rf /var/lib/apt/lists/* /root/.cache

# 3. Package, configs, docs and examples, the release manifest, then the tasks (the largest layer, last).
COPY src/ src/
RUN uv sync --frozen --no-default-groups
COPY configs/ configs/
COPY docs/ docs/
COPY examples/ examples/
COPY LICENSE LICENSE-DATA DISCLAIMER.md ./
COPY release/ release/
COPY tasks/ tasks/

# 4. Writable state on the /runs volume: results/ and the library cache (.cache) link there; keys and endpoint files come
#    from /config. The task files are checked against the release manifest at build time.
RUN mkdir -p /runs /config \
 && ln -s /runs /scamworld/results \
 && ln -s /runs/.cache /scamworld/.cache \
 && chmod 1777 /runs \
 && chmod -R a+rX /scamworld \
 && scamworld check > /dev/null
VOLUME ["/runs"]
ENTRYPOINT ["scamworld"]
CMD ["tasks"]

# Pull the base image
FROM python:3.9 AS deps

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_EXTRA_INDEX_URL=https://download.pytorch.org/whl/cpu

WORKDIR /install

COPY requirements.txt ./
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Download the CLIP weights once the dependencies are installed
RUN python - <<'PY'
import os
import shutil
import time

import clip  # noqa: F401
import torch  # noqa: F401

download_root = os.path.expanduser("~/.cache/clip")

for attempt in range(5):
    try:
        clip.load("ViT-B/32", download_root=download_root)
    except RuntimeError:
        if attempt >= 4:
            raise
        shutil.rmtree(download_root, ignore_errors=True)
        time.sleep(3)
    else:
        break
PY

FROM python:3.9

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_EXTRA_INDEX_URL=https://download.pytorch.org/whl/cpu

RUN apt-get update -y && \
    apt-get install -y --no-install-recommends \
    git \
    default-jdk \
    netcat-openbsd \
    wget \
    gnupg \
    curl \
    && apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /code

# Reuse installed Python packages and cached CLIP weights from the deps stage
COPY --from=deps /usr/local /usr/local
COPY --from=deps /root/.cache/clip /root/.cache/clip

COPY . /code/

RUN chmod +x /code/entrypoint.sh

ENTRYPOINT ["/code/entrypoint.sh"]

CMD ["daphne", "analysis_service.asgi:application", "--port", "$PORT", "--bind", "0.0.0.0"]

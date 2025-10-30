# Pull the base image
FROM python:3.9

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_EXTRA_INDEX_URL=https://download.pytorch.org/whl/cpu

# Install necessary system dependencies
RUN apt-get update -y && \
  apt-get install -y \
  git \
  default-jdk \
  netcat-openbsd \
  wget \
  gnupg \
  curl \
  && apt-get clean && \
  rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /code

# Copy project
COPY . /code/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Download the CLIP model with retries to avoid partial downloads
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
    except RuntimeError as err:
        if attempt >= 4:
            raise
        shutil.rmtree(download_root, ignore_errors=True)
        time.sleep(3)
    else:
        break
PY

# Set execute permission for entrypoint.sh
RUN chmod +x /code/entrypoint.sh

ENTRYPOINT ["/code/entrypoint.sh"]

# Run the application
CMD ["daphne", "analysis_service.asgi:application", "--port", "$PORT", "--bind", "0.0.0.0"]

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

# Download the CLIP model
RUN python -c "import torch; import clip; clip.load('ViT-B/32')"

# Set execute permission for entrypoint.sh
RUN chmod +x /code/entrypoint.sh

ENTRYPOINT ["/code/entrypoint.sh"]

# Run the application
CMD ["daphne", "analysis_service.asgi:application", "--port", "$PORT", "--bind", "0.0.0.0"]

# ⬇️ CHANGED: Pulling from the official AWS ECR Public mirror instead of Docker Hub
FROM public.ecr.aws/docker/library/python:3.12-slim
WORKDIR /app

# Install system dependencies + libpq-dev to handle postgres binary fallbacks securely
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libffi-dev libpq-dev && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r /app/requirements.txt

COPY . /app
RUN apt-get update && apt-get install -y --no-install-recommends sed \
    && find /app/scripts -name "*.sh" -exec sed -i 's/\r$//' {} + \
    && chmod +x /app/scripts/*.sh

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

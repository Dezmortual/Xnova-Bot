FROM python:3.12-slim

WORKDIR /app

# Install dependencies first for better layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

# Cloud hosts set PORT env var; default to 5050
ENV PORT=5050
EXPOSE 5050

# Persist portfolio state in /data (mount volume if needed)
VOLUME ["/data"]
ENV STATE_DIR=/data

CMD ["python", "run.py"]

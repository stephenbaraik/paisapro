# ── Hugging Face Spaces Docker deployment ────────────────────────────────────
FROM python:3.12-slim

# System deps for numpy/scipy/statsmodels
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc g++ && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# HF Spaces uses port 7860
EXPOSE 7860

# Run with uvicorn — HF Spaces sets secrets as env vars automatically
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]

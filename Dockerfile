FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

WORKDIR /app

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY api.py .

# Expose port
EXPOSE 8080

# Run
CMD ["python", "api.py"]

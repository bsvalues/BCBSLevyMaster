# Dockerfile for SaaS Levy Calculation Application
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set work directory
WORKDIR /app

# Install dependencies
COPY requirements.txt /app/
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy project
COPY . /app/

# Expose port
EXPOSE 8080

# Command to run the app (adjust as needed for gunicorn/flask)
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:8080", "--workers=3"]

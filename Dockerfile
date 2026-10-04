```dockerfile
FROM python:3.12-slim

# Install Java
RUN apt-get update \
    && apt-get install -y openjdk-17-jdk \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy the complete project
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r python/requirements.txt

# Allow Python to find app.py, database.py and java_bridge.py
ENV PYTHONPATH=/app/python

# Start Flask using Gunicorn
CMD gunicorn --bind 0.0.0.0:$PORT --chdir python app:app
```

FROM python:3.12-slim

# Install Java JDK
RUN apt-get update \
    && apt-get install -y openjdk-17-jdk \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy project
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r python/requirements.txt

# Flask needs to be able to find the Python modules
ENV PYTHONPATH=/app/python

# Render provides the PORT environment variable
CMD gunicorn --bind 0.0.0.0:$PORT --chdir python app:app

FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y openjdk-17-jdk \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r python/requirements.txt

ENV PYTHONPATH=/app/python

CMD gunicorn --bind 0.0.0.0:$PORT --chdir python app:app

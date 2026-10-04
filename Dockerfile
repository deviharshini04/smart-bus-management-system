FROM eclipse-temurin:17-jdk-jammy

RUN apt-get update \
    && apt-get install -y python3 python3-pip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . .

RUN pip3 install --no-cache-dir -r python/requirements.txt

ENV PYTHONPATH=/app/python

CMD gunicorn --bind 0.0.0.0:$PORT --chdir python app:app

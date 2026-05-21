FROM python:3.15.0b1-slim-trixie

WORKDIR /app

COPY requirements.txt /app

RUN apt-get update && apt-get install gcc -y && pip install -r requirements.txt --break-system-packages

ENV TETON_DISCORD_TOKEN=
ENV TETON_SERVER_IP=
ENV TETON_CHANNEL_ID=

COPY main.py /app

ENTRYPOINT [ "python", "main.py" ]

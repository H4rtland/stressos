FROM python:3-slim

WORKDIR /app
COPY mkobjects2.py /app
COPY requirements.txt /app

RUN pip install --upgrade pip
RUN pip install -r requirements.txt


ENTRYPOINT python mkobjects2.py

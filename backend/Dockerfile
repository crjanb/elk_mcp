FROM python:3.11-slim

WORKDIR /app
COPY app.py /app/app.py
COPY requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir -r /app/requirements.txt

ENV LOG_PATH=/var/log/app/app.log
ENV SERVICE_NAME=dummy-backend

CMD ["python", "/app/app.py"]

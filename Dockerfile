FROM python:3.13-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV UC_CONFIG_HOME=/config
ENV UC_LOG_LEVEL=DEBUG

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY driver.json .
COPY intg-tivo ./intg-tivo

CMD ["python", "./intg-tivo/driver.py"]

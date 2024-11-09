FROM python:3.11-slim

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY ./product_harvester /app/product_harvester
COPY ./server /app/server

WORKDIR /app/server

EXPOSE 8080

ENTRYPOINT ["fastapi", "run", "server.py", "--port", "8080"]

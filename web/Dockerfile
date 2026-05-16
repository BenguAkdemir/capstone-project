FROM python:3.12-slim

WORKDIR /app

COPY web/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY web/ ./web/
COPY data/sample/request_example.json ./data/sample/request_example.json

WORKDIR /app/web

ENV WEB_BACKEND_URL=http://backend:8000

EXPOSE 3000

CMD ["python", "app.py"]

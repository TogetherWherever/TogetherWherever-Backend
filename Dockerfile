FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY ./app ./app

CMD ["sh", "-c", "python -m app.database.create_db && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
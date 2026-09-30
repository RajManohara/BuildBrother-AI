FROM python:3.12-slim
WORKDIR /app
COPY requirements.lock.txt .
RUN pip install --no-cache-dir -r requirements.lock.txt
RUN useradd --create-home appuser
COPY app ./app
COPY migrations ./migrations
COPY alembic.ini .
USER appuser
EXPOSE 8000
CMD ["sh", "-c", "python -m app.bootstrap && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]

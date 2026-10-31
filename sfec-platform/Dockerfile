FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATABASE_URL=sqlite:////data/sfec.db

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app

# Root par défaut : les disques persistants des hébergeurs (ex. Render) sont montés en root.
RUN mkdir /data
VOLUME /data
EXPOSE 8000

# Un seul worker : la synchronisation automatique tourne dans le processus.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]

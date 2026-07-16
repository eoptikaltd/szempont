FROM python:3.12-slim
WORKDIR /srv
COPY pyproject.toml ./
COPY pricing/ pricing/
COPY ingest/ ingest/
COPY app/ app/
RUN pip install --no-cache-dir flask gunicorn google-cloud-bigquery
ENV PORT=8080 SZEMPONT_CATALOG=bq
CMD exec gunicorn --bind :$PORT --workers 2 app.app:app

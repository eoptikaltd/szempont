FROM python:3.12-slim
WORKDIR /srv
COPY pyproject.toml ./
COPY app/requirements.txt app/requirements.txt
RUN pip install --no-cache-dir -r app/requirements.txt
# Every top-level package app.app imports (incl. lazily, e.g. ingest.source in
# bq mode) must be COPYed here — guarded by tests/test_dockerfile.py.
COPY pricing/ pricing/
COPY ingest/ ingest/
COPY quotes/ quotes/
COPY orders/ orders/
COPY vendors/ vendors/
COPY iris/ iris/
COPY app/ app/
ENV PORT=8080 SZEMPONT_CATALOG=bq
CMD exec gunicorn --bind :$PORT --workers 2 app.app:app

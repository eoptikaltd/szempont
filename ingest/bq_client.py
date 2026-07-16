"""Thin BigQuery access layer for the ingest job.

Isolated here so run_ingest() stays unit-testable. Every query/load job
carries labels tool=szempont. Writes only within the szempont dataset.
"""

from __future__ import annotations

from decimal import Decimal

BQ_LABELS = {"tool": "szempont"}


class BQClient:  # pragma: no cover — exercised in staging against real BQ
    def __init__(self, client):
        self.client = client

    def delete_version(self, table: str, catalog_version: str) -> None:
        from google.cloud import bigquery
        job = self.client.query(
            f"DELETE FROM `{table}` WHERE catalog_version = @v",
            job_config=bigquery.QueryJobConfig(
                labels=BQ_LABELS,
                query_parameters=[
                    bigquery.ScalarQueryParameter("v", "STRING", catalog_version)
                ],
            ),
        )
        job.result()

    def load_rows(self, table: str, rows: list[dict], labels=None) -> None:
        # Batch load job, NOT insert_rows_json: streamed rows sit in the
        # streaming buffer and cannot be DELETEd for up to ~90 min, which
        # would break the delete-then-load idempotency contract on re-ingest.
        if not rows:
            return
        from google.cloud import bigquery
        job = self.client.load_table_from_json(
            rows, table,
            job_config=bigquery.LoadJobConfig(
                labels=labels or BQ_LABELS,
                write_disposition="WRITE_APPEND",
            ),
        )
        job.result()
        if job.errors:
            raise RuntimeError(f"BQ load errors on {table}: {job.errors[:5]}")

    def fetch_prices(self, supplier: str, exclude_version: str) -> dict[str, Decimal]:
        from google.cloud import bigquery
        sql = """
        SELECT sku, retail_net_huf
        FROM `szempont.lens_catalog`
        WHERE supplier = @s AND catalog_version != @v
        QUALIFY ROW_NUMBER() OVER (
            PARTITION BY sku ORDER BY _ingested_at DESC) = 1
        """
        job = self.client.query(sql, job_config=bigquery.QueryJobConfig(
            labels=BQ_LABELS,
            query_parameters=[
                bigquery.ScalarQueryParameter("s", "STRING", supplier),
                bigquery.ScalarQueryParameter("v", "STRING", exclude_version),
            ],
        ))
        return {r["sku"]: float(r["retail_net_huf"]) for r in job.result()}

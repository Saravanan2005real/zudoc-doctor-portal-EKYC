"""List vaulted documents per doctor."""
import sys

import psycopg

DSN = "host=localhost port=5433 user=postgres password=dinesh_2006 dbname=doctor_verification_db"

public_id = sys.argv[1] if len(sys.argv) > 1 else None

with psycopg.connect(DSN) as conn:
    sql = (
        "select d.public_id, dd.document_id, dd.document_type, dd.version, dd.uploaded_at "
        "from doctor_documents dd join doctors d on d.id = dd.doctor_id "
        "where dd.is_latest = true and dd.deleted_at is null"
    )
    params = []
    if public_id:
        sql += " and d.public_id = %s"
        params.append(public_id)
    sql += " order by d.public_id, dd.document_type"
    for row in conn.execute(sql, params).fetchall():
        print(row)

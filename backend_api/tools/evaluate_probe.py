"""Diagnostic: run the Step 4 eKYC evaluation exactly like the API does.

Usage (from python_backend):
    .venv/Scripts/python.exe tools/evaluate_probe.py <doctor_public_id> [doc_id ...]
"""
import json
import os
import sys

os.environ.setdefault("TF_USE_LEGACY_KERAS", "1")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config.config import settings
from dependencies import get_ekyc_evaluation_service

# Registering every mapper keeps SQLAlchemy relationships resolvable.
import entities.doctor, entities.license, entities.qualification, entities.clinic  # noqa: E401,F401
import entities.document, entities.history, entities.admin, entities.otp  # noqa: E401,F401
import entities.refresh_token, entities.job, entities.ocr_result, entities.admin_action  # noqa: E401,F401
import entities.note, entities.flag, entities.audit, entities.dlq, entities.prescription  # noqa: E401,F401


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        return
    public_id = sys.argv[1]
    doc_ids = sys.argv[2:] or None

    engine = create_engine(settings.database_url)
    db = sessionmaker(bind=engine)()
    try:
        service = get_ekyc_evaluation_service(db)
        result = service.Evaluate(public_id, doc_ids)
    finally:
        db.close()

    print("decision:", result["status"])
    print("message:", result["message"])
    for stage in result["stages"]:
        print(f"  [{stage['id']}] {stage['status']:<7} {stage['title']}: {stage['detail']}")
    for doc in result["documents"]:
        print(json.dumps({
            "type": doc.get("document_type"),
            "status": doc.get("status"),
            "confidence": doc.get("ocr_confidence"),
            "face": doc.get("face_image_url"),
            "name": (doc.get("parsed_fields") or {}).get("name"),
            "error": doc.get("error"),
        }, indent=2))


if __name__ == "__main__":
    main()

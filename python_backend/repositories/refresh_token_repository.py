from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session
from entities.refresh_token import RefreshToken

class RefreshTokenRepository:
    def __init__(self, db: Session):
        self.db = db

    def Create(self, token: RefreshToken) -> None:
        self.db.add(token)
        self.db.commit()
        self.db.refresh(token)

    def FindByHash(self, token_hash: str) -> Optional[RefreshToken]:
        return self.db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()

    def Revoke(self, token_hash: str) -> None:
        self.db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).update({"is_revoked": True})
        self.db.commit()

    def RevokeAllForDoctor(self, doctor_id: UUID) -> None:
        self.db.query(RefreshToken).filter(RefreshToken.doctor_id == doctor_id).update({"is_revoked": True})
        self.db.commit()

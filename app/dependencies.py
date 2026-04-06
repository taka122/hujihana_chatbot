from __future__ import annotations

import secrets
from fastapi import Header, HTTPException, status, Depends
from app.config import get_settings, Settings

def verify_clinic_key(
    x_clinic_key: str | None = Header(None),
    settings: Settings = Depends(get_settings)
):
    # CLINIC_PASSWORD が設定されていない場合は、セキュリティなし（開発環境用など）とみなす
    if not settings.clinic_password:
        return

    # キーが送られていない場合
    if not x_clinic_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Clinic key missing",
            headers={"WWW-Authenticate": "X-Clinic-Key"},
        )

    # 定数時間比較でパスワードをチェック（タイミング攻撃対策）
    if not secrets.compare_digest(x_clinic_key, settings.clinic_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid clinic key",
            headers={"WWW-Authenticate": "X-Clinic-Key"},
        )

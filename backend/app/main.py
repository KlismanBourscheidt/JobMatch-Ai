
from functools import lru_cache

import jwt
from jwt import PyJWKClient
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client

from .config import Settings


# ==========================================
# CONFIGURACOES
# ==========================================

@lru_cache
def settings():
    return Settings()


app = FastAPI(
    title="JobMatch AI API",
    version="0.4.0"
)


# ==========================================
# CORS
# ==========================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings().frontend_origin.rstrip("/")
    ],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["Authorization", "Content-Type"],
)


# ==========================================
# CHAVES PUBLICAS DO SUPABASE
# ==========================================

@lru_cache
def jwks_client():
    supabase_url = settings().supabase_url.rstrip("/")

    return PyJWKClient(
        f"{supabase_url}/auth/v1/.well-known/jwks.json"
    )


# ==========================================
# AUTENTICACAO
# ==========================================

def current_user(request: Request):
    authorization = request.headers.get("authorization")

    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Token ausente"
        )

    scheme, separator, token = authorization.partition(" ")

    if (
        not separator
        or scheme.lower() != "bearer"
        or not token.strip()
    ):
        raise HTTPException(
            status_code=401,
            detail="Cabeçalho Authorization inválido"
        )

    token = token.strip()
    s = settings()

    try:
        header = jwt.get_unverified_header(token)

        if header.get("alg") != "ES256":
            raise ValueError("Algoritmo JWT não permitido")

        signing_key = jwks_client().get_signing_key_from_jwt(
            token
        )

        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256"],
            audience="authenticated",
            issuer=s.supabase_url.rstrip("/") + "/auth/v1",
        )

    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Token inválido ou expirado"
        )

    user_email = payload.get("email", "").lower()

    if user_email != s.allowed_email.lower():
        raise HTTPException(
            status_code=403,
            detail="Conta não autorizada"
        )

    return payload


# ==========================================
# HEALTH CHECK
# ==========================================

@app.get("/health")
def health():
    return {"status": "ok"}


# ==========================================
# LISTAGEM DE VAGAS
# ==========================================

@app.get("/jobs")
def jobs(user=Depends(current_user)):
    s = settings()

    db = create_client(
        s.supabase_url,
        s.supabase_service_role_key
    )

    result = (
        db.table("jobs")
        .select(
            "id,title,company,location,"
            "remote,score,status,url,created_at,"
            "matched_skills,missing_skills,"
            "required_skills,study_recommendations"
        )
        .order("score", desc=True)
        .limit(500)
        .execute()
    )

    return {
        "jobs": result.data or [],
        "minimum_match_score": 50,
        "highlight_match_score": 80
    }

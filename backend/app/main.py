from functools import lru_cache
from typing import Annotated
import httpx
import jwt
from jwt import PyJWKClient
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client
from .config import Settings

@lru_cache
def settings():
    return Settings()

app = FastAPI(title='JobMatch AI API', version='0.1.0')
# Configure CORS at startup from environment, not with wildcard origins.
@app.on_event('startup')
def startup():
    s = settings()
    app.add_middleware(CORSMiddleware, allow_origins=[s.frontend_origin.rstrip('/')],
                       allow_credentials=False, allow_methods=['GET'], allow_headers=['Authorization'])

@lru_cache
def jwks_client():
    return PyJWKClient(settings().supabase_url.rstrip('/') + '/auth/v1/.well-known/jwks.json')

def current_user(authorization: Annotated[str | None, Header()] = None):
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(401, 'Token ausente')
    token = authorization.removeprefix('Bearer ').strip()
    s = settings()
    try:
        header = jwt.get_unverified_header(token)
        if header.get('alg') != 'ES256':
            raise ValueError('Somente tokens ES256 são aceitos. Configure chave assimétrica ES256 no Supabase.')
        key = jwks_client().get_signing_key_from_jwt(token)
        payload = jwt.decode(token, key.key, algorithms=['ES256'],
                             audience='authenticated',
                             issuer=s.supabase_url.rstrip('/') + '/auth/v1/')
    except Exception:
        raise HTTPException(401, 'Token inválido ou expirado')
    if payload.get('email', '').lower() != s.allowed_email.lower():
        raise HTTPException(403, 'Conta não autorizada')
    return payload

@app.get('/health')
def health():
    return {'status': 'ok'}

@app.get('/jobs')
def jobs(user=Depends(current_user)):
    s = settings()
    db = create_client(s.supabase_url, s.supabase_service_role_key)
    result = db.table('jobs').select('id,title,company,location,remote,score,status,url,created_at').order('score',desc=True).limit(500).execute()
    return {'jobs': result.data or [], 'minimum_match_score': 80}

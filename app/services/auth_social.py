import logging
import httpx
import jwt # PyJWT
from urllib.parse import urlencode
from app.config import settings
from fastapi import HTTPException

logger = logging.getLogger(__name__)

class SocialAuthService:
    @staticmethod
    def get_google_auth_url(redirect_uri: str, state: str):
        params = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "access_type": "offline",
            "state": state,
            "prompt": "select_account",
        }
        return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"

    @staticmethod
    async def exchange_google_code(code: str, redirect_uri: str):
        if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
            raise HTTPException(status_code=500, detail="Google OAuth client credentials are not configured")
        
        token_url = "https://oauth2.googleapis.com/token"
        data = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        }
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.post(
                    token_url, 
                    data=data, 
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                resp.raise_for_status()
            except httpx.HTTPStatusError as e:
                # Try to extract error detail from response
                detail = None
                try:
                    detail = resp.json()
                except Exception:
                    detail = resp.text
                logger.error(f"Google token exchange failed: {e.response.status_code} - {detail}")
                # Classify common errors
                if isinstance(detail, dict):
                    err = detail.get("error")
                    desc = detail.get("error_description")
                    if err in ("invalid_client", "unauthorized_client"):
                        raise HTTPException(status_code=401, detail="Invalid Google client credentials")
                    if err == "invalid_grant":
                        raise HTTPException(status_code=401, detail="Invalid authorization code or redirect_uri mismatch")
                    raise HTTPException(status_code=401, detail=f"Google token error: {err} - {desc}")
                raise HTTPException(status_code=401, detail="Google token exchange unauthorized")
            except Exception as e:
                logger.error(f"Google token request error: {str(e)}")
                raise HTTPException(status_code=500, detail="Google token request failed")
            
            token_data = resp.json()
            
            # Get User Info
            # Option 1: Parse ID Token (if available and verify signature)
            # Option 2: Call UserInfo Endpoint
            
            access_token = token_data["access_token"]
            try:
                userinfo_resp = await client.get(
                    "https://www.googleapis.com/oauth2/v3/userinfo",
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                userinfo_resp.raise_for_status()
            except httpx.HTTPStatusError as e:
                logger.error(f"Google userinfo failed: {e.response.status_code} - {e.response.text}")
                raise HTTPException(status_code=401, detail="Failed to fetch Google user info")
            
            return userinfo_resp.json()

    # Keep legacy/Apple support if needed, or implement manual Apple flow later
    # For now, we focus on fixing Google manually to bypass Session middleware issues.

import logging
import httpx
import jwt # PyJWT
from urllib.parse import urlencode
from app.config import settings

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
        token_url = "https://oauth2.googleapis.com/token"
        data = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        }
        
        async with httpx.AsyncClient() as client:
            resp = await client.post(token_url, data=data)
            resp.raise_for_status()
            token_data = resp.json()
            
            # Get User Info
            # Option 1: Parse ID Token (if available and verify signature)
            # Option 2: Call UserInfo Endpoint
            
            access_token = token_data["access_token"]
            userinfo_resp = await client.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            userinfo_resp.raise_for_status()
            return userinfo_resp.json()

    # Keep legacy/Apple support if needed, or implement manual Apple flow later
    # For now, we focus on fixing Google manually to bypass Session middleware issues.


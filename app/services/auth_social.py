import logging
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
import jwt
from jwt import PyJWKClient
from app.config import settings

logger = logging.getLogger(__name__)

class SocialAuthService:
    @staticmethod
    def verify_google_token(token: str) -> dict:
        try:
            # Specify the CLIENT_ID of the app that accesses the backend:
            id_info = id_token.verify_oauth2_token(
                token, 
                google_requests.Request(), 
                settings.GOOGLE_CLIENT_ID if settings.GOOGLE_CLIENT_ID else None
            )

            # ID token is valid. Get the user's Google Account ID from the decoded token.
            # userid = id_info['sub']
            # email = id_info['email']
            return id_info
        except ValueError as e:
            # Invalid token
            logger.error(f"Google token verification failed: {e}")
            raise ValueError("Invalid Google token")
        except Exception as e:
            logger.error(f"Google auth error: {e}")
            raise e

    @staticmethod
    def verify_apple_token(token: str) -> dict:
        try:
            # Apple keys URL
            apple_keys_url = "https://appleid.apple.com/auth/keys"
            
            jwks_client = PyJWKClient(apple_keys_url)
            signing_key = jwks_client.get_signing_key_from_jwt(token)
            
            data = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=settings.APPLE_CLIENT_ID if settings.APPLE_CLIENT_ID else None,
                options={"verify_exp": True}
            )
            
            return data
        except jwt.exceptions.InvalidTokenError as e:
            logger.error(f"Apple token verification failed: {e}")
            raise ValueError("Invalid Apple token")
        except Exception as e:
            logger.error(f"Apple auth error: {e}")
            raise e

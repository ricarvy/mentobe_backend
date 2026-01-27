import logging
from authlib.integrations.starlette_client import OAuth
from app.config import settings

logger = logging.getLogger(__name__)

# Initialize OAuth
oauth = OAuth()

# Google Configuration
if settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET:
    oauth.register(
        name='google',
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={
            'scope': 'openid email profile'
        }
    )

# Apple Configuration
if settings.APPLE_CLIENT_ID and settings.APPLE_CLIENT_SECRET:
    oauth.register(
        name='apple',
        client_id=settings.APPLE_CLIENT_ID,
        client_secret=settings.APPLE_CLIENT_SECRET,
        server_metadata_url='https://appleid.apple.com/.well-known/openid-configuration',
        client_kwargs={
            'scope': 'name email',
            'response_mode': 'form_post'
        }
    )

class SocialAuthService:
    @staticmethod
    def get_oauth_client(provider_name: str):
        client = oauth.create_client(provider_name)
        if not client:
            raise ValueError(f"Provider {provider_name} not found or not configured")
        return client

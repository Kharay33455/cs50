"""
WSGI config for cs50 project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/wsgi/
"""

import os

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
# To manage sessions and cookies
from channels.auth import AuthMiddleware
from channels.sessions import SessionMiddlewareStack
import chat.routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cs50.settings')

application = ProtocolTypeRouter({
    'http' : get_asgi_application(),
    'websocket' : SessionMiddlewareStack(
      AuthMiddleware(
        URLRouter(
            chat.routing.websocket_urlpatterns
        )
    ))
})

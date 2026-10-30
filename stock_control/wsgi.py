# Rôle : crée l'objet application, point d'entrée WSGI du projet pour le serveur web.
# Liens : désigné par WSGI_APPLICATION dans stock_control/settings.py, réglages qu'il charge lui-même.
"""
WSGI config for stock_control project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stock_control.settings')

application = get_wsgi_application()

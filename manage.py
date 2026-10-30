#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


# Rôle : choisit stock_control.settings par défaut et exécute la commande Django de la ligne de commande.
# Liens : point d'entrée de « python manage.py ... » ; exécute par exemple apps/core/management/commands/.
def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stock_control.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()

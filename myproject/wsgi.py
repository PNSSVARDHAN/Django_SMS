import os
import shutil
import django
from django.core.wsgi import get_wsgi_application
from django.core.management import call_command
import logging

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')

application = get_wsgi_application()

# Vercel requires this alias
app = application

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logging.debug("WSGI application initialized.")

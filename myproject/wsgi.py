"""
WSGI config for myproject project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/wsgi/
"""

import os
import shutil
from django.core.wsgi import get_wsgi_application

# Set the default settings module for Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')

# Paths for the original and temporary SQLite database
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # Adjust if needed
ORIGINAL_DB_PATH = os.path.join(BASE_DIR, 'db.sqlite3')
TEMP_DB_PATH = '/tmp/db.sqlite3'

# Copy the database to /tmp if it exists and is not already there
if os.path.exists(ORIGINAL_DB_PATH) and not os.path.exists(TEMP_DB_PATH):
    print(f"Copying database from {ORIGINAL_DB_PATH} to {TEMP_DB_PATH}")
    shutil.copy(ORIGINAL_DB_PATH, TEMP_DB_PATH)
elif not os.path.exists(TEMP_DB_PATH):
    print(f"No database found at {ORIGINAL_DB_PATH}. Initializing new database at {TEMP_DB_PATH}.")
    with open(TEMP_DB_PATH, 'w'):
        pass

# Get the WSGI application
application = get_wsgi_application()

# Alias for Vercel
app = application

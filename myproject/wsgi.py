import os
import shutil
import django
from django.core.wsgi import get_wsgi_application
from django.core.management import call_command

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ORIGINAL_DB_PATH = os.path.join(BASE_DIR, 'db.sqlite3')
TEMP_DB_PATH = '/tmp/db.sqlite3'

# Ensure the database is copied or initialized
try:
    if os.path.exists(ORIGINAL_DB_PATH) and not os.path.exists(TEMP_DB_PATH):
        print(f"Copying database from {ORIGINAL_DB_PATH} to {TEMP_DB_PATH}")
        shutil.copy(ORIGINAL_DB_PATH, TEMP_DB_PATH)
    elif not os.path.exists(TEMP_DB_PATH):
        print("No database found. Running migrations...")
        django.setup()
        call_command('migrate', interactive=False)
except Exception as e:
    print(f"Error during database setup: {e}")

application = get_wsgi_application()

# Vercel requires this alias
app = application

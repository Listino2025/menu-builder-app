import os
import sys

# Aggiungi la directory root al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import dotenv se disponibile (in locale)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from app import create_app

# Fix per PostgreSQL URL su Vercel
db_url = os.environ.get('DATABASE_URL')
if db_url and db_url.startswith('postgres://'):
    os.environ['DATABASE_URL'] = db_url.replace('postgres://', 'postgresql://', 1)

app = create_app()

# Per Vercel
def handler(request):
    return app
from app import create_app
import os

# Fix per PostgreSQL URL su Vercel
db_url = os.environ.get('DATABASE_URL')
if db_url and db_url.startswith('postgres://'):
    os.environ['DATABASE_URL'] = db_url.replace('postgres://', 'postgresql://', 1)

app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
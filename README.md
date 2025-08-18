# Menu Builder - Progressive Web App

Una Progressive Web App per creare panini personalizzati e menu con analisi dei costi in tempo reale e calcolo dei profitti. Sviluppata per semplificare la pianificazione del menu e la gestione dei costi.

## Funzionalità

### Funzionalità Principali
- **Gestione Ingredienti**: Operazioni CRUD complete con importazione/esportazione CSV
- **Compositore Panini**: Interfaccia drag & drop per creare panini personalizzati
- **Creatore Menu**: Combinare panini con contorni e bevande
- **Calcolo Costi in Tempo Reale**: Calcolo automatico di costi e margini di profitto
- **Dashboard Analytics**: KPI, grafici e insights aziendali
- **Sistema Reporting**: Esportazione dati in PDF, CSV ed Excel

### Funzionalità Tecniche
- **Progressive Web App**: Funzionalità offline, installabile su dispositivi mobili
- **Design Responsive**: UI mobile-first con interazioni touch-friendly
- **Sistema Autenticazione**: Login sicuro con controllo accessi basato su ruoli
- **API RESTful**: Endpoint JSON per integrazioni frontend
- **Integrazione Database**: SQLite per sviluppo, PostgreSQL per produzione
- **Sicurezza**: Protezione CSRF, validazione input, header sicuri

### Ruoli Utente
- **Admin**: Accesso completo al sistema, gestione utenti, reporting completo
- **Manager**: Creazione prodotti, gestione ingredienti, accesso analytics
- **User**: Creazione prodotti base e accesso dati personali

## Installazione e Setup

### Prerequisiti
- Python 3.8+
- pip (gestore pacchetti Python)
- Git

### Guida Rapida

1. **Clona il repository**
   ```bash
   git clone <repository-url>
   cd menu-builder-app
   ```

2. **Crea e attiva ambiente virtuale**
   ```bash
   python -m venv venv
   
   # Windows
   venv\Scripts\activate
   
   # macOS/Linux
   source venv/bin/activate
   ```

3. **Installa dipendenze**
   ```bash
   pip install -r requirements.txt
   ```

4. **Imposta variabili ambiente (opzionale)**
   ```bash
   # Windows
   set FLASK_ENV=development
   set SECRET_KEY=your-secret-key-here
   
   # macOS/Linux
   export FLASK_ENV=development
   export SECRET_KEY=your-secret-key-here
   ```

5. **Avvia l'applicazione**
   ```bash
   python run.py
   ```

6. **Accedi all'applicazione**
   - Apri browser su `http://localhost:5000`
   - Login admin predefinito: `admin` / `admin123`

## Setup Progressive Web App

### Installazione Mobile
1. Apri l'app nel browser mobile
2. Cerca il prompt "Aggiungi alla schermata home"
3. Segui i passaggi di installazione
4. Accedi all'app dalla schermata home come app nativa

### Funzionalità Offline
- Risorse statiche in cache per visualizzazione offline
- Dati moduli memorizzati sincronizzati al ripristino connessione
- Sincronizzazione in background per operazioni critiche
- Pagine di fallback offline

## Struttura Progetto

```
menu-builder-app/
├── app/
│   ├── __init__.py              # Factory Flask app
│   ├── models.py                # Modelli database
│   ├── auth/                    # Blueprint autenticazione
│   ├── routes/                  # Route principali applicazione
│   ├── api/                     # Endpoint API REST
│   ├── static/                  # Risorse statiche
│   └── templates/               # Template Jinja2
├── config.py                    # Impostazioni configurazione
├── requirements.txt             # Dipendenze Python
├── run.py                       # Punto di ingresso applicazione
└── README.md                    # Questo file
```

## Schema Database

### Tabelle Principali
- **users**: Account utenti con permessi basati su ruoli
- **ingredients**: Catalogo master ingredienti con prezzi
- **products**: Panini e menu con calcoli costi
- **product_ingredients**: Relazione molti-a-molti con quantità

### Relazioni Chiave
- I prodotti appartengono agli utenti (created_by)
- I prodotti contengono più ingredienti con quantità
- I menu referenziano prodotti panino
- Tutte le relazioni mantengono integrità referenziale

## Formato Importazione CSV

### Importazione Ingredienti
```csv
wrin_code,name,category,price_per_unit,unit_type,temperature_zone
BUN001,Panino Classico,BASE,0.25,pieces,AMBIENT
BEEF001,Hamburger Manzo,PROTEIN,2.50,pieces,FROZEN
CHED001,Formaggio Cheddar,CHEESE,0.30,slices,CHILLED
```

### Categorie Supportate
- **BASE**: Panini e prodotti da pane
- **PROTEIN**: Carne, pesce, proteine vegetariane
- **CHEESE**: Tutte le varietà di formaggi
- **VEGETABLE**: Verdure fresche e condimenti
- **SAUCE**: Salse e condimenti
- **SIDE**: Patatine, anelli cipolla, ecc.
- **DRINK**: Bevande
- **OTHER**: Articoli vari

## Configurazione

### Variabili Ambiente
```bash
FLASK_ENV=development|production
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///menubuilder.db
PORT=5000
```

### Impostazioni Sicurezza
- Protezione CSRF abilitata
- Hash password sicuri (bcrypt)
- Timeout sessione (30 minuti)
- Rate limiting per tentativi login
- Header sicurezza (HSTS, CSP, ecc.)

## Documentazione API

### Endpoint Autenticazione
- `POST /auth/login` - Login utente
- `POST /auth/logout` - Logout utente
- `POST /auth/register` - Registra nuovo utente (solo admin)

### Endpoint Ingredienti
- `GET /api/ingredients` - Elenca tutti gli ingredienti
- `GET /api/ingredients/categories` - Ottieni categorie ingredienti
- `POST /ingredients` - Crea ingrediente (manager+)
- `PUT /ingredients/<id>` - Aggiorna ingrediente (manager+)
- `DELETE /ingredients/<id>` - Elimina ingrediente (manager+)

### Endpoint Prodotti
- `GET /api/products` - Elenca prodotti utente
- `POST /api/products` - Crea nuovo prodotto
- `PUT /api/products/<id>` - Aggiorna prodotto
- `GET /api/products/<id>/cost` - Calcola costo prodotto

### Endpoint Analytics
- `GET /api/analytics/profit-trend` - Dati trend profitti
- `GET /api/analytics/category-distribution` - Statistiche uso categorie

## Sviluppo

### Esecuzione Test
```bash
pip install pytest pytest-flask
pytest
```

### Stile Codice
```bash
pip install black flake8
black .
flake8
```

### Migrazioni Database
```bash
flask db init
flask db migrate -m "Descrizione"
flask db upgrade
```

## Deploy

### Deploy Vercel
```bash
npm i -g vercel
vercel --prod
```

### Deploy Manuale
```bash
pip install gunicorn
export FLASK_ENV=production
gunicorn -w 4 -b 0.0.0.0:8000 run:app
```

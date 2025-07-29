import os
import sys
from flask import Flask, send_from_directory, session
from dotenv import load_dotenv

# Add current directory to Python path for module imports
project_root = os.path.abspath(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import bank.py and user.py directly as modules
import bank
import user

# Access db and bank_bp from the imported bank module
from bank import db, bank_bp

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__, static_folder='static')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'a_very_secret_key_that_should_be_in_env')

app.register_blueprint(bank_bp, url_prefix='/api')

# Configure database - Turso or fallback to SQLite
TURSO_DATABASE_URL = os.environ.get('TURSO_DATABASE_URL')
TURSO_AUTH_TOKEN = os.environ.get('TURSO_AUTH_TOKEN')

if TURSO_DATABASE_URL and TURSO_AUTH_TOKEN:
    # Use Turso database
    database_url = f'sqlite+{TURSO_DATABASE_URL}?secure=true'
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'connect_args': {
            'auth_token': TURSO_AUTH_TOKEN,
            'check_same_thread': False
        }
    }
else:
    # Fallback to local SQLite
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

with app.app_context():
    db.create_all()

@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')



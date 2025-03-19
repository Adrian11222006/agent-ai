from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from research_agent import ResearchAgent
import os
from datetime import datetime
import logging

# Konfiguracja logowania
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Konfiguracja
CACHE_DIR = os.path.join(os.path.dirname(__file__), ".cache")
agent = ResearchAgent(cache_dir=CACHE_DIR)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    """
    Endpoint do wykonywania wyszukiwań.
    Oczekuje JSON z polem 'query'.
    """
    try:
        data = request.get_json()
        query = data.get('query', '').strip() if data else None
        
        logger.info(f"Otrzymano zapytanie: {query}")
        
        if not query:
            logger.warning("Otrzymano puste zapytanie")
            return jsonify({
                'success': False,
                'error': 'Brak zapytania',
                'timestamp': datetime.now().isoformat()
            }), 400

        logger.info("Rozpoczynam wyszukiwanie...")
        results = agent.research(query)
        logger.info("Wyszukiwanie zakończone")
        
        return jsonify(results)
        
    except Exception as e:
        logger.error(f"Wystąpił błąd: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/health')
def health():
    """Endpoint do sprawdzania stanu aplikacji."""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat()
    })

if __name__ == '__main__':
    # Upewnij się, że katalog cache istnieje
    os.makedirs(CACHE_DIR, exist_ok=True)
    
    logger.info("Uruchamiam serwer Flask...")
    
    # Uruchom aplikację
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True
    )

from flask import Flask, render_template, request, jsonify
from research_agent import ResearchAgent
import time
import logging
from logging.handlers import RotatingFileHandler
import os
import sys

# Konfiguracja loggera
if not os.path.exists('logs'):
    os.makedirs('logs')

handler = RotatingFileHandler('logs/app.log', maxBytes=10000, backupCount=3)
handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
))
handler.setLevel(logging.INFO)

# Inicjalizacja aplikacji
app = Flask(__name__)
app.logger.addHandler(handler)
app.logger.setLevel(logging.INFO)
app.logger.info('Research Agent startup')

# Inicjalizacja agenta
agent = ResearchAgent()

@app.route('/')
def index():
    """Strona główna."""
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    """
    Endpoint do wyszukiwania.
    Przyjmuje zapytanie w formacie JSON i zwraca wyniki wyszukiwania.
    """
    try:
        # Pobierz zapytanie z JSON
        data = request.get_json()
        if not data or 'query' not in data:
            return jsonify({
                'error': 'Brak zapytania w żądaniu',
                'execution_time': 0
            }), 400
            
        query = data['query'].strip()
        
        if not query:
            return jsonify({
                'error': 'Zapytanie nie może być puste',
                'execution_time': 0
            }), 400
            
        # Zmierz czas wykonania
        start_time = time.time()
        
        # Wykonaj wyszukiwanie
        summary, sources = agent.process_query(query)
        
        # Oblicz czas wykonania
        execution_time = round(time.time() - start_time, 2)
        
        app.logger.info(f'Successful search for query: "{query}" in {execution_time}s')
        
        return jsonify({
            'summary': summary,
            'sources': sources,
            'execution_time': execution_time
        })
        
    except Exception as e:
        app.logger.error(f'Error during search: {str(e)}')
        return jsonify({
            'error': 'Wystąpił błąd podczas wyszukiwania',
            'details': str(e),
            'execution_time': 0
        }), 500

def run_console():
    print("Agent Badawczy - Wersja konsolowa")
    print("Wpisz 'exit' aby zakończyć")
    
    while True:
        try:
            query = input("\nO co chcesz się dowiedzieć? ").strip()
            
            if query.lower() == 'exit':
                print("Do widzenia!")
                break
            
            if not query:
                print("Proszę wpisać zapytanie.")
                continue
            
            start_time = time.time()
            summary, sources = agent.process_query(query)
            execution_time = time.time() - start_time
            
            print("\nPodsumowanie:")
            print("-" * 80)
            print(summary)
            print("\nŹródła:")
            print("-" * 80)
            for source in sources:
                print(f"- {source['title']}")
                print(f"  URL: {source['url']}")
                print(f"  {source['summary']}\n")
            
            print(f"Czas wykonania: {execution_time:.2f} sekund")
            
        except KeyboardInterrupt:
            print("\nPrzerwano działanie. Do widzenia!")
            break
        except Exception as e:
            print(f"Wystąpił błąd: {str(e)}")

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--console':
        run_console()
    else:
        app.run(
            host='127.0.0.1',  # localhost
            port=5000,
            debug=True
        )

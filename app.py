from flask import Flask, request, jsonify, render_template
from research_agent import ResearchAgent
import logging
import sys
import time

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

agent = ResearchAgent()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    try:
        data = request.get_json()
        query = data.get('query')
        
        if not query:
            return jsonify({'error': 'Brak zapytania'}), 400

        start_time = time.time()
        summary, sources = agent.process_query(query)
        execution_time = time.time() - start_time

        response = {
            'summary': summary,
            'sources': sources,
            'execution_time': round(execution_time, 2)
        }
        
        return jsonify(response)
    
    except Exception as e:
        logger.error(f"Błąd podczas przetwarzania zapytania: {str(e)}")
        return jsonify({'error': str(e)}), 500

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
        app.run(host='127.0.0.1', port=5000, debug=True)

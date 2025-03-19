from research_agent import ResearchAgent
import os
import time
from typing import Dict
import json

def print_results(results: Dict) -> None:
    """Wyświetla wyniki wyszukiwania w czytelnym formacie."""
    print("\n" + "="*50)
    print(f"Zapytanie: {results['query']}")
    print("="*50 + "\n")
    
    if results.get('error'):
        print(f"❌ Błąd: {results['error']}")
        return
        
    if results.get('summary'):
        print("📝 PODSUMOWANIE:")
        print("-"*50)
        print(results['summary'])
        print("\n")
        
    if results.get('sources'):
        print("🔍 ŹRÓDŁA:")
        print("-"*50)
        for i, source in enumerate(results['sources'], 1):
            print(f"\n{i}. {source['url']}")
            if source.get('summary'):
                print(f"   {source['summary'][:300]}...")
            print()

def main():
    """Główna funkcja programu."""
    # Inicjalizacja agenta
    cache_dir = os.path.join(os.path.dirname(__file__), ".cache")
    agent = ResearchAgent(cache_dir=cache_dir)
    
    print("\n🤖 Agent Badawczy - Wersja Konsolowa")
    print("Wpisz 'exit' aby zakończyć\n")
    
    while True:
        try:
            # Pobierz zapytanie od użytkownika
            query = input("\n❓ O co chcesz się dowiedzieć? ").strip()
            
            if query.lower() in ['exit', 'quit', 'q']:
                print("\n👋 Do widzenia!")
                break
                
            if not query:
                print("\n⚠️ Zapytanie nie może być puste!")
                continue
            
            # Pokaż animację ładowania
            print("\n🔄 Szukam informacji", end="", flush=True)
            loading_chars = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
            loading_idx = 0
            
            # Rozpocznij wyszukiwanie w osobnym wątku
            start_time = time.time()
            results = agent.research(query)
            
            # Wyświetl wyniki
            print("\r" + " "*50 + "\r", end="", flush=True)  # Wyczyść linię ładowania
            print_results(results)
            
            # Pokaż czas wykonania
            execution_time = time.time() - start_time
            print(f"\n⏱️ Czas wykonania: {execution_time:.2f} sekund")
            
        except KeyboardInterrupt:
            print("\n\n👋 Program przerwany przez użytkownika.")
            break
        except Exception as e:
            print(f"\n❌ Wystąpił błąd: {str(e)}")

if __name__ == "__main__":
    main() 
#!/usr/bin/env python3
from research_agent import ResearchAgent
import time
import sys
import logging
from typing import Optional

def setup_logging():
    """Konfiguracja logowania."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('logs/console.log')
        ]
    )
    return logging.getLogger(__name__)

def print_results(summary: str, sources: list, execution_time: float):
    """Wyświetla wyniki wyszukiwania w konsoli."""
    print("\nWyniki wyszukiwania:")
    print("=" * 80)
    print(f"\nPodsumowanie:\n{summary}\n")
    
    if sources:
        print("\nŹródła:")
        print("-" * 80)
        for i, source in enumerate(sources, 1):
            print(f"\n{i}. {source['title']}")
            print(f"   URL: {source['url']}")
            print(f"   Opis: {source['summary'][:200]}...")
    
    print("\n" + "=" * 80)
    print(f"Czas wykonania: {execution_time:.2f} sekund")

def main():
    """Główna funkcja programu."""
    logger = setup_logging()
    agent = ResearchAgent()
    
    print("\nWitaj w Research Agent Console!")
    print("Wpisz 'exit' aby zakończyć.")
    
    while True:
        try:
            # Pobierz zapytanie
            query = input("\nO co chcesz zapytać? > ").strip()
            
            # Sprawdź czy kończymy
            if query.lower() in ['exit', 'quit', 'q']:
                print("\nDo widzenia!")
                break
                
            # Sprawdź czy zapytanie nie jest puste
            if not query:
                print("Zapytanie nie może być puste!")
                continue
                
            # Wykonaj wyszukiwanie
            start_time = time.time()
            summary, sources = agent.process_query(query)
            execution_time = time.time() - start_time
            
            # Wyświetl wyniki
            print_results(summary, sources, execution_time)
            logger.info(f'Successful search for query: "{query}" in {execution_time:.2f}s')
            
        except KeyboardInterrupt:
            print("\nPrzerwano działanie programu.")
            break
            
        except Exception as e:
            logger.error(f"Error during search: {str(e)}")
            print(f"\nWystąpił błąd: {str(e)}")
            continue

if __name__ == "__main__":
    main() 
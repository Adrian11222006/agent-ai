import requests
from bs4 import BeautifulSoup
import nltk
from nltk.tokenize import sent_tokenize
from langdetect import detect, DetectorFactory
import json
import time
from typing import List, Dict, Optional, Tuple
import hashlib
import os
from datetime import datetime, timedelta
import wikipedia

class ResearchAgent:
    def __init__(self, cache_dir: str = ".cache"):
        """
        Inicjalizacja agenta badawczego.
        
        Args:
            cache_dir: Ścieżka do katalogu cache
        """
        # Ustaw seed dla langdetect dla spójnych wyników
        DetectorFactory.seed = 0
        
        # Inicjalizacja NLTK
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            nltk.download('punkt', quiet=True)
            
        # Konfiguracja cache
        self.cache_dir = cache_dir
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
            
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 2  # sekundy
        
        # Limity
        self.max_text_length = 100000  # maksymalna długość tekstu do analizy
        self.max_retries = 3  # maksymalna liczba prób pobrania strony

        self.wikipedia = wikipedia
        self.wikipedia.set_lang('pl')  # domyślnie polski

    def _rate_limit(self):
        """Implementuje ograniczenie częstotliwości zapytań."""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last_request)
            
        self.last_request_time = time.time()

    def search_wikipedia(self, query: str, lang: str = 'pl') -> Dict:
        """
        Wyszukuje informacje w Wikipedii.
        
        Args:
            query: Zapytanie do wyszukania
            lang: Kod języka (pl lub en)
            
        Returns:
            Słownik z wynikami wyszukiwania
        """
        base_url = f"https://{lang}.wikipedia.org/w/api.php"
        
        # Najpierw wyszukaj strony pasujące do zapytania
        search_params = {
            "action": "query",
            "format": "json",
            "list": "search",
            "srsearch": query,
            "srlimit": 5,
            "srprop": "snippet"
        }
        
        try:
            search_response = requests.get(base_url, params=search_params)
            search_response.raise_for_status()
            search_data = search_response.json()
            
            if not search_data.get("query", {}).get("search"):
                return {"error": "Nie znaleziono wyników"}
                
            # Pobierz pełną treść pierwszego artykułu
            first_result = search_data["query"]["search"][0]
            page_id = first_result["pageid"]
            
            content_params = {
                "action": "query",
                "format": "json",
                "prop": "extracts|info|links",
                "pageids": page_id,
                "exintro": 1,
                "explaintext": 1,
                "inprop": "url",
                "pllimit": "5"
            }
            
            content_response = requests.get(base_url, params=content_params)
            content_response.raise_for_status()
            content_data = content_response.json()
            
            page_data = content_data["query"]["pages"][str(page_id)]
            
            return {
                "title": page_data["title"],
                "url": page_data["fullurl"],
                "extract": page_data["extract"],
                "links": [link["title"] for link in page_data.get("links", [])]
            }
            
        except Exception as e:
            print(f"Błąd podczas wyszukiwania w Wikipedii: {e}")
            return {"error": str(e)}

    def process_query(self, query):
        """
        Przetwarza zapytanie i zwraca podsumowanie oraz źródła.
        """
        try:
            # Wyszukaj stronę na Wikipedii
            search_results = self.wikipedia.search(query, results=3)
            if not search_results:
                return "Nie znaleziono informacji.", []
            
            # Weź pierwszy wynik
            page_title = search_results[0]
            page = self.wikipedia.page(page_title)
            
            # Przygotuj podsumowanie
            summary = page.summary
            
            # Przygotuj źródła
            sources = [{
                'title': page.title,
                'url': page.url,
                'summary': summary[:200] + '...' if len(summary) > 200 else summary
            }]
            
            # Dodaj powiązane strony jako dodatkowe źródła
            for related_title in search_results[1:]:
                try:
                    related_page = self.wikipedia.page(related_title)
                    sources.append({
                        'title': related_page.title,
                        'url': related_page.url,
                        'summary': related_page.summary[:200] + '...' if len(related_page.summary) > 200 else related_page.summary
                    })
                except:
                    continue
            
            return summary, sources
            
        except wikipedia.exceptions.DisambiguationError as e:
            # Jeśli jest wiele możliwych stron, weź pierwszą
            try:
                page = self.wikipedia.page(e.options[0])
                summary = page.summary
                sources = [{
                    'title': page.title,
                    'url': page.url,
                    'summary': summary[:200] + '...' if len(summary) > 200 else summary
                }]
                return summary, sources
            except:
                return "Znaleziono wiele możliwych odpowiedzi, ale nie udało się uzyskać szczegółowych informacji.", []
                
        except Exception as e:
            return f"Wystąpił błąd podczas wyszukiwania: {str(e)}", []

    def research(self, query: str) -> Dict:
        """
        Przeprowadza badanie na podstawie zapytania.
        
        Args:
            query: Zapytanie do zbadania
            
        Returns:
            Słownik z wynikami badania
        """
        if not query or len(query.strip()) < 3:
            raise ValueError("Zapytanie musi mieć co najmniej 3 znaki")

        results = {
            "query": query,
            "sources": [],
            "summary": "",
            "language": "unknown",
            "timestamp": datetime.now().isoformat(),
            "success": False,
            "error": None
        }

        try:
            # Wykryj język zapytania
            try:
                lang = detect(query)
                wiki_lang = 'pl' if lang == 'pl' else 'en'
            except:
                wiki_lang = 'pl'  # domyślnie polski
            
            # Wyszukaj w Wikipedii
            wiki_results = self.search_wikipedia(query, wiki_lang)
            
            if "error" in wiki_results:
                # Spróbuj w drugim języku jeśli pierwszy nie dał wyników
                wiki_lang = 'en' if wiki_lang == 'pl' else 'pl'
                wiki_results = self.search_wikipedia(query, wiki_lang)
            
            if "error" not in wiki_results:
                results["summary"] = wiki_results["extract"]
                results["sources"].append({
                    "url": wiki_results["url"],
                    "title": wiki_results["title"],
                    "summary": wiki_results["extract"][:500] + "...",
                    "language": wiki_lang
                })
                
                # Dodaj powiązane artykuły jako dodatkowe źródła
                if wiki_results.get("links"):
                    for link_title in wiki_results["links"][:2]:  # tylko 2 powiązane artykuły
                        link_results = self.search_wikipedia(link_title, wiki_lang)
                        if "error" not in link_results:
                            results["sources"].append({
                                "url": link_results["url"],
                                "title": link_results["title"],
                                "summary": link_results["extract"][:300] + "...",
                                "language": wiki_lang
                            })
                
                results["success"] = True
                results["language"] = wiki_lang
            else:
                results["error"] = "Nie znaleziono informacji w Wikipedii"

        except Exception as e:
            results["error"] = str(e)
            print(f"Błąd podczas badania: {e}")

        return results

def main():
    """Funkcja główna do testowania agenta."""
    agent = ResearchAgent()
    
    while True:
        try:
            query = input("\nO co chcesz się dowiedzieć? (wpisz 'exit' aby zakończyć): ").strip()
            if query.lower() == 'exit':
                break
                
            if not query:
                print("Zapytanie nie może być puste!")
                continue
                
            results = agent.research(query)
            
            print("\nWyniki badania:")
            print("-" * 50)
            print(f"Zapytanie: {results['query']}")
            
            if results['success']:
                print(f"\nPodsumowanie (język: {results['language']}):")
                print(results['summary'])
                print("\nŹródła:")
                for source in results['sources']:
                    print(f"\n- {source['url']}")
                    print(f"  Język: {source['language']}")
                    print(f"  {source['summary'][:200]}...")
            else:
                print(f"\nBłąd: {results['error']}")
                
            print("-" * 50)
            
        except KeyboardInterrupt:
            print("\nPrzerwano działanie programu.")
            break
        except Exception as e:
            print(f"\nWystąpił nieoczekiwany błąd: {e}")

if __name__ == "__main__":
    main()

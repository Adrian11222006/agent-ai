import requests
from bs4 import BeautifulSoup
from googlesearch import search
import nltk
from nltk.tokenize import sent_tokenize
from langdetect import detect, DetectorFactory
import json
import time
from typing import List, Dict, Optional, Tuple
from urllib.parse import urlparse, quote_plus
import hashlib
import os
from datetime import datetime, timedelta

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
        
    def _get_cache_path(self, url: str) -> str:
        """Generuje ścieżkę pliku cache dla URL."""
        url_hash = hashlib.md5(url.encode()).hexdigest()
        return os.path.join(self.cache_dir, f"{url_hash}.json")
        
    def _is_cache_valid(self, cache_path: str, max_age_hours: int = 24) -> bool:
        """Sprawdza czy cache jest wciąż aktualny."""
        if not os.path.exists(cache_path):
            return False
        
        file_time = datetime.fromtimestamp(os.path.getmtime(cache_path))
        age = datetime.now() - file_time
        return age < timedelta(hours=max_age_hours)

    def _rate_limit(self):
        """Implementuje ograniczenie częstotliwości zapytań."""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last_request)
            
        self.last_request_time = time.time()

    def search_web(self, query: str, num_results: int = 5) -> List[str]:
        """
        Wyszukuje strony internetowe związane z zapytaniem.
        """
        if not query.strip():
            raise ValueError("Zapytanie nie może być puste")
            
        print(f"Szukam informacji o: {query}")
        urls = []
        
        try:
            # Próba użycia bezpośredniego wyszukiwania Google
            search_url = f"https://www.google.com/search?q={quote_plus(query)}&hl=pl"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            response = requests.get(search_url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            search_results = soup.find_all('div', class_='g')
            
            for result in search_results[:num_results]:
                link = result.find('a')
                if link and 'href' in link.attrs:
                    url = link['href']
                    if url.startswith('http') and not url.startswith('https://www.google.com'):
                        urls.append(url)
                        self._rate_limit()
            
            # Jeśli nie znaleziono wyników, użyj alternatywnej metody
            if not urls:
                print("Używam alternatywnej metody wyszukiwania...")
                for url in search(query, num_results=num_results, lang="pl"):
                    urls.append(url)
                    self._rate_limit()
                    
            print(f"Znaleziono {len(urls)} źródeł")
            return urls
                    
        except Exception as e:
            print(f"Błąd podczas wyszukiwania: {e}")
            # Próba użycia alternatywnej metody
            try:
                print("Próbuję alternatywną metodę wyszukiwania...")
                for url in search(query, num_results=num_results, lang="pl"):
                    urls.append(url)
                    self._rate_limit()
            except Exception as e2:
                print(f"Błąd alternatywnej metody: {e2}")
            
        return urls

    def extract_content(self, url: str) -> Optional[str]:
        """
        Pobiera i przetwarza treść ze strony internetowej.
        
        Args:
            url: Adres URL strony
            
        Returns:
            Przetworzony tekst ze strony lub None w przypadku błędu
        """
        cache_path = self._get_cache_path(url)
        
        # Sprawdź cache
        if self._is_cache_valid(cache_path):
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    cached_data = json.load(f)
                return cached_data.get('content')
            except:
                pass

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        for attempt in range(self.max_retries):
            try:
                self._rate_limit()
                response = requests.get(url, headers=headers, timeout=10)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Usuń niepotrzebne elementy
                for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'iframe']):
                    tag.decompose()
                
                # Znajdź główną treść
                main_content = soup.find('main') or soup.find('article') or soup.find('div', class_=['content', 'main', 'article'])
                text = ' '.join((main_content or soup).stripped_strings)
                
                # Ogranicz długość tekstu
                text = text[:self.max_text_length]
                
                # Zapisz w cache
                with open(cache_path, 'w', encoding='utf-8') as f:
                    json.dump({
                        'content': text,
                        'timestamp': datetime.now().isoformat()
                    }, f, ensure_ascii=False)
                
                return text
                
            except Exception as e:
                print(f"Próba {attempt + 1}/{self.max_retries} nie powiodła się dla {url}: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    
        return None

    def summarize_content(self, text: str, max_sentences: int = 5) -> Tuple[str, str]:
        """
        Tworzy podsumowanie tekstu.
        
        Args:
            text: Tekst do podsumowania
            max_sentences: Maksymalna liczba zdań w podsumowaniu
            
        Returns:
            Tuple(podsumowanie, wykryty_język)
        """
        if not text or len(text.strip()) < 10:
            return "Brak wystarczającej ilości tekstu do analizy.", "unknown"

        try:
            # Wykryj język tekstu
            lang = detect(text)
            
            # Podziel na zdania z uwzględnieniem języka
            sentences = sent_tokenize(text, language='polish' if lang == 'pl' else 'english')
            
            # Wybierz najważniejsze zdania (prosta implementacja)
            if len(sentences) > max_sentences:
                # Bierzemy pierwsze i ostatnie zdanie oraz kilka ze środka
                selected = []
                selected.append(sentences[0])  # pierwsze zdanie
                
                middle_start = len(sentences) // 4
                middle_end = 3 * len(sentences) // 4
                middle_step = (middle_end - middle_start) // (max_sentences - 2)
                
                for i in range(middle_start, middle_end, middle_step):
                    if len(selected) < max_sentences - 1:
                        selected.append(sentences[i])
                
                selected.append(sentences[-1])  # ostatnie zdanie
                return ' '.join(selected), lang
            
            return ' '.join(sentences), lang
            
        except Exception as e:
            print(f"Błąd podczas tworzenia podsumowania: {e}")
            # Zwróć skrócony tekst jako fallback
            return text[:500] + "...", "unknown"

    def research(self, query: str) -> Dict:
        """
        Przeprowadza pełne badanie na podstawie zapytania.
        
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
            # Wyszukaj źródła
            urls = self.search_web(query)
            if not urls:
                results["error"] = "Nie znaleziono żadnych źródeł"
                return results

            all_content = []
            detected_languages = []
            
            for url in urls:
                content = self.extract_content(url)
                if content:
                    summary, lang = self.summarize_content(content)
                    results["sources"].append({
                        "url": url,
                        "summary": summary,
                        "language": lang
                    })
                    all_content.append(summary)
                    detected_languages.append(lang)

            # Stwórz końcowe podsumowanie
            if all_content:
                final_summary, main_lang = self.summarize_content('\n'.join(all_content))
                results["summary"] = final_summary
                results["language"] = main_lang
                results["success"] = True
            else:
                results["error"] = "Nie udało się pobrać treści z żadnego źródła"

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

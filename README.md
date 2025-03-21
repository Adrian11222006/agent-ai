# Research Agent

Asystent badawczy oparty na wyszukiwaniu w internecie, który pomaga znaleźć i podsumować informacje na zadany temat.

## Funkcje

- Wyszukiwanie informacji w internecie za pomocą DuckDuckGo
- Automatyczne podsumowywanie znalezionych treści
- Interfejs webowy do interakcji z agentem
- Obsługa języka polskiego
- Inteligentne przetwarzanie treści stron internetowych

## Wymagania

- Python 3.8+
- Flask
- BeautifulSoup4
- Requests
- Pozostałe zależności w pliku `requirements.txt`

## Instalacja

1. Sklonuj repozytorium:
```bash
git clone https://github.com/twoja-nazwa/research-agent.git
cd research-agent
```

2. Zainstaluj zależności:
```bash
pip install -r requirements.txt
```

## Uruchomienie

1. Uruchom serwer Flask:
```bash
python app.py
```

2. Otwórz przeglądarkę i przejdź pod adres:
```
http://localhost:5000
```

## Użycie

1. Wpisz pytanie w pole wyszukiwania
2. Kliknij przycisk "Szukaj"
3. Poczekaj na wyniki - agent przeszuka internet i przedstawi podsumowanie znalezionych informacji

## Struktura projektu

- `app.py` - główna aplikacja Flask
- `research_agent.py` - logika wyszukiwania i przetwarzania informacji
- `templates/` - szablony HTML
- `static/` - pliki statyczne (CSS, JavaScript)
- `logs/` - logi aplikacji

## Licencja

MIT License

## Autor

Adrian11222006

## Podziękowania

- BeautifulSoup4 za parsowanie HTML
- NLTK za przetwarzanie tekstu
- Flask za serwer web
- Requests za obsługę HTTP

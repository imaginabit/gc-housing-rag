"""
Scraper de noticias sobre vivienda vacacional en Canarias.

Usa Google News RSS para encontrar artículos relevantes sobre:
- Viviendas vacacionales
- Turistificación
- Alquiler turístico
- Impacto del turismo en la vivienda

Guarda los resultados en data/raw/news_articles.json
"""

import json
import logging
import urllib.request
from urllib.parse import quote
from datetime import datetime, timezone
from pathlib import Path

import feedparser

logger = logging.getLogger(__name__)

# Directorio de datos
DATA_DIR = Path(__file__).parent.parent.parent / "data" / "raw"
OUTPUT_FILE = DATA_DIR / "news_articles.json"

# Queries de búsqueda en Google News RSS
SEARCH_QUERIES = [
    "vivienda vacacional Las Palmas",
    "viviendas vacacionales Canarias",
    "turistificación Canarias",
    "alquiler turístico Gran Canaria",
    "vivienda turística Canarias",
    "pisos turísticos Las Palmas",
]

# Fuentes prioritarias (periódicos de Canarias y España)
PREFERRED_SOURCES = [
    "canarias7",
    "la provincia",
    "diario de avisos",
    "eldiario",
    "cope",
    "atlántico hoy",
    "maspalomas24h",
    "canarias news",
    "europa press",
    "el confidencial",
    "el país",
]

# Topic classification por keywords
TOPIC_KEYWORDS = {
    "legislación": [
        "ley",
        "regulación",
        "normativa",
        "gobierno",
        "ayuntamiento",
        "decreto",
        "licencia",
    ],
    "denuncia vecinal": [
        "vecinos",
        "denuncia",
        "protesta",
        "plataforma",
        "reclamación",
        "queja",
    ],
    "datos": [
        "datos",
        "estadística",
        "registro",
        "cifras",
        "aumento",
        "crece",
        "sube",
        "baja",
    ],
    "impacto social": [
        "familias",
        "desplazamiento",
        "éxodo",
        "infierno",
        "tormento",
        "ruido",
        "molestias",
    ],
    "economía turística": ["facturación", "récord", "millones", "economía", "ingresos"],
}


def classify_topic(title: str) -> str:
    """Clasifica un artículo por su título."""
    title_lower = title.lower()
    scores = {}
    for topic, keywords in TOPIC_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in title_lower)
        if score > 0:
            scores[topic] = score

    if scores:
        return max(scores, key=scores.get)
    return "general"


def fetch_google_news(query: str, max_results: int = 20) -> list[dict]:
    """
    Busca artículos en Google News RSS para una query.

    Returns:
        Lista de dicts con: title, url, source, date, topic
    """
    encoded_query = quote(query)
    url = f"https://news.google.com/rss/search?q={encoded_query}&hl=es&gl=ES&ceid=ES:es"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        response = urllib.request.urlopen(req, timeout=15)
        data = response.read().decode("utf-8")
        feed = feedparser.parse(data)
    except Exception as e:
        logger.error(f"Error fetching Google News for '{query}': {e}")
        return []

    articles = []
    for entry in feed.entries[:max_results]:
        # Extraer fuente
        source = "Desconocido"
        if hasattr(entry, "source") and entry.source:
            source = entry.source.get("title", "Desconocido")

        # Parsear fecha
        date_str = ""
        if hasattr(entry, "published"):
            try:
                dt = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                date_str = dt.strftime("%Y-%m-%d")
            except Exception:
                date_str = entry.get("published", "")

        # Clasificar topic
        topic = classify_topic(entry.title)

        # Priorizar fuentes conocidas
        source_lower = source.lower()
        is_preferred = any(ps in source_lower for ps in PREFERRED_SOURCES)

        articles.append(
            {
                "title": entry.title,
                "url": entry.link,
                "source": source,
                "date": date_str,
                "topic": topic,
                "query": query,
                "preferred": is_preferred,
            }
        )

    return articles


def scrape_all(max_per_query: int = 15) -> list[dict]:
    """
    Ejecuta todas las queries y devuelve artículos únicos.

    Filtra duplicados por URL y prioriza fuentes conocidas.
    """
    all_articles = []
    seen_urls = set()

    for query in SEARCH_QUERIES:
        logger.info(f"Buscando: {query}")
        articles = fetch_google_news(query, max_results=max_per_query)

        for article in articles:
            url = article["url"]
            if url not in seen_urls:
                seen_urls.add(url)
                all_articles.append(article)

    # Ordenar: preferidos primero, luego por fecha (más recientes)
    all_articles.sort(
        key=lambda a: (a.get("preferred", False), a.get("date", "")),
        reverse=True,
    )

    logger.info(f"Total artículos únicos: {len(all_articles)}")
    return all_articles


def save_articles(articles: list[dict]) -> Path:
    """Guarda artículos en JSON."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    output = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "total": len(articles),
        "articles": articles,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    logger.info(f"Guardados {len(articles)} artículos en {OUTPUT_FILE}")
    return OUTPUT_FILE


def load_articles() -> dict:
    """Carga artículos guardados."""
    if not OUTPUT_FILE.exists():
        return {"total": 0, "articles": []}

    with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    """Ejecutar scraper completo."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    print("=" * 50)
    print("  Scraper de Noticias — Éxodo Vecinal")
    print("=" * 50)

    articles = scrape_all(max_per_query=15)
    path = save_articles(articles)

    # Resumen por topic
    topics = {}
    for a in articles:
        t = a.get("topic", "general")
        topics[t] = topics.get(t, 0) + 1

    print(f"\n✅ {len(articles)} artículos guardados en {path}")
    print("\nPor tema:")
    for topic, count in sorted(topics.items(), key=lambda x: -x[1]):
        print(f"  {topic}: {count}")

    # Mostrar los 5 más recientes
    print("\n📰 Últimos 5:")
    for a in articles[:5]:
        print(f"  [{a['source']}] {a['title'][:70]}")
        print(f"    {a['date']} — {a['topic']}")


if __name__ == "__main__":
    main()

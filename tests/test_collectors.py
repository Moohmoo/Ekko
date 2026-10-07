"""Tests unitaires pour les parsers des collecteurs d'articles."""

from tools.watch.collectors.hacker_news import parse_hn_article
from tools.watch.collectors.hugging_face import parse_hf_paper


def test_parse_hn_article_with_external_url() -> None:
    """Vérifie le parsing d'un article standard Hacker News avec URL externe."""
    raw = {
        "id": 123456,
        "title": "Release of Python 3.14",
        "url": "https://python.org/release",
        "score": 350,
        "kids": [1, 2, 3],
    }
    parsed = parse_hn_article(raw)
    assert parsed is not None
    assert parsed.title == "Release of Python 3.14"
    assert parsed.url == "https://python.org/release"
    assert "350 pts" in parsed.summary
    assert "3 commentaires" in parsed.summary


def test_parse_hn_article_fallback_url() -> None:
    """Vérifie l'URL de repli vers la discussion HN en l'absence de lien externe."""
    raw = {
        "id": 999,
        "title": "Ask HN: What is your stack?",
        "score": 80,
    }
    parsed = parse_hn_article(raw)
    assert parsed is not None
    assert parsed.url == "https://news.ycombinator.com/item?id=999"


def test_parse_hf_paper() -> None:
    """Vérifie le parsing d'un papier Hugging Face Daily Papers."""
    raw = {
        "title": "Attention Is All You Need 2",
        "paper": {
            "id": "2610.12345",
            "upvotes": 42,
            "summary": "We propose a revolutionary architecture.",
        },
    }
    parsed = parse_hf_paper(raw)
    assert parsed is not None
    assert parsed.url == "https://huggingface.co/papers/2610.12345"
    assert "42" in parsed.summary

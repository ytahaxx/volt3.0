import re

import pytest

STATIC_PAGES = ["/", "/programme", "/thematiques", "/explorer", "/favoris", "/quiz", "/assistant", "/a-propos"]


@pytest.mark.parametrize("url", STATIC_PAGES)
def test_pages_are_accessible(client, url):
    r = client.get(url)
    assert r.status_code == 200
    assert "Volt" in r.get_data(as_text=True)


def test_every_category_page_lists_its_propositions(client):
    cats = client.get("/api/categories").get_json()
    assert len(cats) >= 10
    for c in cats:
        r = client.get(f"/thematiques/{c['slug']}")
        assert r.status_code == 200
        html = r.get_data(as_text=True)
        assert html.count('class="fav-btn"') == c["count"]


def test_every_proposition_page_works_and_has_source_link(client):
    total = client.get("/api/propositions").get_json()["count"]
    assert total == 48
    for pid in range(1, total + 1):
        r = client.get(f"/proposition/{pid}")
        assert r.status_code == 200
        html = r.get_data(as_text=True)
        assert "voltfrance.org/storage/pdf/volt-ecp_fr.pdf" in html
        assert "Non officielle" in html  # explication complémentaire clairement séparée


def test_internal_links_on_pages_resolve(client):
    """Tous les liens internes de chaque page doivent répondre 200."""
    seen = set()
    for page in STATIC_PAGES + ["/thematiques/democratie", "/proposition/1"]:
        html = client.get(page).get_data(as_text=True)
        for href in re.findall(r'href="(/[^"#]*)"', html):
            if href.startswith("/static/") or href in seen:
                continue
            seen.add(href)
            assert client.get(href).status_code == 200, f"lien cassé : {href} (depuis {page})"


def test_static_assets_are_served(client):
    for path in ["css/style.css", "js/app.js", "js/search.js", "js/quiz.js", "js/assistant.js"]:
        assert client.get(f"/static/{path}").status_code == 200


def test_unknown_page_is_clean_404(client):
    r = client.get("/nimportequoi")
    assert r.status_code == 404
    assert "Page introuvable" in r.get_data(as_text=True)
    assert client.get("/proposition/9999").status_code == 404
    assert client.get("/thematiques/inconnue").status_code == 404


def test_api_errors_are_json(client):
    r = client.get("/api/inexistant")
    assert r.status_code == 404 and r.is_json
    assert client.get("/api/propositions/9999").status_code == 404

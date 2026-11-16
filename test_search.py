def titles(resp):
    return [r["title"] for r in resp.get_json()["results"]]


def test_list_all_without_filter(client):
    data = client.get("/api/propositions").get_json()
    assert data["count"] == 48
    assert [r["id"] for r in data["results"]] == list(range(1, 49))


def test_keyword_search_finds_ai(client):
    data = client.get("/api/propositions?q=intelligence artificielle").get_json()
    ids = {r["id"] for r in data["results"]}
    assert {11, 48} <= ids
    assert data["terms"] == ["intelligence", "artificielle"]


def test_search_is_accent_and_case_insensitive(client):
    a = client.get("/api/propositions?q=EDUCATION").get_json()
    b = client.get("/api/propositions?q=éducation").get_json()
    assert a["count"] == b["count"] > 0


def test_search_short_term_matches_whole_word_only(client):
    ids = {r["id"] for r in client.get("/api/propositions?q=ia").get_json()["results"]}
    assert 48 in ids
    # « ia » ne doit pas matcher à l'intérieur d'autres mots (ex. « familiale », « initiative »)
    for r in client.get("/api/propositions?q=ia").get_json()["results"]:
        assert r["id"] in {11, 48}


def test_search_examples_from_spec_return_results(client):
    for q in ["Intelligence artificielle", "Environnement", "Éducation", "Transports", "Europe"]:
        assert client.get(f"/api/propositions?q={q}").get_json()["count"] > 0, q


def test_no_result_message_case(client):
    data = client.get("/api/propositions?q=zzzxyzabc").get_json()
    assert data["count"] == 0 and data["results"] == []


def test_filter_by_category_returns_only_that_category(client):
    data = client.get("/api/propositions?category=democratie").get_json()
    assert data["count"] == 6
    assert {r["category"] for r in data["results"]} == {"democratie"}


def test_filter_by_subcategory_and_type(client):
    data = client.get("/api/propositions?type=Objectif chiffré").get_json()
    assert data["count"] > 0
    assert {r["type"] for r in data["results"]} == {"Objectif chiffré"}
    sub = client.get("/api/propositions?subcategory=Biodiversité").get_json()
    assert [r["id"] for r in sub["results"]] == [24]


def test_combined_filters(client):
    data = client.get("/api/propositions?category=climat&q=agriculture").get_json()
    assert {r["id"] for r in data["results"]} == {22, 23}


def test_alphabetical_sort(client):
    asc = titles(client.get("/api/propositions?sort=alpha"))
    desc = titles(client.get("/api/propositions?sort=alpha_desc"))
    assert asc != desc
    import unicodedata

    def key(t):
        return unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().lower()
    assert [key(t) for t in asc] == sorted(key(t) for t in asc)
    assert desc == list(reversed(sorted(desc, key=key))) or [key(t) for t in desc] == sorted((key(t) for t in desc), reverse=True)


def test_ids_filter_for_favorites(client):
    data = client.get("/api/propositions?ids=3,9,48").get_json()
    assert {r["id"] for r in data["results"]} == {3, 9, 48}
    assert client.get("/api/propositions?ids=").get_json()["count"] == 0


def test_invalid_parameters_are_rejected(client):
    assert client.get("/api/propositions?sort=bidon").status_code == 400
    assert client.get("/api/propositions?category=bidon").status_code == 400
    assert client.get("/api/propositions?ids=a,b").status_code == 400


def test_filters_endpoint(client):
    f = client.get("/api/filters").get_json()
    assert len(f["categories"]) == 12 and len(f["types"]) >= 5 and f["subcategories"]
    assert sum(c["count"] for c in f["categories"]) == 48


def test_category_counts_match_listing(client):
    for c in client.get("/api/categories").get_json():
        n = client.get(f"/api/propositions?category={c['slug']}").get_json()["count"]
        assert n == c["count"]


def test_proposition_detail_has_all_required_fields(client):
    p = client.get("/api/propositions/9").get_json()
    for key in ["title", "category", "summary", "details", "objectives", "measures",
                "section_ref", "source_url", "source_document"]:
        assert p[key]
    assert "22 %" in p["summary"]

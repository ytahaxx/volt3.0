import json


def test_manifest_is_valid_and_icons_exist(client):
    r = client.get("/static/manifest.webmanifest")
    assert r.status_code == 200
    m = json.loads(r.get_data(as_text=True))
    assert m["display"] == "standalone" and m["start_url"] == "/"
    assert {"192x192", "512x512"} <= {i["sizes"] for i in m["icons"]}
    assert any(i["purpose"] == "maskable" for i in m["icons"])
    for icon in m["icons"]:
        png = client.get(icon["src"])
        assert png.status_code == 200 and png.data[:8] == b"\x89PNG\r\n\x1a\n"
    for s in m["shortcuts"]:
        assert client.get(s["url"]).status_code == 200


def test_service_worker_served_at_root_scope(client):
    r = client.get("/sw.js")
    assert r.status_code == 200
    assert "javascript" in r.content_type
    assert "fetch" in r.get_data(as_text=True)


def test_pages_link_manifest_and_register_worker(client):
    html = client.get("/").get_data(as_text=True)
    assert 'rel="manifest"' in html and 'name="theme-color"' in html
    assert 'register("/sw.js")' in client.get("/static/js/app.js").get_data(as_text=True)


def test_service_worker_precache_files_exist(client):
    import re
    sw = client.get("/sw.js").get_data(as_text=True)
    block = re.search(r"PRECACHE = \[(.*?)\];", sw, re.S).group(1)
    for path in re.findall(r'"(/static/[^"]+)"', block):
        assert client.get(path).status_code == 200, path

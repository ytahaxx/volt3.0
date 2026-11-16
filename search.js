/* Volt Explorer — page Explorer : recherche instantanée + filtres (sans rechargement). */
(function () {
  "use strict";
  var qInput = document.getElementById("q");
  var selCat = document.getElementById("f-category");
  var selSub = document.getElementById("f-subcategory");
  var selType = document.getElementById("f-type");
  var selSort = document.getElementById("f-sort");
  var results = document.getElementById("results");
  var countEl = document.getElementById("result-count");
  var emptyEl = document.getElementById("empty");
  var errorEl = document.getElementById("error");
  var filters = { categories: [], subcategories: [], types: [] };
  var requestId = 0, timer = null;

  function option(value, label) {
    var o = document.createElement("option");
    o.value = value; o.textContent = label;
    return o;
  }

  function fillSubcategories() {
    var current = selSub.value;
    selSub.innerHTML = "";
    selSub.appendChild(option("", "Toutes"));
    var seen = {};
    filters.subcategories.forEach(function (s) {
      if (selCat.value && s.category !== selCat.value) return;
      if (seen[s.label]) return;
      seen[s.label] = true;
      selSub.appendChild(option(s.label, s.label));
    });
    if (seen[current]) selSub.value = current;
  }

  function params() {
    var p = new URLSearchParams();
    if (qInput.value.trim()) p.set("q", qInput.value.trim());
    if (selCat.value) p.set("category", selCat.value);
    if (selSub.value) p.set("subcategory", selSub.value);
    if (selType.value) p.set("type", selType.value);
    if (selSort.value) p.set("sort", selSort.value);
    return p;
  }

  function run() {
    var id = ++requestId, p = params();
    var qs = p.toString();
    history.replaceState(null, "", qs ? "?" + qs : location.pathname);
    fetch("/api/propositions" + (qs ? "?" + qs : ""))
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(function (data) {
        if (id !== requestId) return; // réponse obsolète
        errorEl.hidden = true;
        results.innerHTML = data.results.map(function (x) { return VE.propositionCard(x, data.terms); }).join("");
        emptyEl.hidden = data.count !== 0;
        countEl.textContent = data.count + " proposition" + (data.count > 1 ? "s" : "") + " trouvée" + (data.count > 1 ? "s" : "");
        VE.refreshFavoriteUI();
      })
      .catch(function () {
        if (id !== requestId) return;
        results.innerHTML = ""; countEl.textContent = ""; emptyEl.hidden = true; errorEl.hidden = false;
      });
  }

  function schedule() { clearTimeout(timer); timer = setTimeout(run, 150); }

  qInput.addEventListener("input", schedule);
  selCat.addEventListener("change", function () { fillSubcategories(); run(); });
  [selSub, selType, selSort].forEach(function (s) { s.addEventListener("change", run); });
  document.querySelectorAll("[data-example]").forEach(function (b) {
    b.addEventListener("click", function () { qInput.value = b.getAttribute("data-example"); run(); });
  });
  document.getElementById("reset-filters").addEventListener("click", function () {
    qInput.value = ""; selCat.value = ""; selType.value = ""; selSort.value = "";
    fillSubcategories(); run();
  });

  fetch("/api/filters")
    .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then(function (data) {
      filters = data;
      data.categories.forEach(function (c) { selCat.appendChild(option(c.slug, c.label + " (" + c.count + ")")); });
      data.types.forEach(function (t) { selType.appendChild(option(t, t)); });
      var url = new URLSearchParams(location.search);
      qInput.value = url.get("q") || "";
      selCat.value = url.get("category") || "";
      fillSubcategories();
      selSub.value = url.get("subcategory") || "";
      selType.value = url.get("type") || "";
      selSort.value = url.get("sort") || "";
      run();
    })
    .catch(function () { errorEl.hidden = false; });
})();

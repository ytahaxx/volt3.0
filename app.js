/* Volt Explorer — code commun : menu mobile, utilitaires, favoris (localStorage). */
(function () {
  "use strict";

  // ---------- Utilitaires partagés (window.VE) ----------
  function esc(value) {
    return String(value).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  // Normalise comme le backend (minuscules, sans accents) en gardant la correspondance d'indices.
  function normalizeWithMap(text) {
    var out = "", map = [];
    for (var i = 0; i < text.length; i++) {
      var n = text[i].normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
      for (var j = 0; j < n.length; j++) { out += n[j]; map.push(i); }
    }
    return { text: out, map: map };
  }

  function isWordChar(ch) { return !!ch && /[a-z0-9]/.test(ch); }

  // Échappe le HTML puis entoure d'un <mark> les termes cherchés (insensible aux accents/casse).
  function highlight(text, terms) {
    text = String(text);
    if (!terms || !terms.length) return esc(text);
    var norm = normalizeWithMap(text), ranges = [];
    terms.forEach(function (term) {
      if (!term) return;
      var from = 0, idx;
      while ((idx = norm.text.indexOf(term, from)) !== -1) {
        var end = idx + term.length;
        var ok = term.length > 3 || (!isWordChar(norm.text[idx - 1]) && !isWordChar(norm.text[end]));
        if (ok) ranges.push([norm.map[idx], norm.map[end - 1] + 1]);
        from = idx + 1;
      }
    });
    if (!ranges.length) return esc(text);
    ranges.sort(function (a, b) { return a[0] - b[0]; });
    var merged = [ranges[0]];
    for (var i = 1; i < ranges.length; i++) {
      var last = merged[merged.length - 1];
      if (ranges[i][0] <= last[1]) last[1] = Math.max(last[1], ranges[i][1]);
      else merged.push(ranges[i]);
    }
    var html = "", pos = 0;
    merged.forEach(function (r) {
      html += esc(text.slice(pos, r[0])) + "<mark>" + esc(text.slice(r[0], r[1])) + "</mark>";
      pos = r[1];
    });
    return html + esc(text.slice(pos));
  }

  // ---------- Favoris ----------
  var KEY = "voltExplorer.favorites";
  var favorites = {
    all: function () {
      try {
        var v = JSON.parse(localStorage.getItem(KEY) || "[]");
        return Array.isArray(v) ? v.filter(Number.isInteger) : [];
      } catch (e) { return []; }
    },
    save: function (ids) {
      try { localStorage.setItem(KEY, JSON.stringify(ids)); } catch (e) { /* stockage indisponible */ }
    },
    has: function (id) { return this.all().indexOf(id) !== -1; },
    toggle: function (id) {
      var ids = this.all(), i = ids.indexOf(id);
      if (i === -1) ids.push(id); else ids.splice(i, 1);
      this.save(ids);
      return i === -1;
    },
    clear: function () { this.save([]); }
  };

  function refreshFavoriteUI() {
    var count = favorites.all().length;
    var badge = document.getElementById("fav-count");
    if (badge) { badge.textContent = count; badge.hidden = count === 0; }
    document.querySelectorAll("[data-fav-id]").forEach(function (btn) {
      var on = favorites.has(Number(btn.getAttribute("data-fav-id")));
      btn.setAttribute("aria-pressed", on ? "true" : "false");
      var label = on ? "Retirer des favoris" : "Ajouter aux favoris";
      btn.setAttribute("aria-label", label);
      btn.title = label;
      var span = btn.querySelector(".fav-label");
      if (span) span.textContent = label;
    });
  }

  document.addEventListener("click", function (e) {
    var btn = e.target.closest("[data-fav-id]");
    if (!btn) return;
    favorites.toggle(Number(btn.getAttribute("data-fav-id")));
    refreshFavoriteUI();
    document.dispatchEvent(new CustomEvent("favorites:changed"));
  });

  // Carte de proposition (utilisée par Explorer et Favoris)
  function propositionCard(p, terms) {
    return '<article class="card">' +
      '<div class="card-top"><span class="tag">' + esc(p.category_label || p.category) + "</span>" +
      '<button class="fav-btn" data-fav-id="' + p.id + '" aria-pressed="false" aria-label="Ajouter aux favoris" title="Ajouter aux favoris">♥</button></div>' +
      '<h3><a href="/proposition/' + p.id + '">' + highlight(p.title, terms) + "</a></h3>" +
      "<p>" + highlight(p.summary, terms) + "</p>" +
      '<div><span class="tag tag-soft">' + esc(p.subcategory) + '</span> <span class="tag tag-soft">' + esc(p.type) + "</span></div>" +
      '<a class="card-meta" href="/proposition/' + p.id + '">Voir la fiche →</a></article>';
  }

  window.VE = { esc: esc, highlight: highlight, favorites: favorites, refreshFavoriteUI: refreshFavoriteUI, propositionCard: propositionCard };

  // ---------- Menu mobile ----------
  var toggle = document.getElementById("nav-toggle");
  var nav = document.getElementById("main-nav");
  if (toggle && nav) {
    toggle.addEventListener("click", function () {
      var open = nav.classList.toggle("open");
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
      toggle.setAttribute("aria-label", open ? "Fermer le menu" : "Ouvrir le menu");
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && nav.classList.contains("open")) toggle.click();
    });
  }

  // ---------- Page Favoris ----------
  var list = document.getElementById("favorites-list");
  if (list) {
    var empty = document.getElementById("favorites-empty");
    var errorBox = document.getElementById("favorites-error");
    var clearBtn = document.getElementById("clear-favorites");

    var renderFavorites = function () {
      var ids = favorites.all();
      errorBox.hidden = true;
      if (!ids.length) {
        list.innerHTML = ""; empty.hidden = false; clearBtn.hidden = true;
        refreshFavoriteUI();
        return;
      }
      empty.hidden = true; clearBtn.hidden = false;
      fetch("/api/propositions?ids=" + ids.join(",") + "&sort=alpha")
        .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
        .then(function (data) {
          list.innerHTML = data.results.map(function (p) { return propositionCard(p, []); }).join("");
          if (!data.results.length) { empty.hidden = false; clearBtn.hidden = true; }
          refreshFavoriteUI();
        })
        .catch(function () { errorBox.hidden = false; });
    };

    // Retirer un favori sur cette page retire aussi la carte
    document.addEventListener("favorites:changed", renderFavorites);
    clearBtn.addEventListener("click", function () { favorites.clear(); renderFavorites(); refreshFavoriteUI(); });
    renderFavorites();
  }

  refreshFavoriteUI();

  // ---------- PWA : service worker (HTTPS ou localhost uniquement) ----------
  if ("serviceWorker" in navigator) {
    window.addEventListener("load", function () {
      navigator.serviceWorker.register("/sw.js").catch(function () { /* non bloquant */ });
    });
  }
})();

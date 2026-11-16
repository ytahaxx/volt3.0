/* Volt Explorer — assistant : envoie la question au backend (RAG) et affiche réponse + sources.
   Le texte est inséré via textContent (jamais innerHTML) : pas de risque d'injection. */
(function () {
  "use strict";
  var chat = document.getElementById("chat");
  var form = document.getElementById("chat-form");
  var input = document.getElementById("chat-input");
  var sendBtn = document.getElementById("chat-send");
  var pill = document.getElementById("mode-pill");
  var notice = document.getElementById("mode-notice");
  var busy = false;

  var MODE_LABELS = { demo: "Mode démonstration (sans service externe)", anthropic: "Modèle : Anthropic", openai: "Modèle : OpenAI" };

  function addMessage(kind, text) {
    var div = document.createElement("div");
    div.className = "msg msg-" + kind;
    div.textContent = text;
    chat.appendChild(div);
    chat.scrollTop = chat.scrollHeight;
    return div;
  }

  function renderSources(container, sources) {
    if (!sources || !sources.length) return;
    var box = document.createElement("div");
    box.className = "sources";
    var h = document.createElement("h4");
    h.textContent = "Sources du programme officiel";
    var ul = document.createElement("ul");
    ul.className = "plain";
    sources.forEach(function (s) {
      var li = document.createElement("li");
      var label = document.createElement("strong");
      label.textContent = "[" + s.label + "] ";
      li.appendChild(label);
      var a = document.createElement("a");
      a.href = s.proposition_id ? "/proposition/" + s.proposition_id : s.url;
      if (!s.proposition_id) { a.target = "_blank"; a.rel = "noopener"; }
      a.textContent = s.title;
      li.appendChild(a);
      var ref = document.createElement("div");
      ref.className = "muted";
      ref.textContent = s.ref;
      li.appendChild(ref);
      ul.appendChild(li);
    });
    box.append(h, ul);
    container.appendChild(box);
  }

  function ask(question) {
    if (busy || !question.trim()) return;
    busy = true; sendBtn.disabled = true;
    addMessage("user", question);
    var pending = addMessage("bot", "Recherche dans le programme…");
    pending.classList.add("msg-pending");

    fetch("/api/assistant", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: question })
    })
      .then(function (r) {
        return r.json().then(function (data) { return { ok: r.ok, data: data }; });
      })
      .then(function (res) {
        pending.classList.remove("msg-pending");
        if (!res.ok) { pending.textContent = res.data.error || "Une erreur est survenue."; return; }
        pending.textContent = res.data.answer;
        renderSources(pending, res.data.sources);
        if (res.data.notice) {
          var n = document.createElement("p");
          n.className = "small muted"; n.textContent = res.data.notice;
          pending.appendChild(n);
        }
      })
      .catch(function () {
        pending.classList.remove("msg-pending");
        pending.textContent = "L'assistant est momentanément indisponible. Réessayez dans un instant.";
      })
      .finally(function () {
        busy = false; sendBtn.disabled = false; input.focus();
        chat.scrollTop = chat.scrollHeight;
      });
  }

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    var q = input.value;
    input.value = "";
    ask(q);
  });
  document.querySelectorAll("[data-question]").forEach(function (b) {
    b.addEventListener("click", function () { ask(b.getAttribute("data-question")); });
  });

  fetch("/api/assistant/status")
    .then(function (r) { return r.json(); })
    .then(function (s) {
      pill.textContent = MODE_LABELS[s.mode] || ("Mode : " + s.mode);
      if (s.notice) notice.textContent = s.notice;
    })
    .catch(function () { pill.textContent = "Mode : indisponible"; });
})();

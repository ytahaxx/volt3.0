/* Volt Explorer — quiz : une question à la fois, correction et explication après chaque réponse. */
(function () {
  "use strict";
  var startBox = document.getElementById("quiz-start");
  var playBox = document.getElementById("quiz-play");
  var endBox = document.getElementById("quiz-end");
  var picker = document.getElementById("level-picker");
  var errorBox = document.getElementById("quiz-error");
  var bar = document.getElementById("progress-bar");
  var progress = document.getElementById("progress");
  var progressText = document.getElementById("progress-text");
  var questionEl = document.getElementById("question-text");
  var choicesEl = document.getElementById("choices");
  var feedback = document.getElementById("feedback");
  var nextBtn = document.getElementById("next-btn");
  var restartBtn = document.getElementById("restart-btn");

  var questions = [], index = 0, answers = [], locked = false;

  function show(box) {
    [startBox, playBox, endBox].forEach(function (b) { b.hidden = b !== box; });
  }

  function post(url, body) {
    return fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) })
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); });
  }

  function setProgress(done) {
    var pct = questions.length ? Math.round(100 * done / questions.length) : 0;
    bar.style.width = pct + "%";
    progress.setAttribute("aria-valuenow", String(pct));
  }

  function renderQuestion() {
    var q = questions[index];
    locked = false;
    feedback.hidden = true; feedback.className = "feedback"; feedback.innerHTML = "";
    nextBtn.hidden = true;
    progressText.textContent = "Question " + (index + 1) + " sur " + questions.length;
    setProgress(index);
    questionEl.textContent = q.question;
    choicesEl.innerHTML = "";
    q.choices.forEach(function (label, i) {
      var b = document.createElement("button");
      b.type = "button"; b.className = "choice"; b.textContent = label;
      b.addEventListener("click", function () { answer(i); });
      choicesEl.appendChild(b);
    });
  }

  function answer(choice) {
    if (locked) return;
    locked = true;
    var q = questions[index];
    var buttons = choicesEl.querySelectorAll(".choice");
    buttons.forEach(function (b) { b.disabled = true; });
    post("/api/quiz/answer", { question_id: q.id, choice: choice })
      .then(function (res) {
        answers.push({ question_id: q.id, choice: choice });
        buttons[res.correct_index].classList.add("correct");
        if (!res.correct) buttons[choice].classList.add("wrong");
        feedback.hidden = false;
        feedback.className = "feedback " + (res.correct ? "ok" : "ko");
        var title = document.createElement("strong");
        title.textContent = res.correct ? "Bonne réponse. " : "Ce n'est pas la bonne réponse. La bonne réponse : " + res.correct_answer + ". ";
        var expl = document.createElement("span");
        expl.textContent = res.explanation + " ";
        var link = document.createElement("a");
        link.href = "/proposition/" + res.proposition_id;
        link.textContent = "Voir la proposition et sa source →";
        feedback.append(title, expl, link);
        setProgress(index + 1);
        nextBtn.textContent = index + 1 < questions.length ? "Question suivante" : "Voir mon score";
        nextBtn.hidden = false;
        nextBtn.focus();
      })
      .catch(function () {
        locked = false;
        buttons.forEach(function (b) { b.disabled = false; });
        feedback.hidden = false; feedback.className = "feedback ko";
        feedback.textContent = "Impossible de vérifier la réponse. Réessayez.";
      });
  }

  function finish() {
    post("/api/quiz/score", { answers: answers })
      .then(function (res) {
        document.getElementById("final-score").textContent = res.correct + " / " + res.total;
        document.getElementById("final-detail").textContent = res.percent + " % de bonnes réponses.";
        show(endBox);
      })
      .catch(function () {
        document.getElementById("final-score").textContent = "—";
        document.getElementById("final-detail").textContent = "Le score n'a pas pu être calculé.";
        show(endBox);
      });
  }

  nextBtn.addEventListener("click", function () {
    if (index + 1 < questions.length) { index++; renderQuestion(); } else { finish(); }
  });
  restartBtn.addEventListener("click", function () { show(startBox); });

  function start(level) {
    errorBox.hidden = true;
    fetch("/api/quiz?level=" + encodeURIComponent(level))
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(function (data) {
        if (!data.questions.length) throw new Error("vide");
        questions = data.questions; index = 0; answers = [];
        show(playBox); renderQuestion();
      })
      .catch(function () { errorBox.hidden = false; });
  }

  fetch("/api/quiz?level=tous")
    .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then(function (data) {
      var all = [{ slug: "tous", label: "Tous niveaux" }].concat(data.levels);
      all.forEach(function (lv) {
        var b = document.createElement("button");
        b.type = "button"; b.className = "btn " + (lv.slug === "tous" ? "btn-primary" : "btn-light");
        b.textContent = lv.label;
        b.addEventListener("click", function () { start(lv.slug); });
        picker.appendChild(b);
      });
    })
    .catch(function () { errorBox.hidden = false; });
})();

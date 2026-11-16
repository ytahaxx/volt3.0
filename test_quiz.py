import json
from pathlib import Path

QUIZ = json.loads((Path(__file__).resolve().parent.parent / "data" / "quiz.json").read_text(encoding="utf-8"))


def test_quiz_data_is_consistent(client):
    for q in QUIZ["questions"]:
        assert len(q["choices"]) == 4 and 0 <= q["answer"] < 4
        assert q["level"] in {lv["slug"] for lv in QUIZ["levels"]}
        assert client.get(f"/api/propositions/{q['proposition_id']}").status_code == 200


def test_questions_do_not_leak_answers(client):
    data = client.get("/api/quiz").get_json()
    assert data["count"] == len(QUIZ["questions"])
    for q in data["questions"]:
        assert "answer" not in q and "explanation" not in q


def test_levels_filter(client):
    for lv in QUIZ["levels"]:
        data = client.get(f"/api/quiz?level={lv['slug']}").get_json()
        assert data["count"] > 0
        assert {q["level"] for q in data["questions"]} == {lv["slug"]}
    assert client.get("/api/quiz?level=impossible").status_code == 400


def test_answer_correct_and_wrong(client):
    q = QUIZ["questions"][0]
    good = client.post("/api/quiz/answer", json={"question_id": q["id"], "choice": q["answer"]}).get_json()
    assert good["correct"] is True and good["explanation"] and good["proposition_id"] == q["proposition_id"]
    wrong_choice = (q["answer"] + 1) % 4
    bad = client.post("/api/quiz/answer", json={"question_id": q["id"], "choice": wrong_choice}).get_json()
    assert bad["correct"] is False and bad["correct_index"] == q["answer"]


def test_answer_validation(client):
    assert client.post("/api/quiz/answer", json={"question_id": 9999, "choice": 0}).status_code == 404
    assert client.post("/api/quiz/answer", json={"question_id": 1, "choice": 7}).status_code == 400
    assert client.post("/api/quiz/answer", json={"question_id": 1, "choice": "a"}).status_code == 400
    assert client.post("/api/quiz/answer", data="pas du json").status_code in (400, 404)


def test_score_is_computed_correctly(client):
    answers = []
    for i, q in enumerate(QUIZ["questions"]):
        choice = q["answer"] if i % 2 == 0 else (q["answer"] + 1) % 4
        answers.append({"question_id": q["id"], "choice": choice})
    expected = sum(1 for i in range(len(QUIZ["questions"])) if i % 2 == 0)
    res = client.post("/api/quiz/score", json={"answers": answers}).get_json()
    assert res["correct"] == expected
    assert res["total"] == len(QUIZ["questions"])
    assert res["percent"] == round(100 * expected / len(QUIZ["questions"]))


def test_perfect_and_zero_scores(client):
    perfect = [{"question_id": q["id"], "choice": q["answer"]} for q in QUIZ["questions"]]
    assert client.post("/api/quiz/score", json={"answers": perfect}).get_json()["percent"] == 100
    zero = [{"question_id": q["id"], "choice": (q["answer"] + 1) % 4} for q in QUIZ["questions"]]
    assert client.post("/api/quiz/score", json={"answers": zero}).get_json()["correct"] == 0


def test_score_ignores_duplicates_and_handles_empty(client):
    q = QUIZ["questions"][0]
    dup = [{"question_id": q["id"], "choice": q["answer"]}] * 3
    res = client.post("/api/quiz/score", json={"answers": dup}).get_json()
    assert res["total"] == 1 and res["correct"] == 1
    assert client.post("/api/quiz/score", json={"answers": []}).get_json() == {
        "correct": 0, "total": 0, "percent": 0, "details": []}
    assert client.post("/api/quiz/score", json={"answers": "x"}).status_code == 400


def test_malformed_json_returns_400_not_500(client):
    assert client.post('/api/quiz/answer', json=['wrong']).status_code == 400
    assert client.post('/api/quiz/score', json=['wrong']).status_code == 400
    assert client.post('/api/quiz/score', json={'answers': [None]}).status_code == 400
    assert client.post('/api/quiz/score', json={'answers': ['wrong']}).status_code == 400
    assert client.post('/api/quiz/answer', json={'question_id': [], 'choice': 0}).status_code == 400
    assert client.post('/api/quiz/score', json={'answers': [{'question_id': [], 'choice': 0}]}).status_code == 400

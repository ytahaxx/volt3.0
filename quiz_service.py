"""Quiz pédagogique. Les questions viennent de data/quiz.json et chacune renvoie
à une proposition vérifiée (champ `proposition_id`) pour la référence au programme."""
import json
from pathlib import Path


class QuizService:
    def __init__(self, quiz_json_path):
        data = json.loads(Path(quiz_json_path).read_text(encoding="utf-8"))
        self.levels = data["levels"]
        self.questions = {q["id"]: q for q in data["questions"]}
        self._order = [q["id"] for q in data["questions"]]

    def level_slugs(self):
        return [lv["slug"] for lv in self.levels]

    def get_questions(self, level="tous"):
        """Questions SANS la bonne réponse (celle-ci n'est révélée qu'après réponse)."""
        out = []
        for qid in self._order:
            q = self.questions[qid]
            if level != "tous" and q["level"] != level:
                continue
            out.append({
                "id": q["id"], "level": q["level"], "question": q["question"],
                "choices": q["choices"], "proposition_id": q["proposition_id"],
            })
        return out

    def check_answer(self, question_id, choice):
        if not isinstance(question_id, int) or isinstance(question_id, bool):
            raise ValueError("identifiant de question invalide")
        q = self.questions.get(question_id)
        if q is None:
            raise KeyError(question_id)
        if not isinstance(choice, int) or isinstance(choice, bool) or not (0 <= choice < len(q["choices"])):
            raise ValueError("choix invalide")
        return {
            "question_id": q["id"],
            "correct": choice == q["answer"],
            "correct_index": q["answer"],
            "correct_answer": q["choices"][q["answer"]],
            "explanation": q["explanation"],
            "proposition_id": q["proposition_id"],
        }

    def score(self, answers):
        """answers : liste de {question_id, choice}. Une question répétée n'est comptée qu'une fois."""
        seen, correct, details = set(), 0, []
        for a in answers:
            if not isinstance(a, dict):
                raise ValueError("Chaque réponse doit être un objet JSON.")
            qid = a.get("question_id")
            if not isinstance(qid, int) or isinstance(qid, bool):
                raise ValueError("identifiant de question invalide")
            if qid in seen or qid not in self.questions:
                continue
            seen.add(qid)
            res = self.check_answer(qid, a.get("choice"))
            correct += 1 if res["correct"] else 0
            details.append({"question_id": qid, "correct": res["correct"]})
        total = len(seen)
        return {"correct": correct, "total": total,
                "percent": round(100 * correct / total) if total else 0, "details": details}

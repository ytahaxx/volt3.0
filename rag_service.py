"""Assistant RAG (Retrieval-Augmented Generation).

Pipeline :
  1. corpus   : propositions vérifiées (+ passages du PDF officiel s'il est présent)
  2. index    : TF-IDF (unigrammes + bigrammes, racinisation légère) — scikit-learn
  3. retrieve : similarité cosinus question ↔ passages
  4. generate : fournisseur LLM configurable (démo / Anthropic / OpenAI)
  5. sources  : chaque réponse renvoie les passages utilisés avec leur référence

Choix technique : un index lexical TF-IDF fonctionne hors ligne, sans clé ni téléchargement
de modèle. L'interface `RagIndex.retrieve()` est isolée : on peut la remplacer par une recherche
vectorielle (embeddings + ChromaDB/FAISS) sans toucher au reste.
"""
import re

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel

from services.document_parser import pdf_to_passages
from services.llm_providers import DemoProvider, LLMError, get_provider
from services.text_utils import analyzer, normalize

VOTE_PATTERN = re.compile(
    r"(pour qui voter|faut[- ]il voter|dois[- ]je voter|devrais[- ]je voter|voter (pour|volt)|"
    r"votez (pour|volt)|quel (parti|candidat) (choisir|voter)|meilleur (parti|candidat)|"
    r"(conseill|recommand)\w* .{0,30}vot)"
)

VOTE_REPLY = (
    "Volt Explorer est un outil d'information : je ne donne pas de conseil de vote et je ne cherche "
    "pas à convaincre. Je peux en revanche vous présenter ce que dit le programme officiel sur un "
    "sujet précis (par exemple : l'éducation, le climat ou le numérique), avec les sources."
)
NOT_FOUND_REPLY = (
    "Je n'ai pas trouvé de passage du programme officiel qui réponde à cette question. "
    "Je préfère ne rien affirmer plutôt que d'inventer. Vous pouvez reformuler avec d'autres mots-clés, "
    "ou parcourir les thématiques et la recherche de l'application."
)
EMPTY_REPLY = "Pouvez-vous préciser votre question ? Par exemple : « Que propose le programme sur le climat ? »"


def build_corpus(propositions, pdf_path=None, source_url=""):
    """Passages officiels. Les explications complémentaires (`details`, non officielles) en sont exclues."""
    passages = []
    for p in propositions:
        text = p["summary"] + " Mesures : " + " ; ".join(p["measures"]) + "."
        passages.append({
            "id": f"prop-{p['id']}",
            "kind": "proposition",
            "title": p["title"],
            "text": text,
            "index_text": " ".join([p["title"], p["summary"], " ".join(p["measures"]),
                                    " ".join(p["keywords"]), p["subcategory"]]),
            "ref": p["section_ref"],
            "url": p["source_url"],
            "proposition_id": p["id"],
        })
    if pdf_path:
        passages.extend(pdf_to_passages(pdf_path, source_url))
    return passages


class RagIndex:
    def __init__(self, passages):
        self.passages = passages
        self.vectorizer = TfidfVectorizer(analyzer=analyzer, sublinear_tf=True)
        self.matrix = self.vectorizer.fit_transform([p["index_text"] for p in passages])

    def _coverage(self, question_terms, passage_index):
        """Part des mots significatifs de la question présents dans le passage."""
        if not question_terms:
            return 0.0
        vocab = self.vectorizer.vocabulary_
        row = self.matrix[passage_index]
        hit = 0
        for term in question_terms:
            col = vocab.get(term)
            if col is not None and row[0, col] > 0:
                hit += 1
        return hit / len(question_terms)

    def retrieve(self, question, k=4, min_score=0.08, min_coverage=0.5, strong_score=0.3):
        """Passages les plus proches de la question.

        Un passage est retenu si son score dépasse `min_score` ET si, soit la moitié au moins des
        mots significatifs de la question s'y retrouvent, soit le score est très élevé. Cela évite
        de « trouver » une réponse à partir d'un seul mot générique (ex. « recette », « monde »).
        """
        terms = [t for t in analyzer(question) if "_" not in t]
        if not terms:
            return []
        q_vec = self.vectorizer.transform([question])
        scores = linear_kernel(q_vec, self.matrix).ravel()
        order = scores.argsort()[::-1][:k]
        kept = []
        for i in order:
            if scores[i] < min_score:
                continue
            if scores[i] >= strong_score or self._coverage(terms, i) >= min_coverage:
                kept.append(dict(self.passages[i], score=float(scores[i])))
        return kept


class RagService:
    def __init__(self, propositions, config):
        self.config = config
        pdf_path = config.get("PROGRAMME_PDF")
        source_url = propositions[0]["source_url"] if propositions else ""
        self.index = RagIndex(build_corpus(propositions, pdf_path, source_url))
        self.provider, self.notice = get_provider(config)

    @property
    def mode(self):
        return self.provider.name

    def answer(self, question):
        question = (question or "").strip()
        base = {"mode": self.mode, "notice": self.notice, "sources": []}
        if not question:
            return dict(base, answer=EMPTY_REPLY, status="empty")
        if VOTE_PATTERN.search(normalize(question)):
            return dict(base, answer=VOTE_REPLY, status="refused_vote")

        passages = self.index.retrieve(question, self.config.get("RAG_TOP_K", 4),
                                       self.config.get("RAG_MIN_SCORE", 0.08))
        if not passages:
            return dict(base, answer=NOT_FOUND_REPLY, status="not_found")

        notice = self.notice
        try:
            text = self.provider.generate(question, passages)
        except LLMError as exc:
            text = DemoProvider().generate(question, passages)
            notice = f"{exc} — réponse générée en mode démonstration."
        sources = [{
            "label": f"S{i}", "title": p["title"], "ref": p["ref"], "url": p["url"],
            "proposition_id": p["proposition_id"], "kind": p["kind"], "score": round(p["score"], 3),
            "excerpt": p["text"],
        } for i, p in enumerate(passages, start=1)]
        return {"answer": text, "sources": sources, "mode": self.mode, "notice": notice, "status": "ok"}

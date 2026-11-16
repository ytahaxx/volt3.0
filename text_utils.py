"""Outils de normalisation de texte français partagés par la recherche et le RAG."""
import re
import unicodedata

STOPWORDS = {
    "le", "la", "les", "l", "un", "une", "des", "du", "de", "d", "et", "ou", "en", "au", "aux", "a",
    "dans", "pour", "par", "sur", "sous", "avec", "sans", "ce", "cette", "ces", "se", "sa", "son", "ses",
    "qui", "que", "qu", "quoi", "quel", "quelle", "quels", "quelles", "est", "sont", "il", "elle", "ils",
    "on", "nous", "vous", "je", "tu", "y", "ne", "pas", "plus", "au", "leur", "leurs", "mais", "donc",
    "volt", "propose", "proposent", "proposer", "propositions", "proposition", "programme", "prevoit",
    "prevoir", "prevu", "concernant", "concerne", "mesures", "mesure", "dit", "dire", "veut", "veulent",
    "parle", "parler", "savoir", "peux", "peut", "puis", "quels", "quoi", "comment", "pourquoi",
    "expliquer", "explique", "explication", "sujet", "propos", "donne", "donner", "moi", "me", "toi",
    "france", "europe", "europeen", "europeenne", "ue",
}
# Remarque : « europe/ue » sont retirés des requêtes de l'assistant car presque toutes les
# mesures du programme les concernent ; ils restent actifs dans la recherche par mot-clé
# (voir search_service, qui n'utilise pas cette liste).

_WORD_RE = re.compile(r"[a-z0-9]+")


def normalize(text):
    """Minuscule, sans accents, apostrophes typographiques unifiées."""
    text = (text or "").replace("’", "'").replace("œ", "oe").replace("Œ", "oe")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return text.lower()


def stem(word):
    """Racinisation très légère (pluriels) : suffisant pour apparier « transports » et « transport »."""
    if len(word) > 4 and word.endswith("aux"):
        return word[:-3] + "al"
    if len(word) > 3 and word[-1] in "sx":
        return word[:-1]
    return word


def tokens(text, drop_stopwords=True):
    words = _WORD_RE.findall(normalize(text))
    if drop_stopwords:
        words = [w for w in words if w not in STOPWORDS]
    return [stem(w) for w in words]


def analyzer(text):
    """Analyseur pour TfidfVectorizer : unigrammes + bigrammes de mots racinisés."""
    toks = tokens(text)
    return toks + [f"{a}_{b}" for a, b in zip(toks, toks[1:])]

"""Étapes 1 à 3 du pipeline RAG : PDF → texte → nettoyage → passages.

Le PDF officiel (data/programme.pdf) est OPTIONNEL : s'il est présent, ses passages
(avec numéro de page réel) sont ajoutés à l'index. Pour le télécharger :
https://voltfrance.org/storage/pdf/volt-ecp_fr.pdf
"""
import re
from pathlib import Path


def extract_pages(pdf_path):
    """Retourne [(numero_page, texte)] via pypdf (import différé : dépendance optionnelle)."""
    from pypdf import PdfReader

    reader = PdfReader(str(pdf_path))
    return [(i, page.extract_text() or "") for i, page in enumerate(reader.pages, start=1)]


def clean_text(text):
    text = text.replace("­", "")                      # traits d'union conditionnels
    text = re.sub(r"-\n(?=[a-zàâçéèêëîïôûùüÿœ])", "", text)  # mots coupés en fin de ligne
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{2,}", "\n\n", text)
    return text.strip()


def chunk_text(text, max_chars=700, overlap=1):
    """Découpe en passages de ~max_chars en respectant les phrases ; `overlap` = nb de phrases reprises."""
    sentences = [s.strip() for s in re.split(r"(?<=[.!?;:])\s+|\n+", text) if s.strip()]
    chunks, current = [], []
    for s in sentences:
        if current and sum(len(x) + 1 for x in current) + len(s) > max_chars:
            chunks.append(" ".join(current))
            current = current[-overlap:] if overlap else []
        current.append(s)
    if current:
        chunks.append(" ".join(current))
    return chunks


def pdf_to_passages(pdf_path, source_url, max_chars=700):
    """Passages du PDF au format commun de l'index RAG ([] si le fichier est absent)."""
    path = Path(pdf_path)
    if not path.exists():
        return []
    passages = []
    for page_no, raw in extract_pages(path):
        for n, chunk in enumerate(chunk_text(clean_text(raw), max_chars), start=1):
            passages.append({
                "id": f"pdf-p{page_no}-{n}",
                "kind": "pdf",
                "title": f"Programme officiel (PDF), page {page_no}",
                "text": chunk,
                "index_text": chunk,
                "ref": f"Programme officiel (PDF), page {page_no}",
                "url": source_url,
                "proposition_id": None,
            })
    return passages

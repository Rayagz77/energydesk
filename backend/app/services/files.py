"""Controle des fichiers televerses : type reel (signature), nom nettoye."""

import re
import unicodedata

# Types autorises, reconnus par leur signature binaire ("magic bytes") et non par l'extension
# ou le Content-Type envoye par le navigateur, qui sont falsifiables.
_SIGNATURES: list[tuple[bytes, str]] = [
    (b"%PDF-", "application/pdf"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
]

ALLOWED_TYPES = {mime for _, mime in _SIGNATURES}


def detect_content_type(data: bytes) -> str | None:
    for signature, mime in _SIGNATURES:
        if data.startswith(signature):
            return mime
    return None


def sanitize_filename(filename: str | None) -> str:
    """Garde un nom lisible pour l'affichage, sans chemin ni caracteres dangereux."""
    name = (filename or "fichier").replace("\\", "/").split("/")[-1]
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    name = re.sub(r"[^A-Za-z0-9._ -]", "_", name).strip(" .")
    return (name or "fichier")[:255]

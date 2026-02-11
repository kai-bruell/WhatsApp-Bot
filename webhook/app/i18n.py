"""
i18n — Multi-Language Support fuer Bot-Texte.

Laedt alle .txt-Dateien aus app/lang/, erkennt Sprache anhand der
Telefonvorwahl und gibt uebersetzte Texte zurueck.
"""

from pathlib import Path

# ---------------------------------------------------------------------------
# Konfiguration
# ---------------------------------------------------------------------------

_LANG_DIR = Path(__file__).parent / "lang"

DEFAULT_LANG = "en"

PHONE_PREFIXES: dict[str, str] = {
    "49": "de",   # Deutschland
    "43": "de",   # Oesterreich
    "41": "de",   # Schweiz (deutschsprachig als Default)
    "1": "en",    # USA / Kanada
    "44": "en",   # UK
}

# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def _parse_lang_file(path: Path) -> dict[str, str]:
    """Parst eine .txt-Sprachdatei und gibt ein dict {key: value} zurueck."""
    entries: dict[str, str] = {}
    current_key: str | None = None
    lines_buf: list[str] = []

    def _flush() -> None:
        nonlocal current_key, lines_buf
        if current_key is not None:
            entries[current_key] = "\n".join(lines_buf)
            current_key = None
            lines_buf = []

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        stripped = raw_line.strip()

        # Leerzeile
        if not stripped:
            if current_key is not None:
                # Leerzeile innerhalb eines Mehrzeilenwerts
                lines_buf.append("")
            continue

        # Kommentar
        if stripped.startswith("#"):
            continue

        # Section-Header (rein organisatorisch)
        if stripped.startswith("[") and stripped.endswith("]"):
            _flush()
            continue

        # Key = Value
        if "=" in raw_line and not raw_line[0].isspace():
            _flush()
            key, _, value = raw_line.partition("=")
            key = key.strip()
            value = value.strip()
            if value:
                # Einzeiler
                entries[key] = value
            else:
                # Mehrzeilig — Folgezeilen sammeln
                current_key = key
                lines_buf = []
            continue

        # Fortsetzungszeile (mit fuehrendem Whitespace)
        if current_key is not None and raw_line[0].isspace():
            lines_buf.append(raw_line.strip())
            continue

    _flush()
    return entries


# ---------------------------------------------------------------------------
# Alle Sprachen laden
# ---------------------------------------------------------------------------

_translations: dict[str, dict[str, str]] = {}


def _load_all() -> None:
    """Laedt alle .txt-Dateien aus dem lang/-Verzeichnis."""
    if not _LANG_DIR.is_dir():
        return
    for txt_file in _LANG_DIR.glob("*.txt"):
        lang_code = txt_file.stem.split("_", 1)[0]  # z.B. "de" aus "de_deutsch_german"
        _translations[lang_code] = _parse_lang_file(txt_file)


_load_all()

# ---------------------------------------------------------------------------
# Oeffentliche API
# ---------------------------------------------------------------------------

def detect_lang(phone: str) -> str:
    """Erkennt die Sprache anhand der Telefonvorwahl."""
    # Fuehrende '+' und Leerzeichen entfernen
    digits = phone.lstrip("+").replace(" ", "").replace("-", "")
    # Laengste Vorwahl zuerst pruefen (3, 2, 1 Stellen)
    for length in (3, 2, 1):
        prefix = digits[:length]
        if prefix in PHONE_PREFIXES:
            lang = PHONE_PREFIXES[prefix]
            if lang in _translations:
                return lang
    return DEFAULT_LANG


def t(key: str, lang: str, **kwargs: object) -> str:
    """Gibt den uebersetzten Text fuer key in der Sprache lang zurueck."""
    lang_dict = _translations.get(lang) or _translations.get(DEFAULT_LANG, {})
    text = lang_dict.get(key)
    if text is None:
        # Fallback auf Default-Sprache
        text = _translations.get(DEFAULT_LANG, {}).get(key, key)
    if kwargs:
        text = text.format(**kwargs)
    return text

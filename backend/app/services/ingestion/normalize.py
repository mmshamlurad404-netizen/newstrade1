import re
import unicodedata

URL_RE = re.compile(r"https?://\S+")
EMOJI_RE = re.compile(
    "[\U0001F000-\U0001FAFF\U00002700-\U000027BF\U0001F1E6-\U0001F1FF]+"
)
ZERO_WIDTH_RE = re.compile("[\u200b-\u200f\u202a-\u202e\ufeff]")
DELIMITER_TOKENS = ("<DATA>", "</DATA>", "<|", "|>")


def strip_control_chars(text: str) -> str:
    return "".join(ch for ch in text if ch == "\n" or ch >= " ")


def neutralize_delimiters(text: str) -> str:
    for token in DELIMITER_TOKENS:
        text = text.replace(token, " ")
    return text


def normalize(text: str) -> tuple[str, list[str]]:
    links = URL_RE.findall(text)
    text = URL_RE.sub(" ", text)
    text = EMOJI_RE.sub(" ", text)
    text = ZERO_WIDTH_RE.sub("", text)
    text = neutralize_delimiters(text)
    text = unicodedata.normalize("NFKC", text)
    text = strip_control_chars(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text, links

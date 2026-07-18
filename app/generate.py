from __future__ import annotations

import re

from app.foundry_runtime import FoundryUnavailable, runtime
from app.retrieve import RetrievedChunk


SYSTEM_PROMPT = """Sen yerel calisan bir RAG asistanisin.
Sadece verilen CONTEXT bolumundeki bilgilere dayanarak cevap ver.
Context yeterli degilse bunu acikca soyle; tahmin uretme.
Cevabi Turkce, kisa, net ve kaynak dosya adlariyla ver."""


class AnswerGenerator:
    def __init__(self, use_foundry: bool = True) -> None:
        self._foundry: _FoundryChatClient | None = None
        self._use_foundry = use_foundry
        self._attempted_foundry = not use_foundry
        self.provider = "foundry-lazy" if use_foundry else "extractive-fallback"

    def answer(self, question: str, chunks: list[RetrievedChunk]) -> str:
        if not chunks:
            return "Bu soruyu cevaplamak icin veritabaninda yeterli dokuman yok."

        if self._use_foundry and not self._attempted_foundry:
            self._attempted_foundry = True
            print("Foundry Local modeli hazirlaniyor; ilk calismada indirme/yukleme zaman alabilir...")
            self._foundry = _try_create_foundry_chat_client()
            self.provider = "foundry" if self._foundry is not None else "extractive-fallback"

        if self._foundry is not None:
            try:
                return self._foundry.answer(question, chunks)
            except Exception as exc:
                print(f"Foundry chat kullanilamadi, fallback kullaniliyor: {exc}")
                self._foundry = None
                self.provider = "extractive-fallback"

        return _fallback_answer(question, chunks)


class _FoundryChatClient:
    def __init__(self) -> None:
        self.client, self.model = runtime.load_chat_client()

    def answer(self, question: str, chunks: list[RetrievedChunk]) -> str:
        context = _format_context(chunks)
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"CONTEXT:\n{context}\n\nSORU: {question}",
            },
        ]
        response = self.client.complete_chat(messages)
        return _extract_message_text(response)


def _try_create_foundry_chat_client() -> _FoundryChatClient | None:
    try:
        return _FoundryChatClient()
    except FoundryUnavailable as exc:
        print(f"Foundry Local hazir degil: {exc}")
        return None
    except Exception as exc:
        print(f"Foundry Local baslatilamadi: {exc}")
        return None


def _format_context(chunks: list[RetrievedChunk]) -> str:
    parts = []
    for index, chunk in enumerate(chunks, start=1):
        parts.append(
            f"[{index}] Source: {chunk.source}, chunk {chunk.chunk_index}\n{chunk.content}"
        )
    return "\n\n".join(parts)


def _fallback_answer(question: str, chunks: list[RetrievedChunk]) -> str:
    relevant_chunks = [chunk for chunk in chunks if chunk.score >= 0.05]
    if not relevant_chunks:
        return (
            "Dokumanlarda bu soruyu guvenilir bicimde cevaplayacak yeterli baglam bulamadim. "
            "Daha ilgili dokuman ekleyip `python -m app.ingest` komutunu tekrar calistir."
        )

    keywords = _keywords(question)
    week_answer = _week_answer(question, relevant_chunks)
    if week_answer:
        return week_answer

    selected_sentences: list[tuple[str, str]] = []

    for chunk in relevant_chunks:
        for sentence in _sentences(chunk.content):
            score = sum(1 for word in keywords if word in sentence.lower())
            if score > 0:
                selected_sentences.append((chunk.source, sentence))

    if not selected_sentences:
        selected_sentences = [(relevant_chunks[0].source, _excerpt(relevant_chunks[0].content))]

    selected_sentences = selected_sentences[:4]
    lines = [
        "Foundry Local modeli hazir olmadigi icin extractive fallback cevabi veriyorum:",
        "",
    ]
    for source, sentence in selected_sentences:
        lines.append(f"- {sentence} ({source})")
    lines.append("")
    lines.append("Not: Gercek uretken cevap icin Foundry Local SDK ve model kurulumu tamamlanmali.")
    return "\n".join(lines)


def _extract_message_text(response: object) -> str:
    choices = getattr(response, "choices", None)
    if choices:
        first = choices[0]
        message = getattr(first, "message", None)
        if message is not None:
            content = getattr(message, "content", None)
            if content:
                return str(content)
        delta = getattr(first, "delta", None)
        if delta is not None:
            content = getattr(delta, "content", None)
            if content:
                return str(content)
    return str(response)


def _keywords(question: str) -> set[str]:
    stopwords = {
        "bir",
        "bu",
        "ne",
        "nedir",
        "nasil",
        "nasıl",
        "icin",
        "için",
        "mi",
        "mı",
        "mu",
        "mü",
        "ve",
        "ile",
        "da",
        "de",
        "the",
        "what",
        "how",
    }
    keywords = {
        token
        for token in re.findall(r"[a-zA-ZğüşöçıİĞÜŞÖÇ]+|\d+", question.lower())
        if len(token) > 2 and token not in stopwords
    }
    expansions = {
        "hafta": {"week"},
        "haftasi": {"week"},
        "haftası": {"week"},
        "teslim": {"deliverable", "milestone", "documentation", "presentation"},
        "dokuman": {"document"},
        "doküman": {"document"},
        "kullaniliyor": {"use", "used"},
        "kullanılıyor": {"use", "used"},
    }
    for keyword in list(keywords):
        keywords.update(expansions.get(keyword, set()))
    return keywords


def _sentences(text: str) -> list[str]:
    sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]
    return sentences or [text.strip()]


def _excerpt(text: str, limit: int = 700) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    if len(compact) <= limit:
        return compact
    return compact[:limit].rsplit(" ", 1)[0] + "..."


def _week_answer(question: str, chunks: list[RetrievedChunk]) -> str | None:
    q = question.casefold()
    if "hafta" not in q and "week" not in q:
        return None

    numbers = re.findall(r"\d+", question)
    if not numbers:
        return None

    week = numbers[0]
    marker = re.compile(rf"\bweek\s+{re.escape(week)}\b", re.IGNORECASE)
    for chunk in chunks:
        if not marker.search(chunk.content):
            continue

        paragraphs = [part.strip() for part in re.split(r"\n{2,}", chunk.content) if part.strip()]
        start = 0
        for index, paragraph in enumerate(paragraphs):
            if marker.search(paragraph):
                start = index
                break

        selected = paragraphs[start : start + 7]
        if not selected:
            return None

        lines = [
            "Foundry Local modeli hazir olmadigi icin plan dokumanindan extractive fallback cevabi veriyorum:",
            "",
        ]
        for paragraph in selected:
            compact = _excerpt(paragraph, limit=320)
            prefix = "- "
            if marker.search(paragraph):
                prefix = ""
            lines.append(f"{prefix}{compact}")
        lines.append("")
        lines.append(f"Kaynak: {chunk.source}")
        return "\n".join(lines)

    return None

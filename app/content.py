# © 2026 Синакаев Фидель, Мучкаев Марк, Бутров Трофим, Борисов Никита, Попов Роман. Все права защищены. Исходный код: просмотр жюри для оценки; иное использование — по письменному разрешению правообладателей. Полные условия: LICENSE.
"""Local, source-grounded lecture notes and chapter headings."""

from __future__ import annotations

from collections import Counter
import math
import os
from pathlib import Path
import re
import subprocess


STOP = set("""а и но или да что как это вот ну уже еще ещё там тут где когда тогда если чтобы потому поэтому
который которая которые которого которой которых такой такая такие таком этого этот эта эти этим себе себя
очень просто вообще конечно наверное может можно нужно надо будет были была было есть быть нас вас они она
оно он мы вы ты я мне тебе ему им нам вам его её их для при над под про через без между после перед из за
по со от до на не ни же ли бы также сейчас потом здесь значит знаете знаешь думаю кажется давайте просто
какой какая какие каком сколько тоже только ведь хотя однако именно именно сразу вполне совсем каждый
ну-ка как-то как бы это-то так-то короче собственно говорят говорю сказал сказала говорили""".split())
FILLER = re.compile(r"^(?:(?:ну|вот|слушай|короче|знаешь|знаете|то есть|как бы|в общем|на самом деле)[,\s—-]+)+", re.I)
WORD = re.compile(r"[А-Яа-яЁёA-Za-z0-9-]{3,}")
DIRECT_ADDRESS = re.compile(r"\b(?:я|мы|ты|вы|мой|мои|моя|твой|твои|ваш|ваши|наш|наши|тебе|вам|давай|давайте|смотри|посмотри|представь)\b", re.I)
PROMOTION = re.compile(r"\b(?:подписк\w*|подпиш\w*|колокольчик\w*|комментари\w*|ютуб\w*|интроверт\w*|приложени\w*)\b", re.I)


def clean_sentence(text: str) -> str:
    text = re.sub(r"\b(?:э-э-э|а-а-а|м-м-м|эээ|ааа)\b", "", text, flags=re.I)
    text = re.sub(r"\s+", " ", text).strip(" —-\t\n")
    text = FILLER.sub("", text).strip(" —-\t\n")
    text = re.sub(r"\b(\w+)(?:\s+\1\b){2,}", r"\1", text, flags=re.I)
    if not text:
        return ""
    return text[0].upper() + text[1:]


def tokens(text: str) -> list[str]:
    return [word.lower() for word in WORD.findall(text)
            if word.lower() not in STOP and not PROMOTION.fullmatch(word)]


def sentences(segments: list[dict]) -> list[dict]:
    rows = []
    for segment in segments:
        parts = re.split(r"(?<=[.!?])\s+|\s+[—–]\s*", segment["text"])
        for part in parts:
            text = clean_sentence(part)
            words = WORD.findall(text)
            content = tokens(text)
            if 6 <= len(words) <= 42 and len(content) >= 3 and len(set(content)) >= 3:
                rows.append({"start": segment["start"], "text": text, "terms": set(content)})
    return rows


def chapter_groups(segments: list[dict]) -> list[tuple[float, list[dict]]]:
    if not segments:
        return []
    start = float(segments[0]["start"])
    end = max(float(seg["end"]) for seg in segments)
    span = max(0, end - start)
    chapter_count = min(10, max(1, math.ceil(span / 360)))
    if span < 240:
        chapter_count = 1
    boundaries = [0]
    for index in range(1, chapter_count):
        target = start + span * index / chapter_count
        choices = range(boundaries[-1] + 1, len(segments) - (chapter_count - index) + 1)
        candidates = [i for i in choices if abs(float(segments[i]["start"]) - target) <= 55]
        if not candidates:
            candidates = list(choices)
        if not candidates:
            break
        def boundary_score(i: int) -> float:
            pause = float(segments[i]["start"]) - float(segments[i - 1]["end"])
            return min(8, max(0, pause)) * 4 - abs(float(segments[i]["start"]) - target) / 12
        boundaries.append(max(candidates, key=boundary_score))
    boundaries.append(len(segments))
    return [(float(segments[a]["start"]), segments[a:b]) for a, b in zip(boundaries, boundaries[1:]) if a < b]


def ranked_sentences(group: list[dict]) -> list[dict]:
    candidates = sentences(group)
    if not candidates:
        return []
    frequency = Counter(term for row in candidates for term in row["terms"])
    def score(row: dict) -> float:
        terms = row["terms"]
        distinctiveness = sum(1 / (frequency[t] ** .4) for t in terms)
        words = len(WORD.findall(row["text"]))
        length = max(0, 1 - abs(words - 13) / 22)
        penalty = 2 if re.match(r"^(?:я|ты|мы|вы|он|она|они|это)\b", row["text"], re.I) else 0
        return distinctiveness + length * 2 - penalty
    return sorted(candidates, key=score, reverse=True)


def fallback_title(group: list[dict], used: set[str]) -> str:
    for row in ranked_sentences(group):
        if DIRECT_ADDRESS.search(row["text"]) or PROMOTION.search(row["text"]):
            continue
        phrase = row["text"].split(". ", 1)[0].split(", ", 1)[0].rstrip(".!? :;—")
        words = phrase.split()
        if len(words) > 9:
            phrase = " ".join(words[:9]).rstrip(" ,:;—")
        if len(phrase.split()) < 3 or phrase.casefold() in used:
            continue
        used.add(phrase.casefold())
        return phrase
    terms = Counter(term for seg in group for term in tokens(seg["text"]))
    topic = " и ".join(word for word, _ in terms.most_common(2)) or "Содержание лекции"
    title = topic[0].upper() + topic[1:]
    used.add(title.casefold())
    return title


def fallback_notes(groups: list[tuple[float, list[dict]]], titles: list[str]) -> tuple[str, list[str]]:
    topics = [title.rstrip(".!? ") for title in titles[:4] if title.strip()]
    if not topics:
        return "Тема: содержание лекции.\nИтог: конспект появится после повторной обработки.", []
    note = "Тема: " + topics[0] + ".\nОсновные разделы:\n" + "\n".join(f"• {topic}" for topic in topics[1:])
    if len(topics) == 1:
        note += "\n• Основные понятия темы рассматриваются последовательно."
    note += "\nИтог: содержание лекции раскрывается через перечисленные разделы."
    return note, []


def model_response(binary: Path, model: Path, prompt: str, max_tokens: int) -> str:
    result = subprocess.run([str(binary), "-m", str(model), "-t", "1", "-c", "4096", "-n", str(max_tokens),
                             "--temp", "0.15", "--no-display-prompt", "--no-show-timings",
                             "--single-turn", "--simple-io", "-p", prompt],
                            capture_output=True, text=True, errors="replace", timeout=300,
                            env={**os.environ, "OMP_NUM_THREADS": "1"})
    if result.returncode:
        return ""
    if prompt in result.stdout:
        answer = result.stdout.split(prompt, 1)[1]
    elif " (truncated)\n" in result.stdout:
        answer = result.stdout.split(" (truncated)\n", 1)[1]
    else:
        return ""
    answer = answer.split("\n> ", 1)[0]
    answer = answer.split("Exiting...", 1)[0].strip()
    answer = re.sub(r"[ \t]+", " ", answer)
    return re.sub(r" *\n *", "\n", answer).strip()


def validated_model_recap(recap: str, parts: list[str], segments: list[dict]) -> str:
    """Accept only complete, distinct and source-grounded notebook notes."""
    lines = [re.sub(r"\s+", " ", line).strip() for line in recap.splitlines() if line.strip()]
    if not 6 <= len(lines) <= 8:
        return ""
    topic = re.fullmatch(r"Тема:\s*(.+)", lines[0], re.I)
    question = re.fullmatch(r"Главный вопрос:\s*(.+)", lines[1], re.I)
    conclusion = re.fullmatch(r"Итог:\s*(.+)", lines[-1], re.I)
    theses = [re.fullmatch(r"[•\-—]\s*(.+)", line) for line in lines[2:-1]]
    if not topic or not question or not conclusion or not 3 <= len(theses) <= 5 or not all(theses):
        return ""
    values = [topic.group(1), question.group(1), *(thesis.group(1) for thesis in theses), conclusion.group(1)]
    if not 40 <= len(recap.split()) <= 150 or DIRECT_ADDRESS.search(recap) or PROMOTION.search(recap):
        return ""
    for index, value in enumerate(values):
        words = WORD.findall(value)
        minimum = 1 if index == 0 else 3 if index == 1 else 4
        if not minimum <= len(words) <= 30 or "..." in value or "…" in value:
            return ""
        if not value.endswith("?" if index == 1 else (".", "!", "?")):
            return ""
        if value.count("(") != value.count(")") or value.count("«") != value.count("»"):
            return ""
        if re.search(r"\b(?:и|но|а|что|как|чтобы|потому|для|на|в|с|к|по|о|об)\s*[.!?]$", value, re.I):
            return ""
    thesis_terms = [set(tokens(thesis.group(1))) for thesis in theses]
    if any(len(terms) < 3 for terms in thesis_terms):
        return ""
    for index, left in enumerate(thesis_terms):
        for right in thesis_terms[index + 1:]:
            if len(left & right) / min(len(left), len(right)) > .65:
                return ""
    source_terms = set(tokens(" ".join(parts)))
    recap_terms = set(tokens(recap))
    overlap = len(recap_terms & source_terms) / max(1, len(recap_terms))
    if not .2 <= overlap <= .88:
        return ""
    exact_quotes = sum(1 for sentence in sentences(segments) if len(sentence["text"].split()) >= 8
                       and sentence["text"].casefold() in recap.casefold())
    if exact_quotes > 1:
        return ""
    section_terms = [set(tokens(part)) for part in parts if part]
    if len(section_terms) >= 3:
        frequency = Counter(term for section in section_terms for term in section)
        distinctive = [section - {term for term in section if frequency[term] > len(section_terms) // 2}
                       for section in section_terms]
        coverable = [section for section in distinctive if section]
        covered = sum(bool(section & recap_terms) for section in coverable)
        if len(coverable) >= 3 and covered < min(3, max(2, math.ceil(len(coverable) * .4))):
            return ""
    return "\n".join([f"Тема: {values[0]}", f"Главный вопрос: {values[1]}",
                      *(f"• {value}" for value in values[2:-1]), f"Итог: {values[-1]}"])


def local_model_notes(groups: list[tuple[float, list[dict]]], binary: Path, model: Path):
    selected = []
    for _, group in groups:
        suitable = [row for row in ranked_sentences(group)
                    if not DIRECT_ADDRESS.search(row["text"]) and not PROMOTION.search(row["text"])]
        best = sorted(suitable[:4], key=lambda row: row["start"])
        selected.append(" ".join(row["text"] for row in best)[:1000] or " ".join(seg["text"] for seg in group[:8])[:1000])
    titles = []
    for part in selected:
        title_prompt = ("Дай короткий нейтральный заголовок темы текста на русском языке (от 2 до 6 слов). "
                        "Не используй обращения к зрителю, рекламу, названия приложения и незаконченные фразы. "
                        "Ответь только заголовком.\nТекст:\n" + part[:650] + "\nЗаголовок:\n")
        title = clean_sentence(model_response(binary, model, title_prompt, 35)).strip("\"' .!?—-")
        title_terms = set(tokens(title))
        source_terms = set(tokens(part))
        if not (2 <= len(title.split()) <= 8 and len(title) <= 85 and re.search(r"[А-Яа-яЁё]", title)
                and len(title_terms) >= 2 and not DIRECT_ADDRESS.search(title) and not PROMOTION.search(title)
                and not re.search(r"\b(?:и|в|на|с|к|о|для|от|по)$", title, re.I)
                and len(title_terms & source_terms) / max(1, len(title_terms)) >= .65):
            title = ""
        titles.append(title)
    nonempty = [part for part in selected if part]
    part_limit = min(750, max(180, 2800 // max(1, len(nonempty)) - 12))
    prompt_parts = [part[:part_limit] for part in nonempty]
    source = "\n".join(f"Часть {index + 1}: {part}" for index, part in enumerate(prompt_parts))
    recap_prompt = (
        "Составь короткий учебный конспект лекции по-русски, чтобы его можно было переписать в тетрадь. "
        "Сформулируй своими словами, не копируй предложения и не собирай ответ из цитат. "
        "Укажи тему, главный вопрос, 3–5 содержательных тезисов и итог автора. "
        "Оставь только идеи, подтверждённые текстом; не выдумывай примеры и факты. "
        "Пиши ясно и компактно, без обращения к зрителю, личных местоимений, рекламы и призывов. "
        "Используй такой формат: «Тема: …\nГлавный вопрос: …\n• …\nИтог: …». Ответь только конспектом.\n"
        "Фрагменты лекции:\n" + source[:2900] + "\nКонспект:\n"
    )
    source_segments = [segment for _, group in groups for segment in group]
    recap = validated_model_recap(model_response(binary, model, recap_prompt, 260), prompt_parts, source_segments)
    return recap, titles


def summarize_and_outline(segments: list[dict], model_binary: Path | None = None,
                          model_file: Path | None = None) -> tuple[str, list[dict], list[str]]:
    if not segments:
        return "", [], []
    groups = chapter_groups(segments)
    used: set[str] = set()
    titles = [fallback_title(group, used) for _, group in groups]
    recap, theses = fallback_notes(groups, titles)
    if model_binary and model_file and model_binary.is_file() and model_file.is_file():
        generated = local_model_notes(groups, model_binary, model_file)
        if generated:
            model_recap, model_titles = generated
            if model_recap:
                recap, theses = model_recap, []
            seen = set()
            resolved = []
            for candidate, fallback in zip(model_titles, titles):
                key = re.sub(r"\W+", " ", candidate.casefold().replace("ё", "е")).strip()
                title = candidate if candidate and key not in seen else fallback
                seen.add(re.sub(r"\W+", " ", title.casefold().replace("ё", "е")).strip())
                resolved.append(title)
            titles = resolved
    outline = [{"time": round(start), "title": title} for (start, _), title in zip(groups, titles)]
    counts = Counter(term for seg in segments for term in tokens(seg["text"]))
    keywords = [word for word, _ in counts.most_common(10)]
    summary = recap.strip()
    if theses:
        summary += "\n\nТезисы:\n" + "\n".join("• " + thesis for thesis in theses)
    return summary, outline, keywords

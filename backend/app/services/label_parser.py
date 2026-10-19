import re


_FIELD_PATTERNS = {
    "sugar_g": re.compile(
        r"^[ \t]*total[ \t]+sugars?[ \t]*"
        r"(?:\([ \t]*(?P<label_unit>g|grams?)[ \t]*\))?[ \t]*"
        r"[:\-]?[ \t]*(?:\r?\n[ \t]*)?"
        r"(?P<value>\d+(?:\.\d+)?)[ \t]*(?P<unit>g|grams?)?"
        r"(?:[ \t]+\d+(?:\.\d+)?[ \t]*%)?[ \t]*$",
        re.IGNORECASE | re.MULTILINE,
    ),
    "sodium_mg": re.compile(
        r"^[ \t]*sodium[ \t]*"
        r"(?:\([ \t]*(?P<label_unit>mg|milligrams?)[ \t]*\))?[ \t]*"
        r"[:\-]?[ \t]*(?:\r?\n[ \t]*)?"
        r"(?P<value>\d+(?:\.\d+)?)[ \t]*(?P<unit>mg|milligrams?)?"
        r"(?:[ \t]+\d+(?:\.\d+)?[ \t]*%)?[ \t]*$",
        re.IGNORECASE | re.MULTILINE,
    ),
    "saturated_fat_g": re.compile(
        r"^[ \t]*saturated[ \t]+fat[ \t]*"
        r"(?:\([ \t]*(?P<label_unit>g|grams?)[ \t]*\))?[ \t]*"
        r"[:\-]?[ \t]*(?:\r?\n[ \t]*)?"
        r"(?P<value>\d+(?:\.\d+)?)[ \t]*(?P<unit>g|grams?)?"
        r"(?:[ \t]+\d+(?:\.\d+)?[ \t]*%)?[ \t]*$",
        re.IGNORECASE | re.MULTILINE,
    ),
}
_BASIS_PATTERNS = {
    "per_serving": re.compile(
        r"\b(?:amount\s+)?per\s+serving\b",
        re.IGNORECASE,
    ),
    "per_100g": re.compile(r"\bper\s*100\s*g\b", re.IGNORECASE),
}
_SERVING_SIZE = re.compile(
    r"^[ \t]*serving[ \t]+size[ \t]*:?[ \t]*"
    r"(?P<size>.*?)(?=[ \t]+(?:amount|rda)\b|[ \t]+%|$)",
    re.IGNORECASE,
)
_PRODUCT_NAME = re.compile(
    r"^\s*product(?:\s+name)?\s*:\s*(.*?)\s*$",
    re.IGNORECASE,
)
_INGREDIENTS = re.compile(r"^\s*ingredients?\s*:\s*(.*?)\s*$", re.IGNORECASE)
_INGREDIENT_STOP = re.compile(
    r"^\s*(?:contains|may\s+contain|allergen(?:s)?(?:\s+information)?|"
    r"nutrition\s+facts|warning|storage)\s*:",
    re.IGNORECASE,
)


def _unique_line_match(pattern: re.Pattern[str], lines: list[str]) -> tuple[str, re.Match[str]] | None:
    matches = [(line.strip(), pattern.match(line)) for line in lines]
    matches = [(line, match) for line, match in matches if match is not None]
    if len(matches) != 1:
        return None
    line, match = matches[0]
    return line, match


def _parse_nutrient(
    field: str,
    text: str,
) -> dict[str, float | str | None | bool]:
    pattern = _FIELD_PATTERNS[field]
    value = None
    source_text = None
    matches = list(pattern.finditer(text))
    expected_unit = "mg" if field == "sodium_mg" else "g"
    if len(matches) == 1:
        match = matches[0]
        label_unit = match.group("label_unit")
        value_unit = match.group("unit")
        if (
            (label_unit is None or label_unit.lower().startswith(expected_unit))
            and (value_unit is None or value_unit.lower().startswith(expected_unit))
            and (label_unit is not None or value_unit is not None)
        ):
            value = float(match.group("value"))
            source_text = " ".join(match.group(0).split())

    return {
        "value": value,
        "source_text": source_text,
        "confidence": None,
        "needs_review": True,
    }


def _extract_basis(text: str) -> str | None:
    has_per_serving = bool(_BASIS_PATTERNS["per_serving"].search(text))
    has_per_100g = bool(_BASIS_PATTERNS["per_100g"].search(text))
    if has_per_serving == has_per_100g:
        return None
    return "per_serving" if has_per_serving else "per_100g"


def _extract_single_value(
    pattern: re.Pattern[str],
    lines: list[str],
    group: int | str = 1,
) -> str | None:
    matched = _unique_line_match(pattern, lines)
    if matched is None:
        return None
    value = matched[1].group(group).strip()
    if not value:
        return None
    return re.sub(
        r"(?<=\d)[ \t]*(?=g\b)",
        " ",
        value,
        flags=re.IGNORECASE,
    )


def _extract_ingredients(lines: list[str]) -> str | None:
    starts = [
        (index, match.group(1).strip())
        for index, line in enumerate(lines)
        if (match := _INGREDIENTS.match(line))
    ]
    if len(starts) != 1:
        return None

    start_index, first_line = starts[0]
    parts = [first_line] if first_line else []
    for line in lines[start_index + 1 :]:
        if _INGREDIENT_STOP.match(line):
            break
        if line.strip():
            parts.append(line.strip())
    ingredients_text = " ".join(parts).strip()
    return ingredients_text or None


def _split_ingredients(ingredients_text: str) -> list[str] | None:
    parts: list[str] = []
    depth = 0
    start = 0
    pairs = {"(": ")", "[": "]"}
    closing = {pair: opening for opening, pair in pairs.items()}

    for index, character in enumerate(ingredients_text):
        if character in pairs:
            depth += 1
        elif character in closing:
            depth -= 1
            if depth < 0:
                return None
        elif character == "," and depth == 0:
            parts.append(ingredients_text[start:index].strip())
            start = index + 1

    if depth != 0:
        return None

    parts.append(ingredients_text[start:].strip())
    if not parts or any(not part for part in parts):
        return None
    return parts


def parse_label_text(ocr_text: str) -> dict:
    """Parse conservative candidate fields from raw OCR text."""
    lines = ocr_text.splitlines()
    product_name = _extract_single_value(_PRODUCT_NAME, lines)
    serving_size_text = _extract_single_value(_SERVING_SIZE, lines, "size")
    ingredients_text = _extract_ingredients(lines)
    ingredients = (
        _split_ingredients(ingredients_text)
        if ingredients_text is not None
        else None
    )

    nutrients = {
        field: _parse_nutrient(field, ocr_text)
        for field in ("sugar_g", "sodium_mg", "saturated_fat_g")
    }

    review_required_fields = [
        "product_name",
        "basis",
        "serving_size_text",
        *nutrients,
        "ingredients",
    ]

    return {
        "product_name": {
            "value": product_name,
            "source_text": product_name,
            "confidence": None,
            "needs_review": True,
        },
        "basis": _extract_basis(ocr_text),
        "serving_size_text": serving_size_text,
        "nutrients": nutrients,
        "ingredients_text": ingredients_text,
        "ingredients": ingredients,
        "review_required_fields": review_required_fields,
        "ocr_text": ocr_text,
    }

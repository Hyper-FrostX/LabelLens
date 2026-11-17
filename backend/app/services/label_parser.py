import re

_UNIT_PATTERNS = {
    "g": r"g|grams?",
    "mg": r"mg|milligrams?",
    "kcal": r"kcal|kilocalories?",
    "kJ": r"kj|kilojoules?",
}
_UNIT_NORMALIZATION = {
    "g": "g",
    "gram": "g",
    "grams": "g",
    "kg": "kg",
    "kilogram": "kg",
    "kilograms": "kg",
    "mg": "mg",
    "milligram": "mg",
    "milligrams": "mg",
    "ml": "ml",
    "milliliter": "ml",
    "milliliters": "ml",
    "millilitre": "ml",
    "millilitres": "ml",
    "l": "l",
    "liter": "l",
    "liters": "l",
    "litre": "l",
    "litres": "l",
    "oz": "oz",
    "ounce": "oz",
    "ounces": "oz",
    "floz": "fl oz",
    "cup": "cup",
    "cups": "cup",
    "tablespoon": "tbsp",
    "tablespoons": "tbsp",
    "tbsp": "tbsp",
    "teaspoon": "tsp",
    "teaspoons": "tsp",
    "tsp": "tsp",
    "piece": "piece",
    "pieces": "piece",
    "pack": "pack",
    "packs": "pack",
    "kcal": "kcal",
    "kilocalorie": "kcal",
    "kilocalories": "kcal",
    "kj": "kJ",
    "kilojoule": "kJ",
    "kilojoules": "kJ",
}
_NUMERIC_TOKEN = re.compile(
    r"(?<![\w<>=,])(?P<value>"
    r"\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)"
    r"(?:[ \t]*(?P<unit>kilocalories?|kcal|kilojoules?|kj|"
    r"milligrams?|mg|grams?|g))?(?![\d,])(?![ \t]*%)",
    re.IGNORECASE,
)

_NUTRIENT_DEFINITIONS = {
    "sugar_g": (r"(?:total[ \t]+)?sugars?", "g"),
    "added_sugar_g": (r"(?:(?:includes?|with)[ \t]+)?added[ \t]+sugars?", "g"),
    "sodium_mg": (r"sodium", "mg"),
    "saturated_fat_g": (r"saturated[ \t]+fat", "g"),
    "energy_kcal": (r"(?:energy|calories?)", "kcal"),
    "energy_kj": (r"(?:energy|calories?)", "kJ"),
    "total_fat_g": (r"(?:total[ \t]+fat|fat)", "g"),
    "trans_fat_g": (r"trans[ \t]+fat", "g"),
    "carbohydrates_g": (
        r"(?:total[ \t]+)?(?:carbohydrates?|carbs?)",
        "g",
    ),
    "protein_g": (r"protein", "g"),
    "fiber_g": (r"(?:dietary[ \t]+)?fib(?:er|re)", "g"),
    "salt_g": (r"salt", "g"),
}
_NUTRIENT_PATTERNS = {
    field: re.compile(
        rf"^[ \t]*(?P<label>{label})(?=[ \t]*(?:\(|[:\-]|\d|$))"
        rf"(?:[ \t]*\([ \t]*(?P<label_unit>{_UNIT_PATTERNS[unit]})"
        rf"[ \t]*\))?[ \t]*[:\-]?[ \t]*(?P<rest>.*)$",
        re.IGNORECASE,
    )
    for field, (label, unit) in _NUTRIENT_DEFINITIONS.items()
}
_BASIS_PATTERNS = {
    "per_serving": re.compile(
        r"\b(?:(?:amount[ \t]*[:\-]?[ \t]*)?per[ \t]+"
        r"(?:serv(?:e|ing)))\b",
        re.IGNORECASE,
    ),
    "per_100g": re.compile(r"\bper[ \t]*100[ \t]*(?:g|grams?)\b", re.IGNORECASE),
    "per_100ml": re.compile(r"\bper[ \t]*100[ \t]*ml\b", re.IGNORECASE),
}
_SERVING_SIZE = re.compile(
    rf"^[ \t]*serving[ \t]+size"
    rf"(?:[ \t]*\([ \t]*(?P<label_unit>kg|{_UNIT_PATTERNS['g']}|"
    rf"{_UNIT_PATTERNS['mg']}|ml|millilit(?:er|re)s?|"
    rf"l|lit(?:er|re)s?|oz|ounces?|fl\.?\s*oz|"
    rf"cups?|tablespoons?|tbsp|teaspoons?|tsp|pieces?|packs?)[ \t]*\))?"
    rf"[ \t]*:?[ \t]*(?P<size>.*?)"
    r"(?=[ \t]+(?:amount|rda|servings?\s+per)\b|[ \t]+%|$)",
    re.IGNORECASE,
)
_SERVING_UNIT = re.compile(
    r"\b(fl\.?\s*oz|kg|g|grams?|mg|milligrams?|ml|millilit(?:er|re)s?|"
    r"l|lit(?:er|re)s?|oz|ounces?|cups?|tablespoons?|tbsp|"
    r"teaspoons?|tsp|pieces?|packs?)\b",
    re.IGNORECASE,
)
_PRODUCT_NAME = re.compile(
    r"^[ \t]*(?:"
    r"product(?:[ \t]+name)?|"
    r"(?:name(?:[ \t]+of)?(?:[ \t]+the)?[ \t]+(?:product|food))|"
    r"(?:food(?:[ \t]+name)?)"
    r")[ \t]*[:\-][ \t]*(?P<value>.+?)[ \t]*$",
    re.IGNORECASE,
)
_INGREDIENTS = re.compile(
    r"^[ \t]*ingredients?[ \t]*:?[ \t]*(?P<value>.*?)[ \t]*$",
    re.IGNORECASE,
)
_INGREDIENT_STOP = re.compile(
    r"^[ \t]*(?:contains|may[ \t]+contain|allergen(?:s)?"
    r"(?:[ \t]+(?:information|advice|declaration))?|"
    r"nutrition[ \t]+facts|warning|storage|"
    r"fssai\b|fssai[ \t]+lic|"
    r"per[ \t]*100[ \t]*(?:g|ml)|"
    r"(?:(?:total|added|saturated|trans)[ \t]+)?"
    r"(?:fat|sugars?|sodium|protein|energy|calories?|"
    r"carbohydrates?|carbs?|dietary[ \t]+fib(?:er|re)|salt)"
    r"(?:[ \t]*\([ \t]*(?:g|mg|kcal|kj)[ \t]*\))?"
    r"(?:[ \t]*[:\-][ \t]*|[ \t]+\d))",
    re.IGNORECASE,
)
_CONTAINS_DECLARATION = re.compile(
    r"^[ \t]*(?:contains(?:[ \t]+allergens?)?|"
    r"allergens?(?:[ \t]+(?:information|advice|declaration))?)"
    r"[ \t]*[:\-][ \t]*(?P<value>.*)$",
    re.IGNORECASE,
)
_MAY_CONTAIN_DECLARATION = re.compile(
    r"^[ \t]*may[ \t]+contain"
    r"(?:[ \t]+traces?[ \t]+of)?[ \t]*:?[ \t]*(?P<value>.*)$",
    re.IGNORECASE,
)
_FSSAI_LICENSE = re.compile(
    r"^[ \t]*FSSAI[ \t]+"
    r"(?:(?:license|licence|lic\.?|registration|reg(?:n|istration)?|cert(?:ificate)?|"
    r"no\.?|number)[ \t]*"
    r"(?:(?:no\.?|number)[ \t]*)?|(?:no\.?|number)[ \t]*)"
    r"[:#\-]?[ \t]*(?P<number>[0-9OQILSBGZ](?:[ \t\-/]*[0-9OQILSBGZ]){13}\b)?[ \t]*$",
    re.IGNORECASE,
)
_FSSAI_NUMBER_ONLY = re.compile(
    r"^[ \t]*(?P<number>[0-9OQILSBGZ](?:[ \t\-/]*[0-9OQILSBGZ]){13})[ \t]*$",
    re.IGNORECASE,
)
_FSSAI_CANDIDATE = re.compile(
    r"(?<!\d)(?:[0-9OQILSBGZ](?:[ \t\-/]*[0-9OQILSBGZ]){13})(?!\d)",
    re.IGNORECASE,
)
_INLINE_MAY_CONTAIN = re.compile(r"\bmay[ \t]+contain\b", re.IGNORECASE)


def _field(
    value,
    unit: str | None = None,
    source_text: str | None = None,
) -> dict:
    return {
        "value": value,
        "unit": unit,
        "source_text": source_text,
        "confidence": None,
        "needs_review": True,
    }


def _normalize_unit(unit: str | None) -> str | None:
    if unit is None:
        return None
    normalized = re.sub(r"[ \t.]", "", unit).casefold()
    return _UNIT_NORMALIZATION.get(normalized)


def _normalize_serving_size(value: str) -> str:
    return re.sub(
        r"(?<=\d)[ \t]*(?=(?:kg|g|grams?|mg|milligrams?|ml|"
        r"millilit(?:er|re)s?|l|lit(?:er|re)s?|oz|ounces?|"
        r"fl\.?\s*oz|cups?|tablespoons?|tbsp|teaspoons?|tsp|"
        r"pieces?|packs?)\b)",
        " ",
        value.strip(),
        flags=re.IGNORECASE,
    )


def _extract_serving_size(lines: list[str]) -> tuple[str | None, str | None, str | None]:
    matches = [
        (line, match)
        for line in lines
        if (match := _SERVING_SIZE.match(line)) is not None
        and (match.group("size").strip() or match.group("label_unit"))
    ]
    if len(matches) != 1:
        source_text = "\n".join(line for line, _ in matches) or None
        return None, None, source_text

    source_text, match = matches[0]
    value = _normalize_serving_size(match.group("size"))
    label_unit = _normalize_unit(match.group("label_unit"))
    if label_unit and value and not _SERVING_UNIT.search(value):
        value = f"{value} {label_unit}"
    unit_match = _SERVING_UNIT.search(value)
    unit = _normalize_unit(unit_match.group(1)) if unit_match else label_unit
    return value or None, unit, source_text


def _extract_basis(text: str) -> tuple[str | None, str | None]:
    matches = {
        basis: [
            line
            for line in text.splitlines()
            if pattern.search(line)
        ]
        for basis, pattern in _BASIS_PATTERNS.items()
    }
    found = [basis for basis, sources in matches.items() if sources]
    source_text = "\n".join(
        line
        for line in text.splitlines()
        if any(pattern.search(line) for pattern in _BASIS_PATTERNS.values())
    ) or None
    if len(found) != 1:
        return None, source_text
    return found[0], source_text


def _numeric_candidates(
    rest: str,
    label_unit: str | None,
    expected_unit: str,
    implied_unit: str | None = None,
) -> list[float]:
    candidates = []
    normalized_label_unit = _normalize_unit(label_unit)
    for match in _NUMERIC_TOKEN.finditer(rest):
        unit = (
            _normalize_unit(match.group("unit"))
            or normalized_label_unit
            or implied_unit
        )
        if unit == expected_unit:
            candidates.append(float(match.group("value").replace(",", "")))
    return candidates


def _parse_nutrient(field: str, text: str) -> dict:
    pattern = _NUTRIENT_PATTERNS[field]
    expected_unit = _NUTRIENT_DEFINITIONS[field][1]
    lines = text.splitlines()
    candidates: list[tuple[float, str]] = []
    source_lines: list[str] = []
    observed_units: list[str] = []
    ambiguous_value = False

    for index, line in enumerate(lines):
        match = pattern.match(line)
        if match is None:
            continue

        source_text = line
        rest = match.group("rest")
        if not rest.strip() and index + 1 < len(lines):
            rest = lines[index + 1].strip()
            source_text = f"{line}\n{lines[index + 1]}"

        label_unit = match.group("label_unit")
        normalized_label_unit = _normalize_unit(label_unit)
        label = match.group("label").casefold()
        implied_unit = (
            "kcal"
            if field == "energy_kcal" and label.startswith("calor")
            else None
        )
        if normalized_label_unit:
            observed_units.append(normalized_label_unit)
        if implied_unit:
            observed_units.append(implied_unit)
        values = _numeric_candidates(
            rest,
            label_unit,
            expected_unit,
            implied_unit,
        )
        if values:
            source_lines.append(source_text)
            if len(values) == 1:
                candidates.append((values[0], source_text))
            else:
                ambiguous_value = True
        else:
            source_lines.append(source_text)

    if len(candidates) == 1 and not ambiguous_value:
        value, source_text = candidates[0]
        return _field(value, expected_unit, source_text)

    source_text = "\n".join(source_lines) or None
    unit = (
        expected_unit
        if candidates
        else observed_units[0]
        if len(set(observed_units)) == 1 and observed_units
        else None
    )
    return _field(None, unit, source_text)


def _extract_labeled_value(
    pattern: re.Pattern[str],
    lines: list[str],
    group: str,
) -> tuple[str | None, str | None]:
    matches = [
        (line, match.group(group).strip())
        for line in lines
        if (match := pattern.match(line)) is not None
        and match.group(group).strip()
    ]
    if len(matches) != 1:
        return None, "\n".join(line for line, _ in matches) or None
    source_text, value = matches[0]
    return value, source_text


def _extract_ingredients(lines: list[str]) -> tuple[str | None, str | None]:
    starts = [
        (index, match.group("value").strip(), line)
        for index, line in enumerate(lines)
        if (match := _INGREDIENTS.match(line))
    ]
    if len(starts) != 1:
        return None, "\n".join(line for _, _, line in starts) or None

    start_index, first_line, source_line = starts[0]
    value_parts = [first_line] if first_line else []
    source_parts = [source_line]
    for line in lines[start_index + 1 :]:
        if _INGREDIENT_STOP.match(line):
            break
        if line.strip():
            value_parts.append(line.strip())
            source_parts.append(line)
    ingredients_text = " ".join(value_parts).strip()
    source_text = "\n".join(source_parts)
    return ingredients_text or None, source_text


def _split_ingredients(ingredients_text: str) -> list[str] | None:
    parts: list[str] = []
    delimiters: list[str] = []
    start = 0
    closing_for = {"(": ")", "[": "]"}
    opening_for = {closing: opening for opening, closing in closing_for.items()}

    for index, character in enumerate(ingredients_text):
        if character in closing_for:
            delimiters.append(closing_for[character])
        elif character in opening_for:
            if not delimiters or delimiters.pop() != character:
                return None
        elif character == "," and not delimiters:
            parts.append(ingredients_text[start:index].strip())
            start = index + 1

    if delimiters:
        return None
    parts.append(ingredients_text[start:].strip())
    if not parts or any(not part for part in parts):
        return None
    return parts


def split_ingredients_text(ingredients_text: str) -> list[str] | None:
    """Split a label ingredient list without splitting nested groups."""
    return _split_ingredients(ingredients_text)


def _split_declaration_items(value: str) -> list[str]:
    parts: list[str] = []
    delimiters: list[str] = []
    start = 0
    closing_for = {"(": ")", "[": "]"}
    opening_for = {closing: opening for opening, closing in closing_for.items()}

    for index, character in enumerate(value):
        if character in closing_for:
            delimiters.append(closing_for[character])
        elif character in opening_for:
            if not delimiters or delimiters.pop() != character:
                return [value.strip()] if value.strip() else []
        elif character in ",;" and not delimiters:
            part = value[start:index].strip()
            if part:
                parts.append(part)
            start = index + 1

    if delimiters:
        return [value.strip()] if value.strip() else []
    final_part = value[start:].strip()
    if final_part:
        parts.append(final_part)
    return parts


def _extract_allergen_declarations(
    lines: list[str],
) -> tuple[dict, dict]:
    allergens: list[str] = []
    allergen_sources: list[str] = []
    may_contain: list[str] = []
    may_contain_sources: list[str] = []

    for line in lines:
        may_match = _MAY_CONTAIN_DECLARATION.match(line)
        if may_match:
            may_contain.extend(_split_declaration_items(may_match.group("value")))
            may_contain_sources.append(line)
            continue

        contains_match = _CONTAINS_DECLARATION.match(line)
        if not contains_match:
            continue

        value = re.sub(
            r"^[ \t]*contains\b[ \t]*:?[ \t]*",
            "",
            contains_match.group("value"),
            flags=re.IGNORECASE,
        )
        may_inline = _INLINE_MAY_CONTAIN.search(value)
        if may_inline:
            allergen_value = value[: may_inline.start()].strip(" ;,")
            may_value = value[may_inline.end() :].strip(" :-")
            if may_value.casefold().startswith("traces of "):
                may_value = may_value[10:]
            if may_value:
                may_contain.extend(_split_declaration_items(may_value))
                may_contain_sources.append(line)
        else:
            allergen_value = value
        if allergen_value:
            allergens.extend(_split_declaration_items(allergen_value))
            allergen_sources.append(line)

    return (
        _field(allergens or None, source_text="\n".join(allergen_sources) or None),
        _field(
            may_contain or None,
            source_text="\n".join(may_contain_sources) or None,
        ),
    )


_OCR_FSSAI_DIGIT_MAP = {
    "O": "0",
    "Q": "0",
    "D": "0",
    "I": "1",
    "L": "1",
    "S": "5",
    "B": "8",
    "G": "6",
    "Z": "2",
    "T": "7",
}


def _normalize_fssai_number(value: str | None) -> str | None:
    if value is None:
        return None
    digits = []
    for character in value.strip():
        if character.isdigit():
            digits.append(character)
            continue
        if character.isalpha():
            digit = _OCR_FSSAI_DIGIT_MAP.get(character.upper())
            if digit is not None:
                digits.append(digit)
            continue
        if character in " -_/|.:\t":
            continue
        if character in ",;":
            continue
    normalized = "".join(digits)
    if len(normalized) != 14:
        return None
    return normalized


def _extract_fssai_license(lines: list[str]) -> dict:
    matches: list[tuple[str, str | None]] = []
    for index, line in enumerate(lines):
        match = _FSSAI_LICENSE.match(line)
        if match is not None:
            number = _normalize_fssai_number(match.group("number"))
            source_text = line
            if number is None and index + 1 < len(lines):
                number_match = _FSSAI_NUMBER_ONLY.match(lines[index + 1])
                if number_match:
                    number = _normalize_fssai_number(number_match.group("number"))
                    source_text = f"{line}\n{lines[index + 1]}"
            matches.append((source_text, number))
            continue

        if "fssai" in line.casefold():
            candidate = _FSSAI_CANDIDATE.search(line)
            if candidate is not None:
                number = _normalize_fssai_number(candidate.group(0))
                if number is not None:
                    matches.append((line, number))
                    continue
            if index + 1 < len(lines):
                candidate = _FSSAI_CANDIDATE.search(lines[index + 1])
                if candidate is not None:
                    number = _normalize_fssai_number(candidate.group(0))
                    if number is not None:
                        matches.append((f"{line}\n{lines[index + 1]}", number))

    if len(matches) != 1 or matches[0][1] is None:
        return _field(
            None,
            source_text="\n".join(line for line, _ in matches) or None,
        )
    source_text, number = matches[0]
    assert number is not None
    return _field(number, source_text=source_text)


def parse_label_text(ocr_text: str) -> dict:
    """Parse conservative, review-required fields from raw OCR text."""
    lines = ocr_text.splitlines()
    product_name, product_source = _extract_labeled_value(
        _PRODUCT_NAME,
        lines,
        "value",
    )
    serving_size_text, serving_size_unit, serving_size_source = (
        _extract_serving_size(lines)
    )
    basis, basis_source = _extract_basis(ocr_text)
    ingredients_text, ingredients_source = _extract_ingredients(lines)
    ingredients = (
        _split_ingredients(ingredients_text)
        if ingredients_text is not None
        else None
    )
    allergens, may_contain = _extract_allergen_declarations(lines)
    fssai_license_number = _extract_fssai_license(lines)

    nutrients = {
        field: _parse_nutrient(field, ocr_text)
        for field in _NUTRIENT_DEFINITIONS
    }
    extracted_fields = {
        "product_name": _field(product_name, source_text=product_source),
        "basis": _field(basis, source_text=basis_source),
        "serving_size_text": _field(
            serving_size_text,
            unit=serving_size_unit,
            source_text=serving_size_source,
        ),
        "ingredients_text": _field(
            ingredients_text,
            source_text=ingredients_source,
        ),
        "ingredients": _field(ingredients, source_text=ingredients_source),
        "allergens": allergens,
        "may_contain": may_contain,
        "fssai_license_number": fssai_license_number,
        "nutrients": nutrients,
    }
    review_required_fields = [
        "product_name",
        "basis",
        "serving_size_text",
        *nutrients,
        "ingredients",
        "allergens",
        "may_contain",
        "fssai_license_number",
    ]

    return {
        "product_name": extracted_fields["product_name"],
        "basis": basis,
        "serving_size_text": serving_size_text,
        "nutrients": nutrients,
        "ingredients_text": ingredients_text,
        "ingredients": ingredients,
        "allergens": allergens,
        "may_contain": may_contain,
        "fssai_license_number": fssai_license_number,
        "extracted_fields": extracted_fields,
        "review_required_fields": review_required_fields,
        "ocr_text": ocr_text,
    }

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

from app.models import ExtractedFields, FieldResult, FieldStatus, SubmissionStatus


FIELD_LABELS = {
    "brand": "Brand Name",
    "classType": "Class/Type Designation",
    "abv": "Alcohol Content",
    "netContents": "Net Contents",
    "warning": "Government Warning Statement",
}


VOLUME_UNITS_ML = {
    "ml": Decimal("1"),
    "milliliter": Decimal("1"),
    "milliliters": Decimal("1"),
    "l": Decimal("1000"),
    "liter": Decimal("1000"),
    "liters": Decimal("1000"),
    "cl": Decimal("10"),
    "centiliter": Decimal("10"),
    "centiliters": Decimal("10"),
    "floz": Decimal("29.5735295625"),
    "fl oz": Decimal("29.5735295625"),
    "fluidounce": Decimal("29.5735295625"),
    "fluidounces": Decimal("29.5735295625"),
}


def normalize(value: str) -> str:
    return (
        (value or "")
        .lower()
        .replace("'", "")
        .replace('"', "")
        .replace(".", "")
        .replace(",", "")
    )


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", normalize(value)).strip()


def _decimal_from_match(match: re.Match[str]) -> Decimal | None:
    try:
        return Decimal(match.group(1))
    except (InvalidOperation, IndexError):
        return None


def parse_abv(value: str) -> Decimal | None:
    text = value or ""
    percent_match = re.search(r"(\d+(?:\.\d+)?)\s*%", text)
    if percent_match:
        return _decimal_from_match(percent_match)

    abv_match = re.search(
        r"(\d+(?:\.\d+)?)\s*(?:alc\s*/?\s*vol|abv|alcohol\s+by\s+volume)",
        text,
        flags=re.IGNORECASE,
    )
    if abv_match:
        return _decimal_from_match(abv_match)

    proof_match = re.search(r"(\d+(?:\.\d+)?)\s*proof", text, flags=re.IGNORECASE)
    if proof_match:
        proof = _decimal_from_match(proof_match)
        return proof / Decimal("2") if proof is not None else None

    return None


def parse_net_contents(value: str) -> Decimal | None:
    compact = (value or "").lower().replace(",", "")
    compact = re.sub(r"\s+", " ", compact).strip()
    compact = compact.replace("fluid ounces", "fluidounces")
    compact = compact.replace("fluid ounce", "fluidounce")
    compact = compact.replace("fl. oz", "floz").replace("fl oz", "floz")
    match = re.search(
        r"(\d+(?:\.\d+)?)\s*(ml|milliliters?|l|liters?|cl|centiliters?|floz|fluidounces?)\b",
        compact,
    )
    if not match:
        return None
    try:
        amount = Decimal(match.group(1))
        unit = match.group(2)
        return amount * VOLUME_UNITS_ML[unit]
    except (InvalidOperation, KeyError):
        return None


def _numbers_equal(left: Decimal, right: Decimal, tolerance: Decimal) -> bool:
    return abs(left - right) <= tolerance


def evaluate_field(key: str, app_val: str, scan_val: str) -> FieldStatus:
    return explain_field(key, app_val, scan_val)[0]


def explain_field(key: str, app_val: str, scan_val: str) -> tuple[FieldStatus, str]:
    app_trimmed = (app_val or "").strip()
    scan_trimmed = (scan_val or "").strip()

    missing_reason = _missing_reason(app_trimmed, scan_trimmed)
    if missing_reason:
        return "mismatch", missing_reason

    if key == "warning":
        if app_trimmed == scan_trimmed:
            return "match", "Exact match."
        return "mismatch", _text_difference_reason(app_trimmed, scan_trimmed, strict_case=True)

    if key == "brand" or key == "classType":
        if app_trimmed == scan_trimmed:
            return "match", "Exact match."
        return "mismatch", _text_difference_reason(app_trimmed, scan_trimmed, strict_case=True)

    if key == "abv":
        app_abv = parse_abv(app_trimmed)
        scan_abv = parse_abv(scan_trimmed)
        if app_abv is not None and scan_abv is not None:
            if _numbers_equal(app_abv, scan_abv, Decimal("0.05")):
                return "match", f"Equivalent alcohol content ({app_abv}% vs {scan_abv}%)."
            return "mismatch", f"Numeric alcohol content differs ({app_abv}% vs {scan_abv}%)."
        if app_abv is None or scan_abv is None:
            return _fallback_text_result(app_trimmed, scan_trimmed)

    if key == "netContents":
        app_net = parse_net_contents(app_trimmed)
        scan_net = parse_net_contents(scan_trimmed)
        if app_net is not None and scan_net is not None:
            if _numbers_equal(app_net, scan_net, Decimal("1")):
                return "match", f"Equivalent net contents ({app_net.normalize()} mL vs {scan_net.normalize()} mL)."
            return "mismatch", f"Numeric net contents differ ({app_net.normalize()} mL vs {scan_net.normalize()} mL)."
        if app_net is None or scan_net is None:
            return _fallback_text_result(app_trimmed, scan_trimmed)

    return _fallback_text_result(app_trimmed, scan_trimmed)


def _missing_reason(app_val: str, scan_val: str) -> str:
    if not app_val and not scan_val:
        return "Both values are missing."
    if not app_val:
        return "Application form value is missing."
    if not scan_val:
        return "Label image value is missing."
    return ""


def _fallback_text_result(app_val: str, scan_val: str) -> tuple[FieldStatus, str]:
    if normalize_text(app_val) == normalize_text(scan_val):
        return "match", "Equivalent after text normalization."
    return "mismatch", _text_difference_reason(app_val, scan_val, strict_case=False)


def _text_difference_reason(app_val: str, scan_val: str, *, strict_case: bool) -> str:
    if app_val.casefold() == scan_val.casefold():
        return "Case differs; this field is case-sensitive." if strict_case else "Case differs."

    if _collapse_spaces(app_val) == _collapse_spaces(scan_val):
        return "Spacing or line breaks differ."

    if _strip_punctuation(app_val).casefold() == _strip_punctuation(scan_val).casefold():
        return "Punctuation or special characters differ."

    if normalize_text(app_val) == normalize_text(scan_val):
        return "Case, punctuation, or spacing differs."

    return f"Wording or characters differ near: {_first_difference(app_val, scan_val)}"


def _collapse_spaces(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _strip_punctuation(value: str) -> str:
    return re.sub(r"[^\w\s]", "", _collapse_spaces(value), flags=re.UNICODE)


def _first_difference(left: str, right: str) -> str:
    max_index = min(len(left), len(right))
    index = 0
    while index < max_index and left[index] == right[index]:
        index += 1

    start = max(index - 18, 0)
    left_piece = left[start : index + 28] or "(end)"
    right_piece = right[start : index + 28] or "(end)"
    return f'application "{left_piece}" vs label "{right_piece}"'

def _field_reason(key: str, app_val: str, scan_val: str) -> tuple[FieldStatus, str]:
    return explain_field(key, app_val, scan_val)


def compare_fields(
    application: ExtractedFields, label: ExtractedFields
) -> tuple[list[FieldResult], SubmissionStatus]:
    results: list[FieldResult] = []
    for key, label_text in FIELD_LABELS.items():
        app_val = getattr(application, key)
        scan_val = getattr(label, key)
        status, reason = _field_reason(key, app_val, scan_val)
        results.append(
            FieldResult(
                key=key,
                label=label_text,
                appVal=app_val,
                scanVal=scan_val,
                status=status,
                reason=reason,
            )
        )

    overall: SubmissionStatus = (
        "needs_correction" if any(result.status == "mismatch" for result in results) else "approved"
    )
    return results, overall


def extraction_complete(fields: ExtractedFields) -> bool:
    return all(
        [
            fields.brand.strip(),
            fields.classType.strip(),
            fields.abv.strip(),
            fields.netContents.strip(),
            fields.warning.strip(),
        ]
    )

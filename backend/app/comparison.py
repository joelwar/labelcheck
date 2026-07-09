from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

from app.models import ExtractedFields, FieldResult, Status


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


def evaluate_field(key: str, app_val: str, scan_val: str) -> Status:
    app_trimmed = (app_val or "").trim() if hasattr(app_val, "trim") else (app_val or "").strip()
    scan_trimmed = (scan_val or "").trim() if hasattr(scan_val, "trim") else (scan_val or "").strip()

    if key == "warning":
        return "match" if app_trimmed == scan_trimmed else "fail"

    if key == "abv":
        app_abv = parse_abv(app_trimmed)
        scan_abv = parse_abv(scan_trimmed)
        if app_abv is not None and scan_abv is not None:
            return "match" if _numbers_equal(app_abv, scan_abv, Decimal("0.05")) else "fail"

    if key == "netContents":
        app_net = parse_net_contents(app_trimmed)
        scan_net = parse_net_contents(scan_trimmed)
        if app_net is not None and scan_net is not None:
            return "match" if _numbers_equal(app_net, scan_net, Decimal("1")) else "fail"

    if app_trimmed == scan_trimmed:
        return "match"
    if normalize_text(app_trimmed) == normalize_text(scan_trimmed):
        return "review"
    return "fail"


def compare_fields(application: ExtractedFields, label: ExtractedFields) -> tuple[list[FieldResult], Status]:
    results: list[FieldResult] = []
    for key, label_text in FIELD_LABELS.items():
        app_val = getattr(application, key)
        scan_val = getattr(label, key)
        results.append(
            FieldResult(
                key=key,
                label=label_text,
                appVal=app_val,
                scanVal=scan_val,
                status=evaluate_field(key, app_val, scan_val),
            )
        )

    if any(result.status == "fail" for result in results):
        overall: Status = "fail"
    elif any(result.status == "review" for result in results):
        overall = "review"
    else:
        overall = "match"
    return results, overall

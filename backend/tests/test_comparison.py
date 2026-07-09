from app.comparison import compare_fields, evaluate_field
from app.models import ExtractedFields


def test_warning_is_exact_and_case_sensitive() -> None:
    required = "GOVERNMENT WARNING: (1) According to the Surgeon General..."
    lower = "Government Warning: (1) According to the Surgeon General..."

    assert evaluate_field("warning", required, required) == "match"
    assert evaluate_field("warning", required, lower) == "fail"


def test_brand_fuzzy_match_needs_review() -> None:
    assert evaluate_field("brand", "Acme Reserve", "ACME, Reserve.") == "review"


def test_abv_numeric_match_ignores_common_formatting() -> None:
    assert evaluate_field("abv", "45% Alc./Vol. (90 Proof)", "45% ALC/VOL") == "match"
    assert evaluate_field("abv", "45% Alc./Vol.", "46% Alc./Vol.") == "fail"


def test_net_contents_normalizes_units() -> None:
    assert evaluate_field("netContents", "750 ml", "0.75 L") == "match"
    assert evaluate_field("netContents", "750 ml", "1 L") == "fail"


def test_overall_status_rollup() -> None:
    app = ExtractedFields(
        brand="Acme Reserve",
        classType="Whiskey",
        abv="45% Alc./Vol.",
        netContents="750 ml",
        warning="GOVERNMENT WARNING:",
    )
    label = ExtractedFields(
        brand="ACME, Reserve.",
        classType="Whiskey",
        abv="45% ALC/VOL",
        netContents="750 ml",
        warning="GOVERNMENT WARNING:",
    )

    _, overall = compare_fields(app, label)

    assert overall == "review"

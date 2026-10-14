from __future__ import annotations

import json

import pytest

from qty_ocr.evaluation import UnverifiedGroundTruthError, evaluate, levenshtein, load_ground_truth
from qty_ocr.postprocessing import decide, is_valid_quantity, make_candidate, normalize_text
from qty_ocr.schemas import BlankLabel, FieldResult, FieldStatus


def cand(variant, text, score, error=None):
    return make_candidate(variant, text, score, 1.0, "PP-OCRv5_server_rec",
                          min_digits=1, max_digits=3, error=error)


def dcand(variant, raw, digits, score, substituted=0):
    """Candidate carrying digit-constrained decoding."""
    return make_candidate(variant, raw, 0.5, 1.0, "PP-OCRv5_server_rec", min_digits=1, max_digits=3,
                          digit_text=digits, digit_score=score, digit_substituted=substituted)


def run(cands, **kw):
    params = dict(min_digits=1, max_digits=3, review_threshold=0.85,
                  primary_variant="tight_crop", contradiction_min_score=0.85)
    params.update(kw)
    return decide(cands, **params)


@pytest.mark.parametrize("text", ["0", "5", "15", "123", "007"])
def test_valid_quantities(text):
    assert is_valid_quantity(text, 1, 3)


@pytest.mark.parametrize("text", ["", "1234", "O", "l5", "1.5", "-3", "IS", "B8", None])
def test_invalid_quantities(text):
    assert not is_valid_quantity(text, 1, 3)


def test_no_lookalike_substitution():
    norm, _ = normalize_text("O")
    assert norm == "O" and not is_valid_quantity(norm, 1, 3)
    d = run([cand("tight_crop", "IS", 0.99)])
    assert d.status == FieldStatus.INVALID_TEXT and d.value is None


def test_leading_zero_kept():
    d = run([cand("tight_crop", "007", 0.99)])
    assert d.value == "007" and d.value_int == 7 and d.status == FieldStatus.OK


def test_real_zero_is_string_zero():
    d = run([cand("tight_crop", "0", 0.97)])
    assert d.value == "0" and d.status == FieldStatus.OK


def test_inner_whitespace_flagged():
    norm, notes = normalize_text(" 4 8 ")
    assert norm == "48" and notes == ["inner_whitespace_removed"]
    d = run([cand("tight_crop", "4 8", 0.99)])
    assert d.value == "48" and "inner_whitespace_removed" in d.review_reasons


def test_fullwidth_digits_normalised():
    assert normalize_text("１５")[0] == "15"


def test_primary_variant_wins_over_majority():
    d = run([cand("original", "8", 0.80), cand("grayscale", "8", 0.80), cand("tight_crop", "68", 0.99)])
    assert d.value == "68" and d.variant == "tight_crop" and d.status == FieldStatus.OK


def test_confident_contradiction_flags_review():
    d = run([cand("original", "8", 0.90), cand("tight_crop", "68", 0.99)])
    assert d.value == "68" and d.status == FieldStatus.NEEDS_REVIEW
    assert any(r.startswith("variant_disagreement") for r in d.review_reasons)


def test_primary_invalid_falls_back_with_flag():
    d = run([cand("original", "29", 0.60), cand("tight_crop", "2%", 0.64)])
    assert d.value == "29" and d.status == FieldStatus.NEEDS_REVIEW
    assert any(r.startswith("primary_variant_invalid") for r in d.review_reasons)


def test_low_confidence_flag():
    d = run([cand("tight_crop", "15", 0.60)])
    assert d.status == FieldStatus.NEEDS_REVIEW and any("low_confidence" in r for r in d.review_reasons)


def test_threshold_boundary():
    assert run([cand("tight_crop", "15", 0.85)]).status == FieldStatus.OK
    assert run([cand("tight_crop", "15", 0.8499)]).status == FieldStatus.NEEDS_REVIEW


def test_ink_groups_exceed_digits():
    d = run([cand("tight_crop", "4", 0.96)], ink_groups=2)
    assert d.status == FieldStatus.NEEDS_REVIEW
    assert "ink_groups_exceed_digits(2>1)" in d.review_reasons
    assert run([cand("tight_crop", "48", 0.96)], ink_groups=1).status == FieldStatus.OK


def test_empty_prediction_on_nonblank():
    d = run([cand("tight_crop", "", 0.0), cand("original", " ", 0.4)])
    assert d.status == FieldStatus.INVALID_TEXT
    assert d.review_reasons == ["empty_prediction_on_nonblank"]


def test_recognition_error():
    d = run([cand("tight_crop", None, None, error="RuntimeError: boom")])
    assert d.status == FieldStatus.RECOGNITION_ERROR and d.value is None


def test_uncertain_blank_always_review():
    d = run([cand("tight_crop", "15", 0.99)], blank_label=BlankLabel.UNCERTAIN)
    assert d.status == FieldStatus.NEEDS_REVIEW and "blank_detection_uncertain" in d.review_reasons


def test_field_result_serialises_to_json():
    f = FieldResult(row_id=7, field_type="qty", bbox_aligned=(1, 2, 3, 4), bbox_original=(1, 2, 3, 4),
                    is_blank=True, raw_text=None, normalized_text=None, value=None, value_int=None,
                    confidence=None, status=FieldStatus.BLANK, needs_review=False)
    payload = json.loads(json.dumps(f.to_dict()))
    assert payload["value"] is None and payload["status"] == "blank" and payload["bbox_original"] == [1, 2, 3, 4]


def test_levenshtein():
    assert levenshtein("123", "128") == 1 and levenshtein("", "12") == 2 and levenshtein("12", "12") == 0


def test_unverified_ground_truth_refused(tmp_path):
    p = tmp_path / "gt.json"
    p.write_text(json.dumps({"verified": False, "documents": {"d": {"1": "5"}}}))
    with pytest.raises(UnverifiedGroundTruthError):
        load_ground_truth(p)


def test_evaluate_exact_match_and_blank_confusion(tmp_path):
    gt = {"d": {1: "123", 2: None, 3: "5"}}
    pred = {"document_id": "d", "fields": [
        {"row_id": 1, "value": "128", "is_blank": False, "status": "ok"},
        {"row_id": 2, "value": None, "is_blank": True, "status": "blank"},
        {"row_id": 3, "value": None, "is_blank": True, "status": "blank"},
    ]}
    rep = evaluate([pred], gt).to_dict()
    assert rep["exact_match_accuracy"] == round(1 / 3, 4)
    assert rep["blank_confusion"] == {"tp_blank": 1, "fp_blank": 1, "fn_blank": 0, "tn_blank": 1}
    assert rep["cer_nonblank"] == round(2 / 4, 4)


def test_digit_text_used_for_decision_raw_kept():
    d = run([dcand("tight_crop", "BZ", "32", 0.9, substituted=2)])
    assert d.value == "32" and d.raw_text == "BZ"
    assert d.status == FieldStatus.NEEDS_REVIEW
    assert any(r.startswith("letters_mapped_to_digits") for r in d.review_reasons)


def test_tight_and_segments_agree_ok():
    d = run([dcand("tight_crop", "15", "15", 0.99), dcand("digit_segments", "|5", "15", 0.95)], ink_groups=2)
    assert d.value == "15" and d.status == FieldStatus.OK


def test_segments_fix_missing_digit_when_length_matches_ink_groups():
    d = run([dcand("tight_crop", "|", "1", 0.9), dcand("digit_segments", "||", "11", 0.9)], ink_groups=2)
    assert d.value == "11" and d.variant == "digit_segments"
    assert d.status == FieldStatus.NEEDS_REVIEW
    assert any(r.startswith("tight_vs_segments_disagree") for r in d.review_reasons)


def test_segments_overcount_keeps_primary():
    d = run([dcand("tight_crop", "14", "14", 0.98), dcand("digit_segments", "|d4", "114", 0.9)], ink_groups=2)
    assert d.value == "14" and d.status == FieldStatus.NEEDS_REVIEW


def test_same_length_disagreement_keeps_primary_and_flags():
    d = run([dcand("tight_crop", "23", "23", 0.95), dcand("digit_segments", "93", "93", 0.95)], ink_groups=2)
    assert d.value == "23" and d.status == FieldStatus.NEEDS_REVIEW


def test_merged_digit_recovered_and_flagged():
    c = dcand("tight_crop", "7", "7", 0.8)
    c.longer_text, c.longer_penalty = "79", 0.016
    d = run([c], ink_groups=1)
    assert d.value == "79" and d.status == FieldStatus.NEEDS_REVIEW
    assert any(r.startswith("possible_merged_digits(7->79") for r in d.review_reasons)


def test_merged_digit_not_used_when_penalty_large():
    c = dcand("tight_crop", "7", "7", 0.99)
    c.longer_text, c.longer_penalty = "17", 0.25
    d = run([c], ink_groups=1)
    assert d.value == "7" and d.status == FieldStatus.OK


def test_merged_digit_threshold_relaxed_by_ink_groups():
    c = dcand("tight_crop", "1", "1", 0.9)
    c.longer_text, c.longer_penalty = "11", 0.05
    assert run([c], ink_groups=1).value == "1"
    assert run([c], ink_groups=2).value == "11"

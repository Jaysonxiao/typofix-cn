from typofix_cn.correctors.confusions import ConfusionMatch
from typofix_cn.correctors.macbert_candidates import Candidate, MacBertCandidate
from typofix_cn.correctors.macbert_decisions import build_decisions


def _candidate(*, original_score: float, scores: tuple[float, ...]) -> MacBertCandidate:
    return MacBertCandidate(
        start=2,
        end=3,
        source="新",
        original_score=original_score,
        candidates=tuple(Candidate(text=text, score=score) for text, score in zip(("薪", "心"), scores, strict=True)),
    )


def test_selector_accepts_top_two_candidate_when_thresholds_are_met() -> None:
    decisions = build_decisions("今天新情", [], [_candidate(original_score=0.46, scores=(0.41, 0.39))])

    assert decisions[0].accepted is True
    assert decisions[0].suggestion == "薪"
    assert decisions[0].reason == "accepted"
    assert decisions[0].detection_score == 0.54


def test_selector_records_detection_and_correction_rejections() -> None:
    detection = build_decisions("今天新情", [], [_candidate(original_score=0.70, scores=(0.80, 0.1))])
    correction = build_decisions("今天新情", [], [_candidate(original_score=0.40, scores=(0.20, 0.1))])

    assert (detection[0].accepted, detection[0].reason) == (False, "detection_below_threshold")
    assert (correction[0].accepted, correction[0].reason) == (False, "correction_below_threshold")


def test_confusion_match_has_priority_and_blocks_overlapping_model_decision() -> None:
    confusion = ConfusionMatch(start=2, end=4, source="新资", target="薪资", line_number=3)
    model = _candidate(original_score=0.1, scores=(0.9, 0.2))
    model = MacBertCandidate(start=2, end=3, source="新", original_score=model.original_score, candidates=model.candidates)

    decisions = build_decisions("今天新资", [confusion], [model])

    assert len(decisions) == 1
    assert decisions[0].provider == "confusion"
    assert decisions[0].accepted is True

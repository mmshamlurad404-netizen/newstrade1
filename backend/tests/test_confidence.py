from app.services.signals.confidence import (
    compute_confidence,
    corroboration_score,
    conviction_strength,
    market_risk_factor,
    veto_reasons,
)


def test_confidence_increases_with_corroboration():
    base = compute_confidence(0.5, 0.5, 1, 0.5, "other")
    more = compute_confidence(0.5, 0.5, 4, 0.5, "other")
    assert more > base


def test_high_confidence_bucket_is_reachable():
    assert compute_confidence(1.0, 1.0, 4, 1.0, "hack") >= 85


def test_confidence_within_bounds():
    assert 0 <= compute_confidence(0, 0, 0, 0, "other") <= 100
    assert 0 <= compute_confidence(2, 2, 10, 2, "listing") <= 100


def test_corroboration_score_caps():
    assert corroboration_score(0) == 0.0
    assert corroboration_score(8) == 1.0


def test_conviction_strength_bounds():
    assert 0 <= conviction_strength(1.0, "hack") <= 1.0


def test_market_risk_factor_clamped():
    assert market_risk_factor(0, 0, 0, False) == 1.0
    assert market_risk_factor(10, 10, 1.0, True) == 0.3


def test_veto_reasons():
    reasons = veto_reasons(1.0, 0.5, False, True, -3.0, 3.0, 0.0, 8.0)
    assert "kill_switch" in reasons
    assert "spread" in reasons
    assert "insufficient_depth" in reasons
    assert "daily_loss_limit" in reasons

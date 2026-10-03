from app.services.analysis.filter import detect_fast_alert, relevance_score


def test_relevance_high_for_listing():
    assert relevance_score("Binance will list SOL on spot") >= 0.8


def test_relevance_low_for_offtopic():
    assert relevance_score("gm wagmi") < 0.3


def test_fast_alert_detects_listing():
    alert = detect_fast_alert("Binance will list WIF for spot trading")
    assert alert["event_type"] == "listing"
    assert alert["coin"] == "WIF"


def test_fast_alert_detects_delisting():
    alert = detect_fast_alert("We will delist XYZ token")
    assert alert["event_type"] == "delisting"
    assert alert["coin"] == "XYZ"


def test_fast_alert_ignores_non_event():
    assert detect_fast_alert("BTC is up today") is None

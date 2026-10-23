from types import SimpleNamespace
from app.services.scoring import score_hazard

def h(**kwargs):
    base = dict(severity=5, confidence=.9, admin_rating=None, admin_status="pending")
    base.update(kwargs)
    return SimpleNamespace(**base)

def test_admin_rating_controls_treatment():
    assert score_hazard(h(admin_rating=1))["treatment"] == "flagged"
    assert score_hazard(h(admin_rating=4))["treatment"] == "penalised"
    assert score_hazard(h(admin_rating=5))["treatment"] == "blocked"

def test_dismissed_hazard_ignored():
    assert score_hazard(h(admin_status="dismissed"))["treatment"] == "ignored"

def test_unrated_never_blocked():
    assert score_hazard(h(admin_rating=None, admin_status="confirmed"))["treatment"] == "penalised"

def test_unconfirmed_alert_does_not_change_route():
    assert score_hazard(h(admin_rating=None))["treatment"] == "flagged"

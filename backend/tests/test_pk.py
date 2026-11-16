import pytest

from app.pk import PKBattle


def make(duration=60):
    return PKBattle(anchor_a="lulu", anchor_b="jay", started_at=0.0, duration_s=duration)


def test_rejects_same_anchor():
    with pytest.raises(ValueError):
        PKBattle(anchor_a="lulu", anchor_b="lulu", started_at=0, duration_s=10)


def test_scores_and_winner():
    pk = make()
    assert pk.add_points("lulu", "a", 10, now=1)
    assert pk.add_points("jay", "b", 52, now=2)
    assert pk.add_points("lulu", "c", 5, now=3)
    assert pk.scores == {"lulu": 15, "jay": 52}
    assert pk.winner() == "jay"
    assert pk.loser() == "lulu"
    assert pk.mvp("lulu") == "a"


def test_tie_has_no_winner():
    pk = make()
    pk.add_points("lulu", "a", 10, now=1)
    pk.add_points("jay", "b", 10, now=1)
    assert pk.winner() is None
    assert pk.loser() is None


def test_ignores_outsiders_late_and_nonpositive_points():
    pk = make(duration=10)
    assert not pk.add_points("luna", "a", 10, now=1)  # not in this PK
    assert not pk.add_points("lulu", "a", 0, now=1)
    assert not pk.add_points("lulu", "a", 10, now=10)  # time is up
    assert pk.scores == {"lulu": 0, "jay": 0}


def test_remaining_counts_down():
    pk = make(duration=60)
    assert pk.remaining(0) == 60
    assert pk.remaining(45.2) == 15
    assert pk.remaining(100) == 0
    assert pk.is_over(60)

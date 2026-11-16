import pytest

from app.fans import InsufficientCoins


def test_first_visit_gets_starting_coins(fans):
    fan = fans.record_visit("Alice")
    assert fan.coins == 2000
    assert fan.visits == 1
    assert not fan.is_returning


def test_second_visit_is_returning_and_keeps_wallet(fans):
    fans.record_visit("Alice")
    fans.spend("Alice", "lulu", 100)
    fan = fans.record_visit("Alice")
    assert fan.visits == 2
    assert fan.is_returning
    assert fan.coins == 1900


def test_spend_tracks_support_and_leaderboard(fans):
    fans.record_visit("a")
    fans.record_visit("b")
    fans.spend("a", "lulu", 10)
    fans.spend("a", "jay", 520)
    fans.spend("b", "lulu", 52)
    assert fans.favorite_anchor("a") == "jay"
    assert fans.leaderboard() == [{"name": "a", "total": 530}, {"name": "b", "total": 52}]


def test_cannot_overspend(fans):
    fans.record_visit("a")
    with pytest.raises(InsufficientCoins):
        fans.spend("a", "lulu", 2001)
    assert fans.get("a").coins == 2000


def test_rejects_non_positive_amount(fans):
    fans.record_visit("a")
    with pytest.raises(ValueError):
        fans.spend("a", "lulu", 0)


def test_last_message_is_remembered(fans):
    fans.record_visit("a")
    fans.record_message("a", "Long day at work today")
    assert fans.get("a").last_message == "Long day at work today"

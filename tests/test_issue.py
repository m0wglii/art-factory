from art_factory.issue import parse_issue

BODY = """### Idee in einem Satz

Ein kleiner Roboter
angelt an einem Bergsee.

### Muster (optional)

1 Bewohner

### Spur (optional)

automatisch
"""


def test_vorlage_wird_zerlegt():
    assert parse_issue(BODY) == {
        "idee": "Ein kleiner Roboter angelt an einem Bergsee.",
        "muster": 1,
        "spur": None,
    }


def test_spur_wird_erkannt():
    assert parse_issue(BODY.replace("automatisch", "P privat"))["spur"] == "P"


def test_freitext_ohne_vorlage():
    assert parse_issue("Ein UFO über dem Hafen")["idee"] == "Ein UFO über dem Hafen"

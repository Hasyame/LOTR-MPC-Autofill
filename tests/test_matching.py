from lotrautofill.library.matching import best_match, normalize


def test_apostrophe_and_underscore_normalize_equal():
    assert normalize("Thror's Map") == normalize("Thror_s Map")


def test_trailing_punctuation_ignored():
    assert normalize("Roast 'Em or Boil 'Em!") == normalize("Roast _Em or Boil _Em")


def test_exact_match():
    cands = {normalize("Great Cave-troll"): "img1"}
    val, kind, score = best_match("Great Cave-troll", cands)
    assert (val, kind) == ("img1", "exact")


def test_fuzzy_match_typo():
    cands = {normalize("Hungry Troll"): "img"}
    val, kind, score = best_match("Hungry Trail", cands)
    assert val == "img"
    assert kind == "fuzzy"


def test_no_match():
    cands = {normalize("Gandalf"): "img"}
    val, kind, score = best_match("Balrog of Morgoth", cands)
    assert val is None
    assert kind == "none"

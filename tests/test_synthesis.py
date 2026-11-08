from src.agent.voice.synthesis import _truncate


def test_short_text_is_unchanged():
    assert _truncate("Hello there.", 50) == "Hello there."


def test_cuts_at_latest_boundary_even_if_it_is_not_a_period():
    # A "." early, but a "!" and "?" fit later; the latest one must win.
    text = "Hi. Great trip! Ready? " + "x" * 50
    assert _truncate(text, 25) == "Hi. Great trip! Ready?"


def test_exclamation_later_than_period():
    text = "One. Two three four! " + "y" * 50
    assert _truncate(text, 30) == "One. Two three four!"


def test_sentence_ending_exactly_at_max_chars_is_kept():
    sentence = "a" * 9 + "."  # 10 chars, terminator on last allowed index
    text = sentence + " " + "b" * 50
    assert _truncate(text, 10) == sentence


def test_no_boundary_hard_cuts():
    text = "z" * 100
    assert _truncate(text, 40) == "z" * 40

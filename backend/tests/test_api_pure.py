from api import compact_text, paper_title


def test_compact_text_short_string():
    assert compact_text("hello world") == "hello world"


def test_compact_text_whitespace():
    assert compact_text("  hello   world  ") == "hello world"


def test_compact_text_exactly_max():
    text = "a" * 280
    assert compact_text(text) == text


def test_compact_text_over_max():
    text = "a" * 300
    result = compact_text(text)
    assert result.endswith("...")
    assert len(result) <= 283  # 280 + "..."


def test_compact_text_trims_before_ellipsis():
    text = "word " * 100
    result = compact_text(text)
    assert result.endswith("...")
    assert not result.endswith(" ...")


def test_paper_title_with_title():
    class FakePaper:
        title = "My Paper"
        filename = "paper.pdf"

    assert paper_title(FakePaper()) == "My Paper"


def test_paper_title_without_title():
    class FakePaper:
        title = None
        filename = "paper.pdf"

    assert paper_title(FakePaper()) == "paper"


def test_paper_title_removes_extension():
    class FakePaper:
        title = None
        filename = "my_research.pdf"

    assert paper_title(FakePaper()) == "my_research"

from store.sizes import SHOE_CHART, has_shoe_sizes


def test_has_shoe_sizes():
    assert has_shoe_sizes(["38 · 8 US", "39 · 8,5 US"])
    assert has_shoe_sizes(["8 US"])  # размеры поставщика
    assert not has_shoe_sizes(["S", "M", "122", ""])


def test_shoe_chart_is_ordered_and_complete():
    sizes = [row.ru for row in SHOE_CHART]
    assert sizes == list(range(35, 47))
    # У каждой строки есть хотя бы одна шкала US.
    assert all(row.women or row.men for row in SHOE_CHART)

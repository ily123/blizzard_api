"""Some tests."""


def test_function(text: str = 'hey') -> int:
    """blah"""
    if text == 'bah':
        return 0
    return 1


abc = test_function('bah')
print(abc)

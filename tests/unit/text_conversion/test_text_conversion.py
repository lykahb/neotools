from hypothesis import given, example, settings
from hypothesis.strategies import text

from alphatools.text_file import import_text_to_neo, export_text_from_neo


def test_newlines():
    output = import_text_to_neo('a\nb\r\nc')
    assert output.startswith(b'a\rb\r\rc\xa7')


def test_breaks():
    # hard break
    output = import_text_to_neo('a' * 100)
    assert output.startswith(b'aaaaaaaaaaaaaaaaaaaaaaa\x8faaaaaa')
    # soft break
    output = import_text_to_neo('This is a very long sentence that will need a soft break inside.')
    assert output.startswith(b'This is a very long sentence that will\x81need a soft break inside.')


@given(text())
@example("\n\r\n\t")
@example('↵')  # Without escape handling, it may be interpreted as newline
@settings(max_examples=1000)
def test_import_export_idempotency(s):
    # This loses unsupported characters
    imported = import_text_to_neo(s)
    # Text that has already been converted
    exported = export_text_from_neo(imported)
    doubly_imported = import_text_to_neo(exported)
    doubly_exported = export_text_from_neo(doubly_imported)
    assert imported == doubly_imported
    assert exported == doubly_exported

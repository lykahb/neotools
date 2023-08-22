from hypothesis import given, example, settings
from hypothesis.strategies import text

from neotools.text_file import import_text_to_neo, export_text_from_neo, read_character_map_file, character_map_name_to_filepath

character_map = read_character_map_file(character_map_name_to_filepath('default'))

def test_newlines():
    output = import_text_to_neo('a\nb\r\nc', character_map)
    assert output.startswith(b'a\rb\r\rc\xa7')


def test_breaks():
    # hard break
    output = import_text_to_neo('a' * 100, character_map)
    assert output.startswith(b'aaaaaaaaaaaaaaaaaaaaaaa\x8faaaaaa')
    # soft break
    output = import_text_to_neo('This is a very long sentence that will need a soft break inside.', character_map)
    assert output.startswith(b'This is a very long sentence that will\x81need a soft break inside.')


@given(text())
@example("\n\r\n\t")
@example('↵')  # Without escape handling, it may be interpreted as newline
@settings(max_examples=1000)
def test_import_export_idempotency(s):
    # This loses unsupported characters
    imported = import_text_to_neo(s, character_map)
    # Text that has already been converted
    exported = export_text_from_neo(imported, character_map)
    doubly_imported = import_text_to_neo(exported, character_map)
    doubly_exported = export_text_from_neo(doubly_imported, character_map)
    assert imported == doubly_imported
    assert exported == doubly_exported

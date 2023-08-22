import logging
import importlib.resources

from neotools import constants

logger = logging.getLogger(__name__)

neo_untranslatable_character = 0


def export_text_from_neo(text, character_map):  # from device to host
    neo_to_unicode = character_map['neo_to_unicode']
    index = 0
    result = []
    while index < len(text):
        code = text[index]
        index = index + 1
        is_escaped = False
        if code in [0xa4, 0xa7]:
            continue  # unused codes
        elif code == 0x0d:
            code = 0x0a  # pass code through the character set translation
        elif code in [0x81, 0xa1]:
            # line-breaking space.  0xa1 is from older software versions
            code = 0x20  # line-breaking space
        elif code == 0x8d:
            code = 0x09  # line-breaking tab
        elif code == 0x8f:
            continue  # period break in a run of contiguous characters
        elif code == 0xa3:
            code = 0x09  # line-breaking tab (older software versions)
        elif code == 0xad:
            code = 0x2d  # line-breaking hyphen
        elif code == 0xb0:
            if len(text) - index < 2:
                logger.error('ASAlphaWordText: Unexpectedly truncated escape sequence')
            else:
                is_escaped = True
                code = text[index]  # get the interpreted code directly
                index = index + 1
                if text[index] == 0xb0:
                    index = index + 1  # skip over a following escape code (if present)
        elif 0xa1 <= code <= 0xbf:
            logger.error('ASAlphaWordText: possibly untrapped escape %s', code)
            continue
        skip_conversion = code in [0x09, 0x0a, 0x0d] and not is_escaped
        if skip_conversion:
            char = chr(code)
        else:
            char = neo_to_unicode[code]
        result.append(char)
    return ''.join(result)


def import_text_to_neo(text: str, character_map):
    """
    From host to Neo
    """
    unicode_to_neo = character_map['unicode_to_neo']
    softbreak_interval = 40
    hardbreak_interval = 24
    softbreak_count = 0
    hardbreak_count = 0
    last_break_opportunity = 0
    neo_buffer = []
    min_file_size = 256
    # TODO: should we handle BOM?
    for char in text:
        escape = False
        code = unicode_to_neo.get(char)
        if code is None:
            code = neo_untranslatable_character
        if code == 0x81:
            # Re-map the "not" alternate character (to not clash with line-break hint)
            code = 0xac
        if 0xa1 <= code <= 0xbf or code in [0x09, 0x0a, 0x0d]:
            escape = True
        if char == '\t':
            code = 0x09
        elif char in ['\r', '\n']:
            code = 0x0d

        is_break = not escape and code == 0x0d
        is_breakable = not escape and code in [0x2d, 0x20, 0x09]
        hardbreak_count = hardbreak_count + 1
        softbreak_count = softbreak_count + 1

        if is_break:
            # The current character is an implicit break.
            last_break_opportunity = 0
            softbreak_count = 0
            hardbreak_count = 0
        elif is_breakable:
            last_break_opportunity = len(neo_buffer)
            hardbreak_count = 0
        elif hardbreak_count >= hardbreak_interval:
            neo_buffer.append(0x8f)  # insert a hard-break character
            softbreak_count = 0
            hardbreak_count = 0
            last_break_opportunity = 0

        if escape:
            neo_buffer.extend([0xb0, code, 0xb0])
        else:
            neo_buffer.append(code)

        if softbreak_count >= softbreak_interval and last_break_opportunity:
            # Substitute breakable characters with their breaking equivalents
            last = neo_buffer[last_break_opportunity]
            if last == 0x2d:
                neo_buffer[last_break_opportunity] = 0xad
            elif last == 0x20:
                neo_buffer[last_break_opportunity] = 0x81
            elif last == 0x09:
                neo_buffer[last_break_opportunity] = 0x8d
            else:
                # mismatch between this code and the assignment of isBreakable
                raise RuntimeError('Failed to encode break character')
            softbreak_count = 0
            hardbreak_count = 0
            last_break_opportunity = 0

    if len(neo_buffer) < min_file_size:
        # pad with 'unused space' pad byte to to minimum file size
        neo_buffer.extend([0xa7] * (min_file_size - len(neo_buffer)))
    return bytes(neo_buffer)


def character_map_name_to_filepath(name):
    file_name = constants.CHARACTER_MAP_NAME_TO_RESOURCE_FILE_NAME.get(name or 'default')
    if file_name is None:
        raise RuntimeError(f'Character map {name} not found. Did you mean to pass a path to a character map instead?')
    return importlib.resources.files('neotools').joinpath('character_map', file_name)


def read_character_map_file(path):
    contents = ''
    with open(path, 'r') as f:
        contents = f.read()
    lines = contents.splitlines()

    if len(lines) != 256:
        raise RuntimeError('Character map file must contain 256 characters, one character per line. The file must end with newline.')
    inverse_map = {code: index for (index, code) in enumerate(lines)}
    return {
        'neo_to_unicode': lines,
        'unicode_to_neo': inverse_map
    }

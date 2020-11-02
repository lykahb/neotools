import logging

logger = logging.getLogger(__name__)


# ■δΔ∫Ńĳ❏⅔˙⇥↓↑⤓↵⤈⤉→⅓Ξαρ↕↩□√≤≥θ∞ΩβΣ !"#$%&\'()*+,-./0123456789:;<=>?@
# ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~←€¬
# ‚ƒ„…†‡ˆ‰Š‹ŒΦŽΠ‵‘’“”•–—˜™š›œπžŸ\xa0¡¢£¤¥¦§¨©ª«¬\xad®¯°±²³´µ¶·¸¹º»¼½
# ¾¿ÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞßàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ
NEO_TO_UNICODE = [
    0x25a0, 0x03b4, 0x0394, 0x222b, 0x0143, 0x0133, 0x274f, 0x2154,
    0x02d9, 0x21e5, 0x2193, 0x2191, 0x2913, 0x21b5, 0x2908, 0x2909,
    0x2192, 0x2153, 0x039e, 0x03b1, 0x03c1, 0x2195, 0x21a9, 0x25a1,
    0x221a, 0x2264, 0x2265, 0x03b8, 0x221e, 0x03a9, 0x03b2, 0x03a3,
    0x20, 0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27,
    0x28, 0x29, 0x2a, 0x2b, 0x2c, 0x2d, 0x2e, 0x2f,
    0x30, 0x31, 0x32, 0x33, 0x34, 0x35, 0x36, 0x37,
    0x38, 0x39, 0x3a, 0x3b, 0x3c, 0x3d, 0x3e, 0x3f,
    0x40, 0x41, 0x42, 0x43, 0x44, 0x45, 0x46, 0x47,
    0x48, 0x49, 0x4a, 0x4b, 0x4c, 0x4d, 0x4e, 0x4f,
    0x50, 0x51, 0x52, 0x53, 0x54, 0x55, 0x56, 0x57,
    0x58, 0x59, 0x5a, 0x5b, 0x5c, 0x5d, 0x5e, 0x5f,
    0x60, 0x61, 0x62, 0x63, 0x64, 0x65, 0x66, 0x67,
    0x68, 0x69, 0x6a, 0x6b, 0x6c, 0x6d, 0x6e, 0x6f,
    0x70, 0x71, 0x72, 0x73, 0x74, 0x75, 0x76, 0x77,
    0x78, 0x79, 0x7a, 0x7b, 0x7c, 0x7d, 0x7e, 0x2190,
    0x20ac, 0xac, 0x201a, 0x0192, 0x201e, 0x2026, 0x2020, 0x2021,
    0x02c6, 0x2030, 0x0160, 0x2039, 0x0152, 0x03a6, 0x017d, 0x03a0,
    0x2035, 0x2018, 0x2019, 0x201c, 0x201d, 0x2022, 0x2013, 0x2014,
    0x02dc, 0x2122, 0x0161, 0x203a, 0x0153, 0x03c0, 0x017e, 0x0178,
    0xa0, 0xa1, 0xa2, 0xa3, 0xa4, 0xa5, 0xa6, 0xa7,
    0xa8, 0xa9, 0xaa, 0xab, 0xac, 0xad, 0xae, 0xaf,
    0xb0, 0xb1, 0xb2, 0xb3, 0xb4, 0xb5, 0xb6, 0xb7,
    0xb8, 0xb9, 0xba, 0xbb, 0xbc, 0xbd, 0xbe, 0xbf,
    0xc0, 0xc1, 0xc2, 0xc3, 0xc4, 0xc5, 0xc6, 0xc7,
    0xc8, 0xc9, 0xca, 0xcb, 0xcc, 0xcd, 0xce, 0xcf,
    0xd0, 0xd1, 0xd2, 0xd3, 0xd4, 0xd5, 0xd6, 0xd7,
    0xd8, 0xd9, 0xda, 0xdb, 0xdc, 0xdd, 0xde, 0xdf,
    0xe0, 0xe1, 0xe2, 0xe3, 0xe4, 0xe5, 0xe6, 0xe7,
    0xe8, 0xe9, 0xea, 0xeb, 0xec, 0xed, 0xee, 0xef,
    0xf0, 0xf1, 0xf2, 0xf3, 0xf4, 0xf5, 0xf6, 0xf7,
    0xf8, 0xf9, 0xfa, 0xfb, 0xfc, 0xfd, 0xfe, 0xff]

UNICODE_TO_NEO = {code: index for (index, code) in enumerate(NEO_TO_UNICODE)}

neo_untranslatable_character = 0


def export_text_from_neo(text):  # from device to host
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
        if not skip_conversion:
            code = NEO_TO_UNICODE[code]
        result.append(chr(code))
    return ''.join(result)


def import_text_to_neo(text: str):
    """
    From host to Neo
    :param text:
    :return:
    """
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
        code = UNICODE_TO_NEO.get(ord(char))
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

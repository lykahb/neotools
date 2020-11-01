from typing import List


def string_from_buf(buf, offset, width):
    c_str = buf[offset:offset + width]
    null_index = c_str.find(0)
    substr = c_str if null_index == -1 else c_str[:null_index]
    return substr.decode()


def int_from_buf(buf, offset, width):
    return int.from_bytes(buf[offset:offset + width], byteorder='big', signed=False)


def string_to_buf(buf: List[int], offset, width, value: str):
    raw = value.encode('utf-8')
    if len(value) > width:
        raise ValueError('String is too long %s' % raw)
    for i in range(len(raw)):
        buf[offset + i] = raw[i]


def int_to_buf(buf, offset, width, value):
    raw = int.to_bytes(value, length=width, byteorder='big', signed=False)
    for i in range(len(raw)):
        buf[offset + i] = raw[i]


def calculate_data_checksum(buf):
    return sum(buf) & 0xFFFF


def data_from_buf(buf_format, buf):
    if buf_format['size'] is not None and buf_format['size'] != len(buf):
        raise AlphatoolsError(
            'Expected buffer of size %s, received %s' %
            (buf_format['size'], len(buf)))
    converters = {
        str: string_from_buf,
        int: int_from_buf
    }
    return {
        k: converters[typ](buf, offset, width)
        for k, (offset, width, typ) in buf_format['fields'].items()
    }


def data_to_buf(buf_format, buf, value):
    if buf_format['size'] is not None and buf_format['size'] != len(buf):
        raise AlphatoolsError(
            'Expected buffer of size %s, received %s' %
            (buf_format['size'], len(buf)))
    converters = {
        str: string_to_buf,
        int: int_to_buf
    }
    for k, (offset, width, typ) in buf_format['fields'].items():
        if k in value:
            converters[typ](buf, offset, width, value[k])


class AlphatoolsError(RuntimeError):
    pass

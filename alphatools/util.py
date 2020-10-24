def buf_to_string(buf, offset, width):
    c_str = buf[offset:offset + width]
    null_index = c_str.find(0)
    substr = c_str if null_index == -1 else c_str[0:null_index - 1]
    return substr.decode()


def buf_to_int(buf, offset, width):
    return int.from_bytes(buf[offset:offset + width], byteorder='big', signed=False)


def calculate_data_checksum(buf):
    return sum(buf) & 0xFFFF

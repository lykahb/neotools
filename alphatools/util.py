def buf_to_string(buf, offset, width):
    return buf[offset:offset + width].strip(b'\0').decode()


def buf_to_int(buf, offset, width):
    return int.from_bytes(buf[offset:offset + width], byteorder='big', signed=False)

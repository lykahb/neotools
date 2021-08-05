import logging

from neotools.applet.constants import *
from neotools.message import Message, MessageConst, send_message
from neotools.util import calculate_data_checksum, NeotoolsError, data_from_buf

logger = logging.getLogger(__name__)


class Applet:
    @staticmethod
    def from_raw_header(buf):
        applet = data_from_buf(APPLET_HEADER_FORMAT, buf)
        if applet['signature'] != SIGNATURE_START:
            raise NeotoolsError('Invalid applet signature %s', applet['signature'])

        return applet


def read_applet_list(device):
    applets = []
    logger.info('Retrieving list of applets')
    device.dialogue_start()
    header_size = APPLET_HEADER_FORMAT['size']
    while True:
        buf = raw_read_applet_headers(device, len(applets))
        header_count = int(len(buf) / header_size)
        for index in range(0, header_count):
            applet_raw = buf[index * header_size:(index + 1) * header_size]
            applet = Applet.from_raw_header(applet_raw)
            applets.append(applet)
        if header_count < LIST_APPLETS_REQUEST_COUNT:
            break
    device.dialogue_end()
    return applets


# returns a list of installed applets
def raw_read_applet_headers(device, index):
    header_size = APPLET_HEADER_FORMAT['size']
    logger.info('Requesting to read list of applets with index=%s', index)
    message = Message(MessageConst.REQUEST_LIST_APPLETS, [
        (index, 1, 4), (LIST_APPLETS_REQUEST_COUNT, 5, 2)])
    response = send_message(device, message)
    size = response.argument(1, 4)
    expected_checksum = response.argument(5, 2)
    if size > LIST_APPLETS_REQUEST_COUNT * header_size:
        raise NeotoolsError('rawReadAppletHeaders: reply will return too much data!')

    if size == 0:
        return []

    buf = device.read(size, timeout=(size * 10 + 600))
    if len(buf) % header_size != 0:
        logger.warning(
            'rawReadAppletHeaders: read returned a partial header (expected header size %s, bytes read %s',
            header_size, len(buf))
    if calculate_data_checksum(buf) != expected_checksum:
        raise NeotoolsError('rawReadAppletHeaders: data checksum error')
    return buf


def get_applet_resource_usage(device, applet_id):
    device.dialogue_start()
    message = Message(MessageConst.REQUEST_GET_USED_SPACE, [(0x00000001, 1, 4), (applet_id, 5, 2)])
    response = send_message(device, message, MessageConst.RESPONSE_GET_USED_SPACE)
    result = {
        'ram': response.argument(1, 4),
        'file_count': response.argument(5, 2)
    }
    device.dialogue_end()
    return result

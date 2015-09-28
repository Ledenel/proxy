import re
from urllib.parse import urlparse
from exceptions import AcgxProxyClientParseError, AcgxProxyClientImplementError

IMPLEMENTED_METHODS = (b'OPTIONS', b'HEAD', b'GET', b'POST', b'PUT', b'DELETE', b'TRACE')
RE_REQUEST = re.compile(rb'^(\w+) (.+) HTTP/(.+)\r\n', re.IGNORECASE)
RE_CONTENT_LENGTH = re.compile(rb'\r\nContent-Length: (\d+)\r\n', re.IGNORECASE)
RE_TRANSFER_ENCODING = re.compile(rb'\r\nTransfer-Encoding: chunked\r\n', re.IGNORECASE)
RE_CONNECTION = re.compile(rb'\r\n(Proxy-)?Connection: (.+)\r\n', re.IGNORECASE)


def parse_request_headers(headers):
    request_meta = {'method': None,
                    'scheme': None,
                    'hostname': None,
                    'port': None,
                    'content_length': 0,
                    'chunked': False,
                    'modified_headers': b''}

    # Get HTTP method
    m = RE_REQUEST.search(headers)
    if m:
        method = m.group(1).upper()
        if method in IMPLEMENTED_METHODS:
            request_meta['method'] = method.decode()
        else:
            raise AcgxProxyClientImplementError('Method %s not implement' % method)
        url = m.group(2)
    else:
        raise AcgxProxyClientParseError('Invalid request header: no HTTP method')

    # Parse URL
    u = urlparse(url)
    if not u.scheme:
        raise AcgxProxyClientParseError('Invalid request header: no scheme')
    if u.scheme not in (b'http', b'https'):
        raise AcgxProxyClientImplementError('Scheme %s not implement' % u.scheme)
    request_meta['scheme'] = u.scheme.decode()

    if not u.hostname:
        raise AcgxProxyClientParseError('Invalid request header: no hostname')
    request_meta['hostname'] = u.hostname.decode()

    if u.port:
        request_meta['port'] = u.port
    else:
        request_meta['port'] = 80 if u.scheme == b'http' else 443

    # Get content length
    m = RE_CONTENT_LENGTH.search(headers)
    if m:
        request_meta['content_length'] = int(m.group(1))

    # Get transfer-encoding
    request_meta['chunked'] = True if RE_TRANSFER_ENCODING.search(headers) else False

    # Remove connection parameter
    request_meta['modified_headers'] = RE_CONNECTION.sub(b'\r\n', headers)

    return request_meta


def parse_response_headers(headers):
    response_meta = {'content_length': 0, 'chunked': False, 'modified_headers': b''}

    # Get content length
    m = RE_CONTENT_LENGTH.search(headers)
    if m:
        response_meta['content_length'] = int(m.group(1))

    # Get transfer-encoding
    response_meta['chunked'] = True if RE_TRANSFER_ENCODING.search(headers) else False

    # Force to close connection
    response_meta['modified_headers'] = RE_CONNECTION.sub(b'\r\nConnection: close\r\n', headers)

    return response_meta

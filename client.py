import asyncio
import logging
from utils.parser import parse_request_headers, parse_response_headers


class AcgxProxyClient:
    NEED_BODY_METHODS = ('POST', 'PUT')

    def __init__(self, ip='127.0.0.1', port=8888, buffer_size=4096):
        self._address = (ip, port)
        self._buffer_size = buffer_size
        self._loop = asyncio.get_event_loop()
        self._coroutine = asyncio.start_server(self.handle_request, self._address[0], self._address[1], loop=self._loop)
        self._server = self._loop.run_until_complete(self._coroutine)

    @asyncio.coroutine
    def handle_request(self, reader, writer):

        # Parse request header
        data = b''
        headers = b''
        body = b''
        request_meta = None
        while True:
            data += yield from reader.read(self._buffer_size)
            crlf = data.find(b'\r\n\r\n')
            if crlf >= 0:
                headers = data[:crlf+4]
                body = data[crlf+4:]
                request_meta = parse_request_headers(headers)
                break

        # Establish remote connection and write request headers
        remote_reader, remote_writer = yield from asyncio.open_connection(host=request_meta['hostname'],
                                                                          port=request_meta['port'], loop=self._loop)
        remote_writer.write(request_meta['modified_headers'])
        logging.info(request_meta['modified_headers'].decode())

        # Write request body to remote connection
        if request_meta['method'] in self.NEED_BODY_METHODS:
            while True:
                if request_meta['chunked']:
                    if body.endswith(b'\r\n0\r\n\r\n'):
                        break
                    body += yield from reader.read(self._buffer_size)
                else:
                    if len(body) >= request_meta['content_length']:
                        body = body[:request_meta['content_length']]
                        break
                    body += yield from reader.read(self._buffer_size)
            remote_writer.write(body)
        logging.info(len(body))
        yield from remote_writer.drain()

        # Read response headers
        data = b''
        headers = b''
        body = b''
        response_meta = None
        while True:
            data += yield from remote_reader.read(self._buffer_size)
            crlf = data.find(b'\r\n\r\n')
            if crlf >= 0:
                headers += data[:crlf+4]
                body = data[crlf+4:]
                response_meta = parse_response_headers(headers)
                break
        writer.write(response_meta['modified_headers'])
        logging.info(response_meta['modified_headers'].decode())

        # Read response body
        while True:
            if response_meta['chunked']:
                if body.endswith(b'\r\n0\r\n\r\n'):
                    break
                body += yield from remote_reader.read(self._buffer_size)
            else:
                if len(body) >= response_meta['content_length']:
                    body = body[:response_meta['content_length']]
                    break
                body += yield from remote_reader.read(self._buffer_size)
        writer.write(body)
        logging.info(len(body))
        yield from writer.drain()

        remote_writer.close()
        writer.close()

    def run(self):
        try:
            self._loop.run_forever()
        except KeyboardInterrupt:
            pass
        self._server.close()
        self._loop.run_until_complete(self._server.wait_closed())
        self._loop.close()

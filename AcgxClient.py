import logging
from client import AcgxProxyClient

logging.basicConfig(level=logging.DEBUG)
p = AcgxProxyClient()
p.run()

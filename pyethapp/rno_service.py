# https://github.com/ethereum/go-ethereum/wiki/Blockpool
import time
from ethereum.utils import privtoaddr, sha3
from devp2p.crypto import privtopub, ECCx, encrypt
from rlp.utils import encode_hex
from ethereum.slogging import get_logger
from devp2p.service import BaseService
import eth_protocol
import gevent
log = get_logger('rno')


class RNOService(BaseService):

    # required by BaseService
    name = 'rno'
    default_config = dict(eth=dict(privkey_hex=''))

    # RNO address, where the requests for random number should be addressed to.
    address = None

    def __init__(self, app):
        self.config = app.config
        super(RNOService, self).__init__(app)
        log.info('Initializing rno')
        address = privtoaddr(self.config['eth']['privkey_hex'].decode('hex'))

    # Process the transaction queue. The queue should be synchronized with add_transaction 
    # to avoid concurrency problems.
    def loop_body(self): 
        log.debug("rno body", address=address)

    # Transactions should be added to a queue and loop_body should process that queue
    # This method will be called only with transactions addressed to rno address.
    def add_transaction(tx):
        log.debug("rno received transaction", transaction=transaction)

    # This method is the core of the RNO. Transactions should NOT be processed in the 
    # add_transaction otherwise it would block the caller.
    def process_transaction(tx):
        log.debug("process tx", tx=tx)

    # Sends the reply back to Requester and Reveal Host
    def send_replies(number, requester_address, reveal_host_address, publish_at, publish_on):
        log.debug("rno reply", number=number, requester_address=requester_address, publish_at=publish_at, publish_on=publish_on)

    # Generates the public address (IPFS?) that will be used by the Reveal Host
    def generate_public_address(number):
        address = 'some public address'
        log.debug("rno pub address", address=address)
        return address


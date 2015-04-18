# https://github.com/ethereum/go-ethereum/wiki/Blockpool
import os

from ethereum.utils import privtoaddr, sha3
from devp2p.crypto import privtopub, ECCx, encrypt
from ethereum.slogging import get_logger
from devp2p.service import BaseService

import Queue
from gevent.event import Event
from devp2p.crypto import ECCx, recover, _encode_sig
from ethereum import transactions, processblock

log = get_logger('rno')


class RNOService(BaseService):

    # required by BaseService
    name = 'rno'
    default_config = dict(eth=dict(privkey_hex=''))

    # RNO address, where the requests for random number should be addressed to.
    my_address = None

    # Keeps all transactions not yet processed by loop_body
    transaction_queue = None

    # Will be used to a) sign transaction and b) cncrypt random number using ECIES
    eccx = None

    def __init__(self, app):
        log.info('Initializing rno')
        self.config = app.config
        self.interrupt = Event()
        super(RNOService, self).__init__(app)
        my_address = privtoaddr(self.config['eth']['privkey_hex'].decode('hex'))
        transaction_queue = Queue.Queue()  # thread safe
        eccx = ECCx(None, self.config['eth']['privkey_hex'].decode('hex'))

    # Process the transaction queue. There is no concurrency problem here since
    # the Queue is thread-safe.
    def loop_body(self): 
        log.debug("rno body", my_address=my_address)
        while not transaction_queue.empty():
            tx = transaction_queue.get()
            target_address = tx.fields['to']
            if target_address.__dict__ == my_address.__dict__:
                process_transaction(tx)

    # Transactions should be added to a queue so that 'loop_body' process that queue
    # To minimize code dependency and coupling, this method will be called for ALL
    # transactions received. 
    # It is called in the loop of eth_service.py -> on_receive_transactions
    def add_transaction(self, tx):
        log.debug("rno received transaction", transaction=transaction)
        # All transactions are being queue here to minizize the blocking
        # of caller's thread. Transactions not addressed to rno are discarded 
        # in loop_body.
        transaction_queue.put(tx)

    # This method is the core of the RNO. Transactions should NOT be processed in the 
    # add_transaction otherwise it would block the caller.
    def process_transaction(self, tx):
        log.debug("process tx", tx=tx)

        # 1) find out sender's address
        sender_address = tx.fields['from']

        # 2) Extract sender's pubkey from the Electrum-style signature of the tx
        encoded_signature = _encode_sig(tx.fields['v'], tx.fields['r'], tx.field['s'])
        message = None  # TODO: find out how to build the data (message) where the signature is applied.
        sender_pubkey = recover(message, encoded_signature)

        # 3) generate the random number
        number = os.urandom(32)

        # 4) encrypt RN using sender's pubkey (eRN1)
        encrypted_number = eccx.encrypt(number, sender_pubkey)

        # 5) encrypt RN using reveal host's pubkey (eRN2) (???)
        # this is not specified yet

        # 6) create/send transaction back to tx sender

        # nonce = number of transactions already sent by that account
        chain = self.app.services.chain.chain
        current_block = chain.head
        nonce = block.get_nonce(my_address)

        # Took from buterin example: https://blog.ethereum.org/2014/04/10/pyethereum-and-serpent-programming-guide/
        gas_price = 10**12 

        # Took from buterin example: https://blog.ethereum.org/2014/04/10/pyethereum-and-serpent-programming-guide/
        start_gas = 10000
        to = sender_address
        value = 0  # It's just a message, don't need to send any value (TODO: confirm that info)

        # data is a json formatted message but has to be 'binary'
        data = 0  # TODO
        reply_tx = transactions.Transaction(nonce, gas_price, start_gas, to, value, data).sign(self.config['eth']['privkey_hex'].decode('hex'))
        processblock.apply_transaction(current_block, reply_tx)

        # 7) create/send transaction to revel host.
        # this is not specified yet

    # Sends the reply back to Requester and Reveal Host
    def send_replies(self, number, requester_address, reveal_host_address, publish_at, publish_on):
        log.debug("rno reply", number=number, requester_address=requester_address, publish_at=publish_at, publish_on=publish_on)

    # Generates the public address (IPFS?) that will be used by the Reveal Host
    def generate_public_address(self, number):
        address = 'some public address'
        log.debug("rno pub address", address=address)
        return address

    # This will make the loop_body be executed by RNOService thread.
    def wakeup(self):
        self.interrupt.set()

    # @override BaseService._run (Greenlet._run)
    def _run(self):
        while True:
            self.interrupt.wait()
            self.loop_body()
            self.interrupt.clear()

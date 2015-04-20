# https://github.com/ethereum/go-ethereum/wiki/Blockpool
import os
import json
from Queue import Queue
from time import time

from devp2p.crypto import privtopub, ECCx, encrypt, recover, _encode_sig
from devp2p.service import BaseService
from ethereum.transactions import Transaction
from ethereum.processblock import apply_transaction
from ethereum.utils import privtoaddr
from ethereum.slogging import get_logger
from gevent.event import Event

log = get_logger('rno')


class RNOService(BaseService):

    # required by BaseService
    name = 'rno'
    default_config = dict(eth=dict(privkey_hex=''))

    # RNO address, where the requests for random number should be addressed to.
    my_addr = None

    # Keeps all transactions not yet processed by loop_body
    tx_queue = None

    # Will be used to a) sign transaction and b) encrypt random number using ECIES
    eccx = None

    privkey_hex = None

    def __init__(self, app):
        super(RNOService, self).__init__(app)
        log.info('Initializing RNO')
        self.config = app.config
        self.interrupt = Event()
        self.tx_queue = Queue()  # thread safe
        self.privkey_hex = self.config['eth']['privkey_hex'].decode('hex')
        self.my_addr = privtoaddr(self.privkey_hex)
        self.eccx = ECCx(None, self.privkey_hex)

    # Process the transaction queue. There is no concurrency problem here since
    # the Queue is thread-safe.
    def loop_body(self):
        log.debug('RNO body', my_addr=self.my_addr)
        while not self.tx_queue.empty():
            tx = self.tx_queue.get()
            if tx.to == self.my_addr:
                self.process_tx(tx)

    # Transactions should be added to a queue so that 'loop_body' process that queue
    # To minimize code dependency and coupling, this method will be called for ALL
    # transactions received.
    # It is called in the loop of eth_service.py -> on_receive_transactions
    def add_transaction(self, tx):
        log.debug('RNO received transaction', tx=tx)
        # All transactions are being queued here to minimize the blocking
        # of caller's thread. Transactions not addressed to RNO are discarded
        # in loop_body.
        self.tx_queue.put(tx)

    # This method is the core of the RNO. Transactions should NOT be processed in the
    # add_transaction otherwise it would block the caller.
    def process_tx(self, tx):
        log.debug('process tx', tx=tx)

        # 2) Extract sender's pubkey from the Electrum-style signature of the tx
        sender_pubkey = self.sender_pubkey_from_tx(tx)
        enc_num = self.generate_encrypted_random_number(sender_pubkey)

        # 5) encrypt RN using reveal host's pubkey (eRN2) (???)
        # this is not specified yet

        # 6) create/send transaction back to tx sender
        self.deliver(enc_num, tx.sender)

        # 7) create/send transaction to reveal host.
        # this is not specified yet

    def sender_pubkey_from_tx(self, tx):
        encoded_signature = _encode_sig(tx.v, tx.r, tx.s)
        message = None  # TODO: find out how to build the data (message) where the signature is applied.
        return recover(message, encoded_signature)

    def generate_encrypted_random_number(self, pubkey):
        # 3) generate the random number
        number = os.urandom(64)

        # 4) encrypt RN using sender's pubkey (eRN1)
        return self.eccx.encrypt(number, pubkey)

    def deliver(self, enc_num, to):
        # nonce = number of transactions already sent by that account
        head = self.app.services.chain.chain.head
        nonce = head.get_nonce(self.my_addr)

        # Took from buterin example:
        # https://blog.ethereum.org/2014/04/10/pyethereum-and-serpent-programming-guide/
        gasprice = 10**12

        # Took from buterin example:
        # https://blog.ethereum.org/2014/04/10/pyethereum-and-serpent-programming-guide/
        startgas = 10000
        value = 0  # It's just a message, don't need to send any value (TODO: confirm that info)

        # data is a json formatted message but has to be 'binary'
        unix_now = int(round(time()))
        payload = {}
        payload['when'] = unix_now
        payload['number'] = enc_num
        payload['publish_on'] = unix_now + 86400  # in 24 hours
        payload['published_at'] = 'http://www.example.com/foo'
        data = json.dumps(payload)

        deliver_tx = Transaction(nonce, gasprice, startgas, to, value, data)
        signed_deliver_tx = deliver_tx.sign(self.privkey_hex)
        success, output = apply_transaction(head, signed_deliver_tx)

    # Sends the reply back to Requester and Reveal Host
    def send_replies(self, number, requester_addr, reveal_host_addr,
                     publish_at, publish_on):
        log.debug('RNO reply', number=number, requester_addr=requester_addr,
                  publish_at=publish_at, publish_on=publish_on)

    # Generates the public address (IPFS?) that will be used by the Reveal Host
    def generate_public_address(self, number):
        address = 'some public address'
        log.debug('RNO pub address', address=address)
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

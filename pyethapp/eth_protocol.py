from devp2p.protocol import BaseProtocol, SubProtocolError
from ethereum.transactions import Transaction
from ethereum.blocks import Block, BlockHeader
import rlp
import gevent
from ethereum import slogging
log = slogging.get_logger('protocol.eth')


class ETHProtocolError(SubProtocolError):
    pass


class ETHProtocol(BaseProtocol):

    """
    DEV Ethereum Wire Protocol
    https://github.com/ethereum/wiki/wiki/Ethereum-Wire-Protocol
    https://github.com/ethereum/go-ethereum/blob/develop/eth/protocol.go#L15
    """
    protocol_id = 1
    max_cmd_id = 15  # FIXME
    name = 'eth'
    version = 60
    network_id = 99107

    max_getblocks_count = 256
    max_getblockhashes_count = 2048

    def __init__(self, peer, service):
        # required by P2PProtocol
        self.config = peer.config
        BaseProtocol.__init__(self, peer, service)

    class status(BaseProtocol.command):

        """
        protocolVersion: The version of the Ethereum protocol this peer implements. 30 at present.
        networkID: The network version of Ethereum for this peer. 0 for the official testnet.
        totalDifficulty: Total Difficulty of the best chain. Integer, as found in block header.
        latestHash: The hash of the block with the highest validated total difficulty.
        GenesisHash: The hash of the Genesis block.
        """
        cmd_id = 0
        sent = False

        structure = [
            ('eth_version', rlp.sedes.big_endian_int),
            ('network_id', rlp.sedes.big_endian_int),
            ('chain_difficulty', rlp.sedes.big_endian_int),
            ('chain_head_hash', rlp.sedes.binary),
            ('genesis_hash', rlp.sedes.binary)]

        def create(self, proto, chain_difficulty, chain_head_hash, genesis_hash):
            self.sent = True
            return [proto.version, proto.network_id, chain_difficulty, chain_head_hash,
                    genesis_hash]

    class gettransactions(BaseProtocol.command):

        "unused"
        cmd_id = 1

    class transactions(BaseProtocol.command):

        """
        Specify (a) transaction(s) that the peer should make sure is included on its transaction
        queue. The items in the list (following the first item 0x12) are transactions in the
        format described in the main Ethereum specification. Nodes must not resend the same
        transaction to a peer in the same session. This packet must contain at least one (new)
        transaction.
        """
        cmd_id = 2
        structure = rlp.sedes.CountableList(Transaction)

        # todo: bloomfilter: so we don't send tx to the originating peer

        @classmethod
        def decode_payload(cls, rlp_data):
            # convert to dict
            txs = []
            for i, tx in enumerate(rlp.decode_lazy(rlp_data)):
                txs.append(Transaction.deserialize(tx))
                if not i % 10:
                    gevent.sleep(0.0001)
            return txs

    class getblockhashes(BaseProtocol.command):

        """
        Requests a BlockHashes message of at most maxBlocks entries, of block hashes from
        the blockchain, starting at the parent of block hash. Does not require the peer
        to give maxBlocks hashes - they could give somewhat fewer.
        """
        cmd_id = 3

        structure = [
            ('child_block_hash', rlp.sedes.binary),
            ('count', rlp.sedes.big_endian_int),
        ]

    class blockhashes(BaseProtocol.command):

        """
        Gives a series of hashes of blocks (each the child of the next). This implies that
        the blocks are ordered from youngest to oldest.
        """
        cmd_id = 4
        structure = rlp.sedes.CountableList(rlp.sedes.binary)

    class getblocks(BaseProtocol.command):

        """
        Requests a Blocks message detailing a number of blocks to be sent, each referred to
        by a hash. Note: Don't expect that the peer necessarily give you all these blocks
        in a single message - you might have to re-request them.
        """
        cmd_id = 5
        structure = rlp.sedes.CountableList(rlp.sedes.binary)

    class blocks(BaseProtocol.command):
        cmd_id = 6
        structure = rlp.sedes.CountableList(Block)

        @classmethod
        def encode_payload(cls, list_of_rlp):
            return rlp.encode([rlp.codec.RLPData(x) for x in list_of_rlp], infer_serializer=False)

        @classmethod
        def decode_payload(cls, rlp_data):
            # fn = 'blocks.fromthewire.hex.rlp'
            # open(fn, 'a').write(rlp_data.encode('hex') + '\n')
            # convert to dict
            blocks = []
            for block in rlp.decode_lazy(rlp_data):
                blocks.append(TransientBlock(block))
            return blocks

    class newblock(BaseProtocol.command):

        """
        NewBlock [+0x07, [blockHeader, transactionList, uncleList], totalDifficulty]
        Specify a single block that the peer should know about.
        The composite item in the list (following the message ID) is a block in
        the format described in the main Ethereum specification.
        """
        cmd_id = 7
        structure = [('block', Block), ('chain_difficulty', rlp.sedes.big_endian_int)]

        # todo: bloomfilter: so we don't send block to the originating peer

        @classmethod
        def decode_payload(cls, rlp_data):
            # convert to dict
            # print rlp_data.encode('hex')
            ll = rlp.decode_lazy(rlp_data)
            assert len(ll) == 2
            transient_block = TransientBlock(ll[0])
            difficulty = rlp.sedes.big_endian_int.deserialize(ll[1])
            data = [transient_block, difficulty]
            return dict((cls.structure[i][0], v) for i, v in enumerate(data))


class TransientBlock(rlp.Serializable):

    """A partially decoded, unvalidated block."""

    fields = [
        ('header', BlockHeader),
        ('transaction_list', rlp.sedes.CountableList(Transaction)),
        ('uncles', rlp.sedes.CountableList(BlockHeader))
    ]

    def __init__(self, block_data):
        self.header = BlockHeader.deserialize(block_data[0])
        self.transaction_list = rlp.sedes.CountableList(Transaction).deserialize(block_data[1])
        self.uncles = rlp.sedes.CountableList(BlockHeader).deserialize(block_data[2])

    def to_block(self, db, parent=None):
        """Convert the transient block to a :class:`ethereum.blocks.Block`"""
        return Block(self.header, self.transaction_list, self.uncles, db=db, parent=parent)

    # def serialize(self):
    # return rlp.encode([self.header.serialize(self.header),
    # self.transaction_list, self.uncles])

    @property
    def hex_hash(self):
        return self.header.hex_hash()

    def __repr__(self):
        return '<TransientBlock(#%d %s)>' % (self.header.number, self.header.hash.encode('hex')[:8])

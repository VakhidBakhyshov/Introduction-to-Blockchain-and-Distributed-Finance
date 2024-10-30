import logging
import json
import time
import threading
import pickle

from typing import List, Dict, Set, Optional
from hashlib import sha256
from copy import deepcopy

from pprint import pprint

# Configure the logging system
logging.basicConfig(
    filename='blockchain.log',       # Log file name
    level=logging.INFO,        # Default log level
    format='%(asctime)s | %(name)s | %(levelname)s | %(message)s'
)

# Create a logger
logger = logging.getLogger('blockchain')


class Transaction:
    """
    A class to represent a transaction in a blockchain.
    """
    def __init__(self,
                 sender_address: str, recipient_address: str,
                 value: float = 0, data: Optional[str] = '',
                ):
        """

        Args:
            sender_address (str): sender's address
            recipient_address (str): recipient's address
            value (float): value of the transaction
            data (str, optional): data of the transaction. Defaults to None.
        """
        self.sender_address = sender_address
        self.recipient_address = recipient_address
        self.value = value
        self.data: str = data

    def to_json(self) -> str:
        """
        Convert object to json string

        Returns:
            str: json string
        """
        return str(self.__dict__)

    def __str__(self) -> str:
        return self.to_json()
    
    def __repr__(self) -> str:
        return self.to_json()

    def __hash__(self) -> str:
        return hash(self.to_json())

    def __eq__(self, other) -> bool:
        return self.__hash__() == other.__hash__()


class Block:
    """
    A class to represent a block in a blockchain.
    """
    def __init__(self,
                 index: int, transactions: List[Transaction], author: str,
                 timestamp: float, previous_hash: str, nonce: int = 0
                ):
        """

        Args:
            index (int): index of the block
            transactions (List[Transaction]): list of transactions in the block
            timestamp (datetime): timestamp of the block
            previous_hash (str): hash of the previous block
            nonce (int, optional): Nonce. Defaults to 0.
        """
        self.index: int = index
        self.transactions: List[Transaction] = transactions
        self.author: str = author
        self.timestamp: float = timestamp
        self.previous_hash: str = previous_hash
        self.nonce: int = nonce

    def compute_hash(self) -> str:
        """
        A function that return the hash of the block contents.
        """
        block_string = json.dumps(str(self.to_json()), sort_keys=True)
        return sha256(block_string.encode()).hexdigest()

    def to_json(self):
        return str(self.__dict__)
    
    def __str__(self):
        return self.to_json()
    
    def __repr__(self):
        return self.to_json()


class BlockchainPeer:
    # difficulty of our PoW algorithm
    difficulty = 3

    def __init__(self, peer_name: str):
        self.peer_name: str = peer_name
        self.unconfirmed_transactions: List[Transaction] = [] # mempool
        self.chain: List[Block] = None
        self.__init_blockchain()

    def create_genesis_block(self) -> None:
        """
        A function to generate genesis block and appends it to
        the chain. The block has index 0, previous_hash as 0, and
        a valid hash.
        """
        genesis_block = Block(
            index=0, transactions=[],
            author='Satoshi', timestamp=0,
            nonce=0, previous_hash="0",
        )
        genesis_block.hash = self.proof_of_work(genesis_block)
        self.chain = []
        self.chain.append(genesis_block)
        logging.info(f"{self.peer_name} | Created genesis block {genesis_block.to_json()}")

    @property
    def last_block(self):
        return self.chain[-1]

    def __add_block(self, block: Block, proof: str):
        """
        A function that adds the block to the chain after verification.
        Verification includes:
        * Checking if the proof is valid.
        * The previous_hash referred in the block and the hash of latest block
          in the chain match.

        Args:
            block (Block): block to be added
            proof (str): proof of work result
        """
        logging.info(f"{self.peer_name} | Adding block {block.to_json()}")

        previous_hash = self.last_block.hash

        if previous_hash != block.previous_hash:
            logging.error(f"{self.peer_name} | Previous hash {previous_hash} != {block.previous_hash}")
            raise Exception("Invalid block")

        if not BlockchainPeer.is_valid_proof(block, proof):
            logging.error(f"{self.peer_name} | Invalid proof {proof}")
            raise Exception("Invalid proof")

        block.hash = proof
        self.chain.append(block)
        logging.info(f"{self.peer_name} | Added block {block}")

    @staticmethod
    def proof_of_work(block: Block) -> str:
        """
        Function that tries different values of nonce to get a hash
        that satisfies our difficulty criteria.

        Args:
            block (Block): block to be mined
        
        Returns:
            str: hash of the mined block
        """
        block.nonce = 0
        computed_hash = block.compute_hash()
        while not computed_hash.startswith('0' * BlockchainPeer.difficulty):
            block.nonce += 1
            computed_hash = block.compute_hash()
        return computed_hash

    def add_new_transaction(self, transaction: Transaction):
        self.unconfirmed_transactions.append(transaction)
        logging.info(f"{self.peer_name} | Added transaction {transaction.to_json()}")

    def __init_blockchain(self):
        logging.info(f"{self.peer_name} | Initializing blockchain")
        self.chain: List[Block] = []
        self.create_genesis_block()

    def _get_chain(self) -> Dict:
        """
        A function that returns the chain and its length.

        Returns:
            Dict: {
                'length': int - length of the chain,
                'chain': List[Block] - list of blocks in the chain
                'current_mainnet_peer_name': str - name of the current mainnet peer
                'peers': List[str] - list of peers names
            }
        """
        chain_data = []
        for block in self.chain:
            chain_data.append(block)

        return {
            "length": len(chain_data),
            "chain": chain_data,
        }

    def _announce(self):
        """
        A function to announce to the network once a block has been mined.
        In this case we will send data to all peers to update the blockchain by file.
        """
        with open('the_longest_chain.pickle', 'wb') as storage:
            pickle.dump(self.peer_name, storage)

    def mine(self):
        """
        This function serves as an interface to add the pending
        transactions to the blockchain by adding them to the block
        and figuring out Proof Of Work.
        """
        logging.info(f"{self.peer_name} | Start mining")

        if not self.unconfirmed_transactions:
            logging.info(f"{self.peer_name} | No transactions to mine")
            return

        last_block: Block = self.last_block
        new_block = Block(
            index=last_block.index + 1,
            transactions=self.unconfirmed_transactions,
            author=self.peer_name,
            timestamp=time.time(),
            previous_hash=last_block.hash,
            nonce=0,
        )
        proof = self.proof_of_work(new_block)
        self.__add_block(new_block, proof)
        self.unconfirmed_transactions = []
        self._announce()

    @classmethod
    def is_valid_proof(cls, block: Block, block_hash: str) -> bool:
        """
        Check if block_hash is valid hash of block and satisfies
        the difficulty criteria.

        Args:
            block (Block): block to be verified
            block_hash (str): hash of the block to be verified
        
        Returns:
            bool: True if block_hash is valid, False otherwise
        """
        return (block_hash.startswith('0' * BlockchainPeer.difficulty) and
                block_hash == block.compute_hash())

    @classmethod
    def check_chain_validity(cls, chain: List[Block]) -> bool:
        result = True
        previous_hash = "0"

        try:
            chain_copy = deepcopy(chain)
        except TypeError: # some attr is a couroutine
            return False

        for block in chain_copy:
            block_hash = block.hash
            # remove the hash field to recompute the hash again
            # using `compute_hash` method.
            delattr(block, "hash")

            if not cls.is_valid_proof(block, block_hash):
                logging.error(f"Invalid proof {block_hash} for block {block.index} | valid proof {block.compute_hash()}")
                result = False
                break

            if previous_hash != block.previous_hash:
                logging.error(f"Invalid previous hash {block.previous_hash} != {previous_hash}")
                result = False
                break

            block.hash, previous_hash = block_hash, block_hash

        return result


class BlockchainMainnet:

    def __init__(self, peers: List[BlockchainPeer]):
        self.peers: List[BlockchainPeer] = peers
        self.blockchain: BlockchainPeer = peers[0]
        self.blockchain._announce()
        self.the_longest_chain: Optional[BlockchainPeer] = None

    # Function to query unconfirmed transactions
    def get_pending_txs(self) -> List[str]:
        mempool: Set[Transaction] = []
        for peer in self.peers:
            mempool.extend(peer.unconfirmed_transactions)
        return [tr.to_json() for tr in mempool]

    def consensus(self):
        """
        Our naive consnsus algorithm. If a longer valid chain is
        found, our chain is replaced with it.
        """
        logging.info(f"Mainnet | Consensus started")
        longest_blockchain = self.the_longest_chain

        if not BlockchainPeer.check_chain_validity(longest_blockchain.chain):
            logging.error(f"Mainnet | Invalid longest chain {self.the_longest_chain.peer_name}")
            return
        else:
            self.blockchain = longest_blockchain
            logging.info(f"Mainnet | Consensus done with new chain {self.blockchain.peer_name} | Announcing new block {self.blockchain.last_block}")

    def __sync_peers(self):
        """
        A function to announce to the network once a block has been mined.
        Other blocks can simply verify the proof of work and add it to their
        respective chains.
        """
        for peer in self.peers:
            peer.chain = deepcopy(self.blockchain.chain)
        self.the_longest_chain = None

    def run_mining(self):
        """
        A function to simulate mining of new block by adding
        it to the blockchain and announcing to the network.
        Announcing to the network is done by consensus - the first peer
        that finishes mining will announce the new block to the network and all other sync with it.
        """
        tasks = []
        for peer in set(self.peers):
            tasks.append(threading.Thread(target=peer.mine, daemon=True, args=()))

        for task in set(tasks):
            task.start()

        while True and self.the_longest_chain is None:
            for task in set(tasks):
                if not task.is_alive(): # the first peer that finishes mining will announce the new block to the network
                    time.sleep(1)       # wait for the file to be written (announced)
                    with open('the_longest_chain.pickle', 'rb+') as storage:
                       new_peer = pickle.load(storage)
                       self.the_longest_chain = self.__find_peer_by_name(new_peer)
                    break

        for task in tasks:
            task.join()

        self.consensus()
        self.__sync_peers()

    def __find_peer_by_name(self, peer_name: str) -> BlockchainPeer:
        for peer in self.peers:
            if peer.peer_name == peer_name:
                return peer
        raise Exception(f"Peer {peer_name} not found")

    def get_chain(self):
        chain = self.blockchain._get_chain()
        chain.update({'current_mainnet_peer_name': self.blockchain.peer_name})
        chain.update({'peers': [peer.peer_name for peer in self.peers]})
        return chain

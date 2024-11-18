import threading
import time
import utils as utils
from config import cfg

# Constants for node states
FOLLOWER = 0
CANDIDATE = 1
LEADER = 2

# ANSI escape codes for colored output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

class Node:
    """
    Represents a single node in a distributed system implementing Raft consensus algorithm.
    """
    def __init__(self, fellow, my_ip):
        """
        Initialize a Node with its fellow nodes and IP address.
        """
        self.addr = my_ip  # Node's IP address
        self.fellow = fellow  # List of other nodes in the cluster
        self.lock = threading.Lock()  # Lock for handling staged data
        self.DB = {}  # Simulated database
        self.log = []  # Log entries for Raft
        self.staged = None  # Staged log entry
        self.term = 0  # Current term of the node
        self.status = FOLLOWER  # Initial state of the node
        self.voteCount = 0  # Count of votes received
        self.commitIdx = 0  # Index of the latest committed log entry
        self.timeout_thread = None  # Thread for handling timeout
        self.majority = len(self.fellow) // 2 + 1  # Majority needed for consensus
        self.leader = None  # Current leader's address
        self.init_timeout()  # Initialize election timeout
        print(f"{Colors.OKBLUE}[Node {self.addr}] Initialized as FOLLOWER.{Colors.ENDC}")

    def incrementVote(self):
        """
        Increment the vote count and check if the node has received a majority to become LEADER.
        """
        self.voteCount += 1
        print(f"{Colors.OKBLUE}[Node {self.addr}] Received vote. Total votes: {self.voteCount}/{self.majority} (Term {self.term}).{Colors.ENDC}")
        if self.voteCount >= self.majority:
            print(f"{Colors.OKGREEN}[Node {self.addr}] Elected as LEADER for Term {self.term}.{Colors.ENDC}")
            self.status = LEADER
            self.leader = self.addr
            self.startHeartBeat()

    def startElection(self):
        """
        Transition the node to CANDIDATE state and start a new election.
        Dynamically calculate the majority based on active nodes.
        """
        self.term += 1  # Increment term for the new election
        self.voteCount = 1  # Start with self-vote
        self.status = CANDIDATE
        self.leader = None
        self.majority = (len(self.fellow) + 1) // 2 + 1  # Calculate majority based on total nodes
        print(f"{Colors.WARNING}[Node {self.addr}] Starting election for Term {self.term}. Current Leader: None.{Colors.ENDC}")
        self.init_timeout()
        self.send_vote_req()


    def check_majority(self):
        """
        Check the majority dynamically based on reachable peers and update the majority threshold.
        """
        active_peers = [peer for peer in self.fellow if utils.send(peer, "heartbeat", {"term": self.term})]
        self.majority = (len(active_peers) + 1) // 2 + 1  # Include self in the majority calculation
        print(f"{Colors.OKBLUE}[Node {self.addr}] Updated majority: {self.majority} based on active peers ({len(active_peers) + 1} total active nodes).{Colors.ENDC}")

    def send_vote_req(self):
        """
        Request votes from fellow nodes for the current election term.
        Dynamically count votes only from responding peers.
        """
        print(f"{Colors.OKBLUE}[Node {self.addr}] Requesting votes from fellow nodes for Term {self.term}.{Colors.ENDC}")
        for voter in self.fellow:
            threading.Thread(target=self.ask_for_vote, args=(voter, self.term)).start()

    def ask_for_vote(self, voter, term):
        """
        Send a vote request to a specific node and handle its response.
        """
        message = {"term": term, "commitIdx": self.commitIdx, "staged": self.staged}
        route = "vote_req"
        while self.status == CANDIDATE and self.term == term:
            reply = utils.send(voter, route, message)
            if reply:
                choice = reply.json()["choice"]
                if choice and self.status == CANDIDATE:
                    print(f"{Colors.OKGREEN}[Node {self.addr}] Vote received from {voter} for Term {term}.{Colors.ENDC}")
                    self.incrementVote()
                elif not choice:
                    term = reply.json()["term"]
                    if term > self.term:
                        print(f"{Colors.FAIL}[Node {self.addr}] Detected higher Term {term} from {voter}. Stepping down to FOLLOWER.{Colors.ENDC}")
                        self.term = term
                        self.status = FOLLOWER
                break
            else:
                print(f"{Colors.FAIL}[Node {self.addr}] No response from {voter} for Term {term}.{Colors.ENDC}")


    def decide_vote(self, term, commitIdx, staged):
        """
        Decide whether to vote for a candidate based on its term and log state.
        """
        if self.term < term and self.commitIdx <= commitIdx and (staged or (self.staged == staged)):
            self.reset_timeout()
            self.term = term
            print(f"{Colors.OKGREEN}[Node {self.addr}] Voting for Term {term}.{Colors.ENDC}")
            return True, self.term
        else:
            print(f"{Colors.FAIL}[Node {self.addr}] Vote denied for Term {term}. Current Term: {self.term}.{Colors.ENDC}")
            return False, self.term

    def startHeartBeat(self):
        """
        Begin sending periodic heartbeat messages to maintain leadership.
        """
        print(f"{Colors.OKGREEN}[Node {self.addr}] Sending heartbeats as LEADER for Term {self.term}.{Colors.ENDC}")
        if self.staged:
            self.handle_put(self.staged)

        for each in self.fellow:
            t = threading.Thread(target=self.send_heartbeat, args=(each,))
            t.start()

    def send_heartbeat(self, follower):
        """
        Send a heartbeat message to a follower node and handle its response.
        """
        route = "heartbeat"
        message = {"term": self.term, "addr": self.addr}
        while self.status == LEADER:
            start = time.time()
            reply = utils.send(follower, route, message)
            if reply:
                print(f"{Colors.OKGREEN}[Node {self.addr}] Heartbeat acknowledged by {follower}.{Colors.ENDC}")
                self.heartbeat_reply_handler(reply.json()["term"], reply.json()["commitIdx"])
            else:
                print(f"{Colors.FAIL}[Node {self.addr}] No response from {follower} during heartbeat.{Colors.ENDC}")
            delta = time.time() - start
            time.sleep((cfg.HB_TIME - delta) / 1000)

    def heartbeat_reply_handler(self, term, commitIdx):
        """
        Handle the reply to a heartbeat and update node state if necessary.
        """
        if term > self.term:
            print(f"{Colors.FAIL}[Node {self.addr}] Higher Term {term} detected. Stepping down to FOLLOWER.{Colors.ENDC}")
            self.term = term
            self.status = FOLLOWER
            self.init_timeout()

    def reset_timeout(self):
        """
        Reset the election timeout with a new random value.
        """
        self.election_time = time.time() + utils.random_timeout()
        print(f"{Colors.OKBLUE}[Node {self.addr}] Timeout reset. Next timeout at {self.election_time}.{Colors.ENDC}")

    def heartbeat_follower(self, msg):
        """
        Handle a heartbeat message from the current leader.
        """
        term = msg["term"]
        if self.term <= term:
            self.leader = msg["addr"]
            self.reset_timeout()

            if self.status == CANDIDATE:
                print(f"{Colors.WARNING}[Node {self.addr}] Stepping down to FOLLOWER after receiving heartbeat from Leader {self.leader} (Term {term}).{Colors.ENDC}")
                self.status = FOLLOWER
            elif self.status == LEADER:
                print(f"{Colors.FAIL}[Node {self.addr}] Stepping down to FOLLOWER as higher Term {term} detected.{Colors.ENDC}")
                self.status = FOLLOWER
                self.init_timeout()

            if self.term < term:
                self.term = term

            if "action" in msg:
                action = msg["action"]
                if action == "log":
                    payload = msg["payload"]
                    self.staged = payload
                elif self.commitIdx <= msg["commitIdx"]:
                    if not self.staged:
                        self.staged = msg["payload"]
                    self.commit()

        return self.term, self.commitIdx

    def init_timeout(self):
        """
        Start or restart the timeout thread for handling elections.
        """
        self.reset_timeout()
        if self.timeout_thread and self.timeout_thread.is_alive():
            return
        self.timeout_thread = threading.Thread(target=self.timeout_loop)
        self.timeout_thread.start()

    def timeout_loop(self):
        """
        Wait for the timeout period and trigger a new election if necessary.
        """
        while self.status != LEADER:
            delta = self.election_time - time.time()
            if delta < 0:
                print(f"{Colors.WARNING}[Node {self.addr}] Timeout reached. Starting a new election for Term {self.term + 1}.{Colors.ENDC}")
                self.startElection()
            else:
                time.sleep(delta)

        if self.status == CANDIDATE and self.voteCount < self.majority:
            print(f"{Colors.FAIL}[Node {self.addr}] Election failed. Retrying...{Colors.ENDC}")
            self.startElection()

    def handle_get(self, payload):
        """
        Handle a GET request for a specific key in the database.
        """
        key = payload["key"]
        if key in self.DB:
            payload["value"] = self.DB[key]
            return payload
        else:
            return None

    def check_majority(self):
        """
        Check the majority based on active peers and update the majority threshold.
        """
        active_peers = [peer for peer in self.fellow if utils.send(peer, "heartbeat", {"term": self.term})]
        self.majority = ((len(active_peers) + 1) // 2) + 1
        print(f"{Colors.OKBLUE}[Node {self.addr}] Updated majority: {self.majority} based on active peers.{Colors.ENDC}")

    def spread_update(self, message, confirmations=None, lock=None):
        """
        Send a message to all fellow nodes and collect confirmations.
        """
        for i, each in enumerate(self.fellow):
            r = utils.send(each, "heartbeat", message)
            if r and confirmations:
                confirmations[i] = True
        if lock:
            lock.release()

    def handle_put(self, payload):
        """
        Handle a PUT request to stage, commit, and replicate a log entry.
        """
        print(f"{Colors.OKBLUE}[Node {self.addr}] Handling PUT request: {payload}{Colors.ENDC}")
        self.lock.acquire()
        self.staged = payload
        waited = 0
        log_message = {
            "term": self.term,
            "addr": self.addr,
            "payload": payload,
            "action": "log",
            "commitIdx": self.commitIdx
        }

        log_confirmations = [False] * len(self.fellow)
        threading.Thread(target=self.spread_update, args=(log_message, log_confirmations)).start()
        while sum(log_confirmations) + 1 < self.majority:
            waited += 0.0005
            time.sleep(0.0005)
            if waited > cfg.MAX_LOG_WAIT / 1000:
                print(f"{Colors.FAIL}[Node {self.addr}] Log update rejected after waiting {cfg.MAX_LOG_WAIT} ms.{Colors.ENDC}")
                self.lock.release()
                return False

        commit_message = {
            "term": self.term,
            "addr": self.addr,
            "payload": payload,
            "action": "commit",
            "commitIdx": self.commitIdx
        }
        self.commit()
        threading.Thread(target=self.spread_update, args=(commit_message, None, self.lock)).start()
        print(f"{Colors.OKGREEN}[Node {self.addr}] Log entry committed and replicated to majority.{Colors.ENDC}")
        return True

    def commit(self):
        """
        Commit a staged log entry to the log and update the database.
        """
        self.commitIdx += 1
        self.log.append(self.staged)
        key = self.staged["key"]
        value = self.staged["value"]
        self.DB[key] = value
        self.staged = None
        print(f"{Colors.OKGREEN}[Node {self.addr}] Committed log entry: {key} -> {value} (Term {self.term}).{Colors.ENDC}")

    def show_log(self):
        """
        Outputs the current log of the node in a readable format.
        """
        if self.log:
            print(f"{Colors.HEADER}[Node {self.addr}] Current Log:{Colors.ENDC}")
            for idx, entry in enumerate(self.log):
                print(f"  {Colors.OKBLUE}Log Index {idx}: {entry}{Colors.ENDC}")
        else:
            print(f"{Colors.WARNING}[Node {self.addr}] Log is empty.{Colors.ENDC}")

    def handle_delete(self, payload):
        """
        Handles a DELETE request to remove a key-value pair from the database.

        Args:
            payload (dict): Contains the key to be deleted.

        Returns:
            bool: True if the key was deleted successfully, False otherwise.
        """
        key = payload["key"]
        if key in self.DB:
            del self.DB[key]
            print(f"{Colors.OKGREEN}[Node {self.addr}] Deleted key: {key}.{Colors.ENDC}")
            return True
        else:
            print(f"{Colors.FAIL}[Node {self.addr}] Key not found: {key}.{Colors.ENDC}")
            return False
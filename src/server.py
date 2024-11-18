from node import Node
from node import FOLLOWER, LEADER
from flask import Flask, request, jsonify
import sys
import logging

app = Flask(__name__)

@app.route("/request", methods=['DELETE'])
def value_delete():
    """
    Handle DELETE requests to remove a key-value pair from the Raft cluster.

    If the node is a LEADER:
        - Process the request using the node's `handle_delete` method.
    If the node is a FOLLOWER:
        - Redirect the request to the current leader.

    Returns:
        JSON response indicating success or failure of the DELETE operation.
    """
    payload = request.json["payload"]
    reply = {"code": 'fail'}

    if n.status == LEADER:
        result = n.handle_delete(payload)
        if result:
            reply = {"code": "success"}
    elif n.status == FOLLOWER:
        # Redirect to the current leader
        payload["message"] = n.leader
        reply["payload"] = payload
    return jsonify(reply)


@app.route("/show_log", methods=['GET'])
def show_log():
    """
    Handle GET requests to output the current log of the node.
    
    Returns:
        JSON response containing the log of the node.
    """
    print(f"[Server {n.addr}] Showing current log.")
    return jsonify({"log": n.log})

@app.route("/request", methods=['GET'])
def value_get():
    """
    Handle GET requests to retrieve the value of a key in the Raft cluster.

    If the node is a LEADER:
        - Process the request using the node's `handle_get` method.
    If the node is a FOLLOWER:
        - Redirect the request to the current leader.

    Returns:
        JSON response containing the result of the GET operation or a redirection.
    """
    payload = request.json["payload"]
    reply = {"code": 'fail', 'payload': payload}
    if n.status == LEADER:
        result = n.handle_get(payload)
        if result:
            reply = {"code": "success", "payload": result}
    elif n.status == FOLLOWER:
        # Redirect to the current leader
        reply["payload"]["message"] = n.leader
    return jsonify(reply)

@app.route("/request", methods=['PUT'])
def value_put():
    """
    Handle PUT requests to store a key-value pair in the Raft cluster.

    If the node is a LEADER:
        - Process the request using the node's `handle_put` method.
    If the node is a FOLLOWER:
        - Redirect the request to the current leader.

    Returns:
        JSON response indicating success or failure of the PUT operation.
    """
    payload = request.json["payload"]
    reply = {"code": 'fail'}

    if n.status == LEADER:
        result = n.handle_put(payload)
        if result:
            reply = {"code": "success"}
    elif n.status == FOLLOWER:
        # Redirect to the current leader
        payload["message"] = n.leader
        reply["payload"] = payload
    return jsonify(reply)


@app.route("/leader_down", methods=['POST'])
def leader_down():
    """
    Handle POST requests indicating the leader is stepping down.

    Updates the node's status to FOLLOWER and initializes a timeout to start an election.

    Returns:
        JSON response indicating the status of the operation.
    """
    msg = request.json
    print(f"[Server {n.addr}] Leader {msg['addr']} is stepping down.")
    n.status = FOLLOWER
    n.init_timeout()
    return jsonify({"status": "ok"})


@app.route("/vote_req", methods=['POST'])
def vote_req():
    """
    Handle POST requests for vote requests in an election.

    Processes the vote request using the node's `decide_vote` method and responds
    with the vote decision and term.

    Returns:
        JSON response containing the vote decision and current term.
    """
    term = request.json["term"]
    commitIdx = request.json["commitIdx"]
    staged = request.json["staged"]
    choice, term = n.decide_vote(term, commitIdx, staged)
    message = {"choice": choice, "term": term}
    return jsonify(message)


@app.route("/heartbeat", methods=['POST'])
def heartbeat():
    """
    Handle POST requests for heartbeat messages from the leader.

    Updates the node's state based on the received heartbeat and responds
    with the current term and commit index.

    Returns:
        JSON response containing the term and commit index.
    """
    term, commitIdx = n.heartbeat_follower(request.json)
    message = {"term": term, "commitIdx": commitIdx}
    return jsonify(message)


# Disable Flask's default logging
log = logging.getLogger('werkzeug')
log.disabled = True

if __name__ == "__main__":
    """
    Main entry point for the server.

    Usage:
        python server.py <index> <ip_list_file>

    Args:
        index (int): Index of the current node in the IP list.
        ip_list_file (str): Path to a file containing the list of IPs in the cluster.

    Adds an endpoint for viewing the node's log.
    """
    if len(sys.argv) == 3:
        index = int(sys.argv[1])
        ip_list_file = sys.argv[2]
        ip_list = []

        # Read IP list from file
        with open(ip_list_file) as f:
            for ip in f:
                ip_list.append(ip.strip())

        # Extract the current node's IP and remove it from the list
        my_ip = ip_list.pop(index)
        http, host, port = my_ip.split(':')

        # Initialize the Node with the IP list and its own IP
        n = Node(ip_list, my_ip)

        # Start the Flask server
        print("Routes available:")
        print("- /request (GET/PUT/DELETE): Handle GET, PUT, and DELETE requests.")
        print("- /show_log (GET): Display the current log of the node.")
        print("- /leader_down (POST): Notify that the leader is stepping down.")
        print("- /vote_req (POST): Handle vote requests during elections.")
        print("- /heartbeat (POST): Handle heartbeat messages from the leader.")


        app.run(host="127.0.0.1", port=int(port), debug=False)
    else:
        # Print usage instructions
        print("usage: python server.py <index> <ip_list_file>")

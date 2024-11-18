import sys
import requests

def show_log(addr):
    """
    Sends a GET request to retrieve the log of the node.

    Args:
        addr (str): The address of the node to query.
    """
    server_address = addr + "/show_log"
    try:
        response = requests.get(server_address, timeout=1)
        if response.status_code == 200:
            print(f"Log of the node at {addr}:")
            log = response.json().get("log", [])
            if log:
                for idx, entry in enumerate(log):
                    print(f"  Log Index {idx}: {entry}")
            else:
                print("  Log is empty.")
        else:
            print(f"Failed to retrieve log from {addr}.")
    except requests.exceptions.RequestException as e:
        print(f"Error retrieving log from {addr}: {e}")


def redirect_to_leader(server_address, message):
    """
    Handles leader redirection in a Raft cluster.
    If the contacted node is not the leader, this function redirects to the leader
    based on the redirection information provided in the response.

    Args:
        server_address (str): The address of the current server.
        message (dict): The request message, including the type (GET/PUT) and payload.

    Returns:
        dict: The JSON response from the leader or an error message.
    """
    request_type = message["type"]
    while True:
        try:
            # Determine the type of request and send it to the server
            if request_type == "get":
                response = requests.get(server_address, json=message, timeout=1)
            else:  # PUT request
                response = requests.put(server_address, json=message, timeout=1)
        except Exception as e:
            print(f"Error communicating with {server_address}: {e}")
            return {"error": str(e)}

        # Check the response for redirection or successful handling
        if response.status_code == 200 and "payload" in response.json():
            payload = response.json()["payload"]
            if "message" in payload:  # Redirect to the leader
                server_address = payload["message"] + "/request"
                print(f"Redirecting to leader at {server_address}")
            else:  # Successfully handled by the current node
                break
        else:  # Unhandled error or unexpected response
            break

    return response.json()


def put(addr, key, value):
    """
    Sends a PUT request to store a key-value pair in the Raft cluster.

    Args:
        addr (str): The address of the initial server.
        key (str): The key to store.
        value (str): The value to associate with the key.
    """
    server_address = addr + "/request"
    payload = {'key': key, 'value': value}
    message = {"type": "put", "payload": payload}
    print("PUT request result:", redirect_to_leader(server_address, message))


def get(addr, key):
    """
    Sends a GET request to retrieve the value associated with a key in the Raft cluster.

    Args:
        addr (str): The address of the initial server.
        key (str): The key whose value needs to be retrieved.
    """
    server_address = addr + "/request"
    payload = {'key': key}
    message = {"type": "get", "payload": payload}
    print("GET request result:", redirect_to_leader(server_address, message))

def delete(addr, key):
    """
    Sends a DELETE request to remove a key-value pair in the Raft cluster.

    Args:
        addr (str): The address of the node.
        key (str): The key to be deleted.
    """
    server_address = addr + "/request"
    payload = {'key': key}
    message = {"type": "delete", "payload": payload}
    try:
        response = requests.delete(server_address, json=message, timeout=1)
        if response.status_code == 200:
            print(f"DELETE request result: {response.json()}")
        else:
            print(f"Failed to delete key {key} from {addr}.")
    except requests.exceptions.RequestException as e:
        print(f"Error deleting key {key} from {addr}: {e}")


if __name__ == "__main__":
    """
    Entry point for the client script.
    Supports both interactive and command-line modes for GET, PUT, and SHOW_LOG requests.

    Usage:
    - Interactive mode: python3 client.py address
    - GET request: python3 client.py address key
    - PUT request: python3 client.py address key value
    - SHOW_LOG: python3 client.py address show_log
    """
    if len(sys.argv) == 2:
        # Interactive mode
        addr = sys.argv[1]
        while True:
            command = input("Enter command (get <key> | put <key> <value> | delete <key> | show_log | exit): ").strip().split()
            if not command:
                continue
            if command[0].lower() == "exit":
                break
            elif command[0].lower() == "get" and len(command) == 2:
                get(addr, command[1])
            elif command[0].lower() == "put" and len(command) == 3:
                put(addr, command[1], command[2])
            elif command[0].lower() == "delete" and len(command) == 2:
                delete(addr, command[1])
            elif command[0].lower() == "show_log" and len(command) == 1:
                show_log(addr)
            else:
                print("Invalid command. Use 'get <key>', 'put <key> <value>', 'delete <key>', 'show_log', or 'exit'.")
    elif len(sys.argv) == 3:
        # Command-line mode: DELETE or GET request
        addr = sys.argv[1]
        if sys.argv[2].lower() == "show_log":
            show_log(addr)
        else:
            key = sys.argv[2]
            delete(addr, key)  # Assume DELETE if only 2 arguments (for simplicity)
    elif len(sys.argv) == 4:
        # Command-line mode: PUT request
        addr = sys.argv[1]
        key = sys.argv[2]
        value = sys.argv[3]
        put(addr, key, value)
    else:
        # Print usage instructions for invalid arguments
        print("Usage:")
        print("PUT usage: python3 client.py address 'key' 'value'")
        print("GET usage: python3 client.py address 'key'")
        print("DELETE usage: python3 client.py address 'key'")
        print("SHOW_LOG usage: python3 client.py address show_log")
        print("Format: address: http://ip:port")
        print("Interactive mode: python3 client.py address")

# Raft Consensus Algorithm Implementation

This project implements a simplistic version of the Raft consensus algorithm using Python and Flask to simulate a distributed system of nodes. It was based on [GlucoRAFT](https://github.com/nicehoplite/GlucoRAFT) but has many key differences. The system supports operations like adding key-value pairs, retrieving them, deleting them, and inspecting logs, all while ensuring consensus across nodes using raft's leader election and log replication.

[Click here to watch a quick Demo Video](https://www.loom.com/share/1444d240d76e4f54b42139157ee5888f?sid=ce3c1cc0-9512-4b63-b2a3-c8798def9f97)

## File Structure

```plaintext

RAFT/
├── src/
│   ├── client.py        # Client script to interact with the Raft cluster
│   ├── config.py        # Configuration file for timeout and other settings
│   ├── node.py          # Implementation of the Node class for Raft
│   ├── server.py        # Server script to start a Raft node
│   ├── servers.txt      # List of server addresses for the cluster
│   ├── utils.py         # Utility functions used across the project
│   └── __pycache__/     # Compiled Python files (ignored in version control)
├── .gitignore           # Specifies files and directories to ignore in Git
├── README.md            # Documentation for the project
├── requirements.txt     # Python dependencies for the project

```

## Setup Instructions

**Prerequisites**

- Python 3.8 or higher (I ran it on Python3 version 3.12.4)
- pip for installing Python packages
- virtualenv for creating a Python virtual environment (optional but recommended)

### Dependencies

Install the required Python libraries by running:

```bash
pip install -r requirements.txt
```

### Running the Nodes

To set up a Raft cluster, follow these steps:

1. **Prepare an IP List File:** Edit the servers.txt file to include the IP addresses and ports for all the nodes in the cluster. For example:

```plaintext
http://127.0.0.1:8000
http://127.0.0.1:8001
http://127.0.0.1:8002
```

2. **Start Each Node:** Run the following command for each node in the cluster, replacing <index> with the node's index in servers.txt (0-based index):

```bash
python3 src/server.py <index> src/servers.txt
```

Example for a 3-node cluster:

```bash
python3 src/server.py 0 src/servers.txt
python3 src/server.py 1 src/servers.txt
python3 src/server.py 2 src/servers.txt
```

### Client Operations

To interact with the Raft cluster, use the client script:

**Interactive Mode**

Run the client in interactive mode by specifying the address of one of the nodes:

```bash
python3 src/client.py http://127.0.0.1:8000
```

You can then use the following commands:

- **GET a Key:**

```bash
get <key>
```

Example

```bash
get name
```

- **PUT a Key-Value Pair:**

```bash
put <key> <value>
```

Example

```bash
put name Alice
```

- **DELETE a Key:**

```bash
delete <key>
```

Example

```bash
delete name
```

- **SHOW_LOG:** Display the log of the connected node.

```bash
show_log
```

- **EXIT:** Quit the client.

```bash
exit
```

## Shortcomings

1. **No Persistent Storage:** The implementation does not persist data. All logs and key-value pairs are stored in memory and will be lost when a node is restarted.

2. **Leader Election Limitations:** If the leader crashes, there may be a delay before a new leader is elected, impacting the availability of the cluster.

3. **No Dynamic Membership:** The system does not support adding or removing nodes dynamically during runtime. We need to specify the numbers of nodes in the servers.txt file before use.

4. **Limited Fault Tolerance:** While the Raft algorithm is designed to handle failures, this implementation assumes reliable communication between nodes and does not handle extensive network partitions. There is leader election and log replication mechanisms that handles consistency in case of leader or node failure but we cannot simualte network partitions in this implementation.

5. **No Log Compaction:**8 The implementation does not include a mechanism for log compaction, which is essential for reducing the size of logs over time. Without log compaction, logs can grow indefinitely, consuming more memory and potentially leading to performance degradation in long-running systems.

## AI Usage Statement

This project includes portions of the code and documentation that were generated, revised, and refined with the assistance of AI tools, specifically OpenAI's ChatGPT and Github copilot. All code and documentation have been reviewed and tested to ensure correctness and compliance with project requirements.

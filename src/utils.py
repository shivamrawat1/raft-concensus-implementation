import random
import requests
from config import cfg

def random_timeout():
    """
    Generate a random timeout value within a specified range defined in the config.

    Ensures that LOW_TIMEOUT is less than HIGH_TIMEOUT. If not, the values are swapped
    to correct the range.

    Returns:
        float: A random timeout value in seconds.
    """
    low, high = cfg.LOW_TIMEOUT, cfg.HIGH_TIMEOUT
    if low > high:
        print(f"Warning: Swapping LOW_TIMEOUT({low}) and HIGH_TIMEOUT({high}) to fix range.")
        low, high = high, low
    return random.randrange(low, high) / 1000


def send(addr, route, message):
    """
    Send a POST request to a specific route of a given address.

    Args:
        addr (str): The base address of the node (e.g., http://ip:port).
        route (str): The route to append to the base address (e.g., "heartbeat").
        message (dict): The JSON payload to include in the POST request.

    Returns:
        requests.Response or None: The response object if the request was successful, or None if the request failed.
    """
    url = addr + '/' + route
    try:
        reply = requests.post(url=url, json=message, timeout=cfg.REQUESTS_TIMEOUT / 1000)
        if reply.status_code == 200:
            return reply
    except requests.exceptions.RequestException:
        print(f"[Utils] Node at {addr} is unreachable.")
    return None

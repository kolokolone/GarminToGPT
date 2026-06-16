import socket


def is_port_open(host: str, port: int, timeout_seconds: float = 1.0) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout_seconds)
        return sock.connect_ex((host, port)) == 0

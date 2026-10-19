import socket
import subprocess
import time
from dataclasses import dataclass

import pytest

from test_mdb_workflows.run_minimdb import main as run_minimdb


@dataclass
class Neo4jConnection:
    bolt_uri: str
    user: str
    password: str


def _bolt_ready(host: str, port: int, timeout: float = 30.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=2):
                return True
        except OSError:
            time.sleep(1)
    return False


def _container_running(name: str) -> bool:
    result = subprocess.run(
        ["docker", "inspect", "-f", "{{.State.Running}}", name],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0 and result.stdout.strip() == "true"


@pytest.fixture(scope="session")
def mini_mdb():
    already_running = _container_running("mini-mdb")
    if already_running:
        print("mini-mdb container already running, reusing it")
    else:
        run_minimdb()
    if not _bolt_ready("localhost", 7687):
        raise RuntimeError("mini-mdb did not become ready in time")
    yield Neo4jConnection(
        bolt_uri="bolt://localhost:7687",
        user="neo4j",
        password="neo4j",
    )
    if not already_running:
        subprocess.run(
            ["docker", "rm", "-f", "mini-mdb"],
            capture_output=True,
        )


"""Launch the mini-mdb Neo4j 4.4 container."""

import subprocess
import sys
from pathlib import Path


def main():
    neo4j_dir = Path(__file__).resolve().parent.parent / "neodata"

    cmd = [
        "docker", "run",
        "--detach",
        "--env", "NEO4J_AUTH=none",
        "--name", "mini-mdb",
        "--publish", "7474:7474",
        "--publish", "7687:7687",
        "--tmpfs", "/tmp:rw,exec,size=512m",
        "--volume", f"{neo4j_dir / 'data'}:/data",
        "--volume", f"{neo4j_dir / 'import'}:/import",
        "--volume", f"{neo4j_dir / 'conf'}:/var/lib/neo4j/conf",
        "--volume", f"{neo4j_dir / 'plugins'}:/plugins",
        "neo4j:4.4",
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        sys.exit(result.returncode)
    print(f"Container 'mini-mdb' started: {result.stdout.strip()}")


if __name__ == "__main__":
    main()

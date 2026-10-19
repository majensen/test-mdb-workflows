"""Load test_model_changelog.xml into the mini-mdb Neo4j container."""

import sys
from pathlib import Path
from neo4j import GraphDatabase

from mdb_changelog_runner import ChangelogExecutor

BOLT_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "neo4j"

if len(sys.argv) > 1:
    CHANGELOG_PATH = sys.argv[1]
else:
    print("Arg 1 (changelog path) required")
    exit(1)

def main():
    driver = GraphDatabase.driver(BOLT_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    try:
        executor = ChangelogExecutor(driver)
        result = executor.execute(
            schema_mode=True,
            changelog_path=CHANGELOG_PATH,
            changelog_location="model-desc",
            changelog_scope="TEST",
        )
        print(f"Executed {result.changesets_executed} changeset(s)")
    finally:
        driver.close()


if __name__ == "__main__":
    main()

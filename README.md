# test-mdb-workflows

This is a fixture that enables tests of components of the bento-mdb update workflow. It sets up a neo4j container loaded with a simple model. Tests run bento-mdb scripts or modules with simple model updates. These most often create changelog files. Changelog files are executed on the minimal database using changelog-runner, and the resulting database is checked for the expected content.

# Usage

	cd test-mdb-workflows
	tar -xzf neodata.tar.gz
	uv pip install -e .
	# start the database
	uv run run_minimdb
	# load a changelog file
	uv run load_changelog <changelog.xml>
	# run tests
	uv run pytest
	
# Setup notes

The mini mdb container runs with the directories below neodata/ mounted as the Neo4j backing directories, so the database changes persist between uses of run_minimdb.

To set up a completely fresh mdb, run 

	load_changelog bento-mdb/data/output/misc_changelogs/mdb_setup_changelog.xml 
	
from the working directory before running other changelogs. (This adds indexes and triggers.)

import pytest
import subprocess
from pathlib import Path
from neo4j import GraphDatabase
from mdb_changelog_runner import ChangelogExecutor
from pdb import set_trace
from bento_mdf.mdf import MDF
from bento_mdb.clients import CADSRClient, NCItClient
from bento_mdb.model_cdes import (
    add_cde_pvs_to_model_cde_spec,
    add_ncit_synonyms_to_model_cde_spec,
    make_model_cde_spec
)
from bento_mdb.cde_cypher import convert_model_cdes_to_changelog

@pytest.fixture(scope="class", autouse=True)
def db_setup(request, mini_mdb):
    drv = GraphDatabase.driver(mini_mdb.bolt_uri,
                               auth=(mini_mdb.user, mini_mdb.password))

    res = drv.execute_query("match (a) detach delete a;")
    request.cls.drv = drv
    request.cls.exc = ChangelogExecutor(drv)

    yield
    drv.close()

class TestNoDuplicates:
    def test_setup(self):
        res = self.drv.execute_query("match (a) return count(a) as ct;")
        assert len(res.records) > 0
        assert res.records[0]["ct"] == 0

    def test_concepts_reused_by_later_model_versions(self, tmp_path):
        changelog_a = tmp_path / "a.xml"
        changelog_av2 = tmp_path / "av2.xml"
        subprocess.run([
            "make_model_changelog",
            "--model_handle", "TEST_A",
            "--mdf_files", "model-desc/test-model-a.yml",
            "--output_file_path", str(changelog_a),
            "-a", "operator",
            "-c", "t1"
            ], check=True)
        self.exc.execute(changelog_path=str(changelog_a),
                    changelog_location="local")
        ncpt = self.drv.execute_query(
            "match (c:concept) return count(c) as ct"
            ).records[0]["ct"]
        assert ncpt > 0
        # pull a new version of model (identical to v1) - numbers of concepts should not
        # change
        subprocess.run([
            "make_model_changelog",
            "--model_handle", "TEST_A",
            "--mdf_files", "model-desc/test-model-a-v2.yml",
            "--output_file_path", str(changelog_av2),
            "-a", "operator",
            "-c", "t2"
            ], check=True)
        self.exc.execute(changelog_path=str(changelog_av2),
                    changelog_location="local")
        nv2 = self.drv.execute_query(
            "match (a {version: '0.0.2'}) return count(a) as ct"
            ).records[0]["ct"]
        assert nv2 > 0
        res = self.drv.execute_query("match (c:concept) return count(c) as ct")
        assert res.records[0]["ct"] == ncpt
        self.drv.execute_query(
            "match (a {_commit:'t2'}) detach delete a"
            )
        
    def test_valuesets_reused_by_props_with_identical_pvs(self, tmp_path):
        changelog_b = tmp_path / "b.xml"
        vsct = self.drv.execute_query(
            "match (v:value_set) return count(v) as ct"
            ).records[0]["ct"]
        # pull a new model (identical to v1) - property 'sex_at_birth' valueset node should be
        # the same for both models
        subprocess.run([
            "make_model_changelog",
            "--model_handle", "TEST_B",
            "--mdf_files", "model-desc/test-model-b.yml",
            "--output_file_path", str(changelog_b),
            "-a", "operator",
            "-c", "t3"
            ], check=True)
        self.exc.execute(changelog_path=str(changelog_b),
                    changelog_location="local")
        nb = self.drv.execute_query(
            "match (a {model: 'TEST_B'}) return count(a) as ct"
            ).records[0]["ct"]
        assert nb > 0
        # no new value sets added
        assert vsct == self.drv.execute_query(
            "match (v:value_set) return count(v) as ct"
            ).records[0]["ct"]
        
    def test_new_synonyms_reuse_existing_concepts(self, tmp_path):
        changelog_pvsyn = tmp_path / "pvsyn.xml"
        cadsr_cli = CADSRClient()
        ncit_cli = NCItClient(
            ncim_tsv=Path("bento-mdb/data/source/NCIt/NCIt_Metathesaurus_Mapping.txt"))
        mdf = MDF("model-desc/test-model-a.yml")
        # following scripts/get_pvs_and_synonyms.py
        spec = make_model_cde_spec(mdf.model)
        add_cde_pvs_to_model_cde_spec(spec, cadsr_cli)
        add_ncit_synonyms_to_model_cde_spec(spec, ncit_cli)
        # following scripts/make_model_cde_changelog.py
        chglog = convert_model_cdes_to_changelog(spec, "test", "t4")
        chglog.save_to_file(changelog_pvsyn, encoding="UTF-8")
        self.exc.execute(changelog_path=str(changelog_pvsyn),
                         changelog_location="local")
        ncpt = self.drv.execute_query(
            "match (c:concept)-[:has_tag]->(:tag {key:'mapping_source', value:'NCIm'}) return count(c) as ct"
            ).records[0]["ct"]
        assert ncpt > 0
        
        # re-running the changelog shouldn't increase the number of concepts with
        # mapping_source:NCIm tag, should add the same number of concepts with
        # mapping_source:NCIm_2 tag

        self.exc.execute(changelog_path=str(changelog_pvsyn),
                         changelog_location="local")
        ncpt_2 = self.drv.execute_query(
            "match (c:concept)-[:has_tag]->(:tag {key:'mapping_source', value:'NCIm_2'}) return count(c) as ct"
            ).records[0]["ct"]
        # change mapping_source to 'NCIm_2', should see double the concepts after re-running
        # changlog
        subprocess.run([
            "sed",
            "-ie",
            "/NCIm/s/NCIm/NCIm_2/",
            changelog_pvsyn], check=True)
        self.exc.execute(changelog_path=str(changelog_pvsyn),
                         changelog_location="local")
        
        ncpt_3 = self.drv.execute_query(
            "match (c:concept)-[:has_tag]->(:tag {key:'mapping_source', value:'NCIm'}) return count(c) as ct"
            ).records[0]["ct"]
        ncpt_4 = self.drv.execute_query(
            "match (c:concept)-[:has_tag]->(:tag {key:'mapping_source', value:'NCIm_2'}) return count(c) as ct"
            ).records[0]["ct"]

        assert ncpt == ncpt_3
        assert ncpt == ncpt_4
        pass

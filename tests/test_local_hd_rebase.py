import importlib.util,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import sampler_pack
s=importlib.util.spec_from_file_location('local_hd_rebase',ROOT/'tools/rebase-local-hd-recipes.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)


class LocalHdRebase(unittest.TestCase):
    def fixture(self):
        key='000000001234abcd56781234';digest='a'*64
        ref=dict(resource_id='00020001',source_sha256='b'*64,texture_index=0,name='PB00_00')
        job=dict(reference=ref,dimensions=[[64,64]],source_rgba_sha256=[digest],wrap=0,method='restore',model='realesrgan-x4plus',detail_pass=None)
        old=dict(jobs={'old':job},groups=[dict(key=sampler_pack.tagged_key(key,0),job='old')])
        row=dict(ref,width=64,height=64,mip_levels=1,authored_levels=[dict(width=64,height=64,rgba_sha256=digest,opaque=True)],candidate_keys=[key])
        rendered=dict(ISO_only_texture_generation_complete=True,source_identity_and_edit_region_guards=True,platform_rasterization_variants=[])
        return old,[row],dict(archive_sha256='c'*64,index_sha256='d'*64),rendered

    def test_world_processing_survives_archive_identity_change(self):
        old,catalog,report,rendered=self.fixture();catalog[0]['source_sha256']='e'*64
        result=m.rebase(old,catalog,report,rendered)
        restored=[j for j in result['jobs'].values() if j['method']=='restore']
        self.assertTrue(restored);self.assertTrue(all(j['reference']['source_sha256']=='e'*64 for j in restored))

    def test_unexplained_world_pixel_change_is_not_admitted(self):
        old,catalog,report,rendered=self.fixture();catalog[0]['authored_levels'][0]['rgba_sha256']='e'*64
        with self.assertRaisesRegex(ValueError,'world/model source'):m.rebase(old,catalog,report,rendered)

    def test_explicit_guarded_ui_variant_gets_current_keys(self):
        old,catalog,report,rendered=self.fixture();catalog[0]['authored_levels'][0]['rgba_sha256']='e'*64
        catalog[0]['candidate_keys']=['000000001234abcd98769876'];rendered['platform_rasterization_variants']=[dict(resource_id='00020001')]
        result=m.rebase(old,catalog,report,rendered)
        self.assertTrue(all(j['method']=='scale' for j in result['jobs'].values()))
        self.assertTrue(all(g['canonical_key']==catalog[0]['candidate_keys'][0] for g in result['groups']))

    def test_ui_variants_need_independent_region_proof(self):
        old,catalog,report,rendered=self.fixture();rendered['source_identity_and_edit_region_guards']=False
        with self.assertRaisesRegex(ValueError,'edit-region guards'):m.rebase(old,catalog,report,rendered)


if __name__=='__main__':unittest.main()

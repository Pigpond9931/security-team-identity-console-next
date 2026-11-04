"""Storage boundaries use only disposable external directories."""
import os
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import runtime_paths as paths


class RuntimePaths(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='SecurityTeamPaths-')
        self.root = Path(self.temp.name)
        self.repo = self.root/'repo'
        self.repo.mkdir()
        self.outside = self.root/'private'

    def tearDown(self):
        self.temp.cleanup()

    def resolve(self, env):
        return paths.data_dir(environ=env, repo_root=self.repo)

    def test_default_is_dedicated_localappdata_and_does_not_create(self):
        result = self.resolve({'LOCALAPPDATA':str(self.root/'local')})
        self.assertEqual(result,self.root/'local/SecurityTeam/IdentityConsoleNext')
        self.assertFalse(result.exists())

    def test_absolute_external_override_is_not_created(self):
        self.assertEqual(self.resolve({'ST_DATA_DIR':str(self.outside)}), self.outside)
        self.assertFalse(self.outside.exists())

    def test_relative_empty_internal_root_and_ancestor_are_rejected(self):
        for value in ('', ' ', 'relative', str(self.repo/'private'), str(self.repo), str(self.root), self.root.anchor):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.resolve({'ST_DATA_DIR':value})

    def test_similar_sibling_name_is_allowed(self):
        sibling=self.repo.with_name(self.repo.name+'-private')
        self.assertEqual(self.resolve({'ST_DATA_DIR':str(sibling)}), sibling)

    def test_normalized_parent_traversal_into_repository_is_rejected(self):
        with self.assertRaises(ValueError):
            self.resolve({'ST_DATA_DIR':str(self.root/'x/../repo/private')})

    def test_populated_legacy_data_stops_even_with_external_override(self):
        legacy=self.repo/'data';legacy.mkdir()
        secret=legacy/'identity.sqlite';secret.write_bytes(b'fixture-not-a-database')
        with self.assertRaises(RuntimeError):self.resolve({'ST_DATA_DIR':str(self.outside)})
        self.assertEqual(secret.read_bytes(),b'fixture-not-a-database')
        self.assertFalse(self.outside.exists())

    def test_empty_legacy_folder_does_not_block(self):
        (self.repo/'data').mkdir()
        self.assertEqual(self.resolve({'ST_DATA_DIR':str(self.outside)}),self.outside)

    def test_existing_regular_file_is_rejected(self):
        self.outside.write_text('fixture')
        with self.assertRaises(ValueError):self.resolve({'ST_DATA_DIR':str(self.outside)})

    def test_missing_localappdata_fails_closed(self):
        with self.assertRaises(RuntimeError):self.resolve({})

    @unittest.skipUnless(os.name=='nt','Windows junction boundary')
    def test_junction_into_repository_and_external_junction_are_rejected(self):
        for target in (self.repo,self.root/'other'):
            target.mkdir(exist_ok=True)
            link=self.root/'junction'
            env=dict(os.environ,ST_PATH_LINK=str(link),ST_PATH_TARGET=str(target))
            process=subprocess.run(['powershell.exe','-NoProfile','-Command',
                'New-Item -ItemType Junction -Path $env:ST_PATH_LINK -Target $env:ST_PATH_TARGET | Out-Null'],
                env=env,capture_output=True,timeout=20)
            if process.returncode and not link.exists():
                self.skipTest('El entorno Windows no permite crear junctions; requiere ensayo fuera del sandbox.')
            self.assertEqual(process.returncode,0,process.stderr.decode(errors='replace'))
            try:
                with self.assertRaises(ValueError):self.resolve({'ST_DATA_DIR':str(link/'child')})
            finally:os.rmdir(link)

    def test_private_file_rejects_traversal(self):
        for name in ('..','../secret','nested/file'):
            with self.assertRaises(ValueError):paths.private_file(name)

    def test_unmarked_foreign_folder_is_rejected_before_permissions_or_database(self):
        self.outside.mkdir()
        sentinel=self.outside/'personal-notes.txt';sentinel.write_bytes(b'private fixture, not app data')
        before=sentinel.read_bytes();modified=sentinel.stat().st_mtime_ns
        import windows_store
        acl_before=windows_store.directory_acl(self.outside) if os.name=='nt' else None
        with patch.object(windows_store,'private_directory',side_effect=AssertionError('Foreign ACL changed')):
            with self.assertRaises(RuntimeError):paths.prepare_private_store(self.outside)
        env=dict(os.environ,ST_DATA_DIR=str(self.outside))
        env.pop('ST_TEST_MODE',None);env.pop('ST_DEMO_SEED',None)
        process=subprocess.run([sys.executable,'-c','import server;server.initialize()'],
            cwd=paths.REPO_ROOT,env=env,capture_output=True,timeout=30)
        self.assertNotEqual(process.returncode,0)
        self.assertEqual({p.name for p in self.outside.iterdir()},{sentinel.name})
        self.assertEqual(sentinel.read_bytes(),before)
        self.assertEqual(sentinel.stat().st_mtime_ns,modified)
        if acl_before is not None:self.assertEqual(windows_store.directory_acl(self.outside),acl_before)

    def test_directory_with_only_bootstrap_lock_can_be_prepared(self):
        self.outside.mkdir();lock=self.outside/'.server.lock';lock.write_bytes(b'\0')
        self.assertFalse(paths.assert_dedicated_store(self.outside))
        self.assertEqual(lock.read_bytes(),b'\0')
        self.assertFalse((self.outside/paths.STORE_MARKER).exists())

    def test_invalid_marker_never_adopts_an_existing_directory(self):
        self.outside.mkdir();marker=self.outside/paths.STORE_MARKER
        cases=(b'not json',b'{}',json.dumps({'application':'AnotherApp','format':1}).encode(),
               json.dumps({'application':paths.STORE_ID,'format':True}).encode(),b' ' * 4097)
        import windows_store
        for content in cases:
            marker.write_bytes(content)
            with self.subTest(marker_size=len(content)):
                with patch.object(windows_store,'private_directory',side_effect=AssertionError('Invalid marker changed ACL')):
                    with self.assertRaises(RuntimeError):paths.prepare_private_store(self.outside)
                self.assertEqual(marker.read_bytes(),content)

    def test_valid_marker_recognizes_store_without_modification(self):
        self.outside.mkdir();marker=self.outside/paths.STORE_MARKER
        content=json.dumps({'application':paths.STORE_ID,'format':1}).encode()
        marker.write_bytes(content);(self.outside/'identity.sqlite').write_bytes(b'fixture')
        self.assertTrue(paths.assert_dedicated_store(self.outside))
        self.assertEqual(marker.read_bytes(),content)

    @unittest.skipUnless(os.name=='nt','DPAPI store targets Windows')
    def test_fresh_preparation_creates_private_marker_and_preserves_it_on_reopen(self):
        import windows_store
        paths.prepare_private_store(self.outside)
        marker=self.outside/paths.STORE_MARKER;before=marker.read_bytes();modified=marker.stat().st_mtime_ns
        self.assertEqual(json.loads(before),{'application':paths.STORE_ID,'format':1})
        self.assertTrue(windows_store.directory_acl(self.outside)['protected'])
        paths.prepare_private_store(self.outside)
        self.assertEqual(marker.read_bytes(),before)
        self.assertEqual(marker.stat().st_mtime_ns,modified)


if __name__=='__main__':unittest.main()

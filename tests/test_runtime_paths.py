"""Storage boundaries use only disposable external directories."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

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


if __name__=='__main__':unittest.main()

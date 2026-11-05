import os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch,Mock
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
# El supervisor valida su carpeta privada al importarse. En Linux/CI se usa una
# ruta temporal externa; las pruebas sustituyen DATA y no tocan almacén real.
_import_data=tempfile.TemporaryDirectory(prefix='SecurityTeamSupervisorImport-')
with patch.dict(os.environ,{'ST_DATA_DIR':_import_data.name}):
    import supervise_cloudflare as supervisor

class Supervisor(unittest.TestCase):
    def test_failed_child_is_restarted_and_stop_marker_prevents_respawn(self):
        with tempfile.TemporaryDirectory(prefix='SecurityTeamNextSupervisor-') as temporary:
            data=Path(temporary);stop=data/'stop';calls=[]
            def launch(*args,**kwargs):
                calls.append(args)
                child=Mock()
                if len(calls)==2:stop.touch()
                child.poll.return_value=1
                return child
            with patch.object(supervisor,'DATA',data),patch.object(supervisor,'STOP',stop),patch.object(supervisor.subprocess,'Popen',side_effect=launch),patch.object(supervisor.time,'sleep'):
                supervisor.main()
            self.assertEqual(len(calls),2)
    def test_stop_during_backoff_does_not_start_another_child(self):
        with tempfile.TemporaryDirectory(prefix='SecurityTeamNextSupervisor-') as temporary:
            data=Path(temporary);stop=data/'stop';child=Mock();child.poll.return_value=1
            with patch.object(supervisor,'DATA',data),patch.object(supervisor,'STOP',stop),patch.object(supervisor.subprocess,'Popen',return_value=child) as launch,patch.object(supervisor.time,'sleep',side_effect=lambda _:stop.touch()):
                supervisor.main()
            self.assertEqual(launch.call_count,1)

if __name__=='__main__':unittest.main()

"""Ejecuta cada grupo en un proceso separado con SQLite temporal."""
from pathlib import Path
import subprocess,sys

GROUPS=['test_policy_assets','test_backend','test_v130','test_hardening','test_initial_passwords','test_terminal_rfid','test_rfid_reference_import',
        'test_browser_cameras','test_phone_links','test_camera','test_camera_admin','test_camera_removal','test_surveillance','test_supervisor','test_bootstrap','test_cctv_duration','test_group_onboarding','test_four_person_access','test_terms_revision','test_runtime_paths','test_access_capacity','test_publication_guard','test_private_backup','test_read_transactions','test_qr_readiness','test_camera_read_transactions']
if __name__=='__main__':
    root=Path(__file__).resolve().parent
    failed=[]
    for group in GROUPS:
        print('\n--- '+group+' ---',flush=True)
        result=subprocess.run([sys.executable,'-m','unittest',group,'-v'],cwd=root)
        if result.returncode:failed.append(group)
    if failed:raise SystemExit('Fallaron: '+', '.join(failed))
    print('Todos los grupos de regresión pasaron.')

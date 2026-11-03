"""Perfil local de la prueba académica: cuatro identidades, no cuatro tarjetas totales."""
import json
import db_manager as db

ZONE='DATA_CENTER_VAULT'
LICENSE='LIC-DC-VAULT'


def configure(c,usernames,issued_by='operador_windows'):
    if not isinstance(usernames,(list,tuple)) or len(usernames)!=4 or len(set(usernames))!=4:
        raise ValueError('Selecciona exactamente cuatro matrículas diferentes.')
    users=c.execute('SELECT * FROM users ORDER BY username').fetchall()
    selected=[u for u in users if u['username'] in usernames]
    if len(selected)!=4 or any(not u['is_active'] or u['is_locked'] or not u['rfid_uid'] for u in selected):
        raise ValueError('Las cuatro personas deben existir, estar activas, desbloqueadas y tener tarjeta RFID registrada.')
    if not c.execute('SELECT 1 FROM licenses_catalog WHERE license_id=?',(LICENSE,)).fetchone():raise ValueError('Falta el catálogo del centro de datos.')
    for user in users:
        zones=json.loads(user['allowed_zones'] or '[]')
        before=list(zones);authorized=user['username'] in usernames
        zones=[z for z in zones if z!=ZONE]
        if authorized:zones.append(ZONE)
        if set(zones)!=set(before):
            c.execute('UPDATE users SET allowed_zones=? WHERE id=?',(json.dumps(zones),user['id']))
            db.write_audit(c,issued_by,'ZONES_UPDATED','Perfil de cuatro: '+json.dumps(zones),user['username'])
        had=c.execute('SELECT 1 FROM user_licenses WHERE matricula=? AND license_id=?',(user['username'],LICENSE)).fetchone()
        if authorized and not had:
            c.execute('INSERT INTO user_licenses(matricula,license_id,assigned_by,assigned_at) VALUES(?,?,?,?)',(user['username'],LICENSE,issued_by,db._now()))
            db.write_audit(c,issued_by,'LICENSE_ASSIGNED',LICENSE,user['username'])
        if not authorized and had:
            c.execute('DELETE FROM user_licenses WHERE matricula=? AND license_id=?',(user['username'],LICENSE))
            db.write_audit(c,issued_by,'LICENSE_REVOKED',LICENSE,user['username'])
    c.execute('UPDATE licenses_catalog SET seats=4 WHERE license_id=?',(LICENSE,))
    for key,value in (('rfid_capacity','4'),('restricted_four_enabled','1')):
        c.execute('INSERT INTO access_settings VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',(key,value))
    db.write_audit(c,issued_by,'PROJECT_FOUR_CONFIGURED','Cuatro identidades para F1; otras zonas conservadas; visitantes excluidos; no es un límite de aforo.')
    return {'zone':ZONE,'authorized':[{'matricula':u['username'],'full_name':u['full_name']} for u in selected],'capacity':4}

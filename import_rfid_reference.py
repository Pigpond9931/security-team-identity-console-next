"""Importación local explícita autorizada; no se ejecuta al iniciar el servidor."""
if __name__ == '__main__':
    # Configurar ST_DB_PATH antes de importar el módulo de base de datos.
    import server
import json
import db_manager as db
import features
import rfid_cards

# Ejemplo opcional con identidades ficticias; adaptar y revisar antes de ejecutar.
ASSIGNMENTS = [
    ('9900001', 'dpo', None, ['0007000001', '0007000002', '7003'], list(db.ZONES)),
    ('9900002', 'area_admin', db.AREA_AC, ['0001111111'], [db.ZONE_VAULT]),
    ('9900004', 'area_admin', db.AREA_IM, ['0002222222'], [db.ZONE_SERVER]),
    ('9900003', 'area_admin', db.AREA_MON, ['0003333333'], [db.ZONE_CCTV]),
    ('9900005', 'area_admin', db.AREA_IAM, ['0004444444'], [db.ZONE_GENERAL]),
]


def apply(conn):
    """El llamador aporta transacción IMMEDIATE; cualquier conflicto revierte todo."""
    for username, role, area, cards, zones in ASSIGNMENTS:
        user = features.row_user(conn, username)
        if user['role'] != role or user['area'] != area:
            raise ValueError('Cambió el responsable de la cuenta ' + username)
        if user['rfid_uid'] and user['rfid_uid'] != cards[0]:
            raise ValueError('La cuenta ya tiene otra tarjeta: ' + username)
        for card in cards:
            if rfid_cards.owners(conn, features.normalize_rfid(card), exclude_id=user['id']):
                raise ValueError('Tarjeta vinculada a otra cuenta.')
        for zone in zones:
            license_id = features.ZONE_LICENSE.get(zone)
            if not license_id or conn.execute('SELECT 1 FROM user_licenses WHERE matricula=? AND license_id=?', (username, license_id)).fetchone():
                continue
            catalog = conn.execute('SELECT * FROM licenses_catalog WHERE license_id=?', (license_id,)).fetchone()
            used = conn.execute('SELECT COUNT(*) FROM user_licenses WHERE license_id=?', (license_id,)).fetchone()[0]
            if not catalog or used >= catalog['seats']:
                raise ValueError('Cupo de licencia agotado: ' + str(license_id))
            conn.execute('INSERT INTO user_licenses(matricula,license_id,assigned_by,assigned_at) VALUES(?,?,?,?)', (username, license_id, 'operador_windows', features.now()))
            db.write_audit(conn, 'operador_windows', 'LICENSE_ASSIGNED', license_id + ' por importación RFID autorizada', username)
        conn.execute('UPDATE users SET rfid_uid=? WHERE id=?', (cards[0], user['id']))
        conn.execute('UPDATE users SET rfid_aliases=?,allowed_zones=?,updated_at=?,security_version=security_version+1 WHERE id=?', (json.dumps(cards[1:]), json.dumps(zones), features.now(), user['id']))
        db.write_audit(conn, 'operador_windows', 'RFID_REFERENCE_IMPORTED', json.dumps({'cards': cards, 'zones': zones, 'schedules': False}), username)


if __name__ == '__main__':
    import server
    import windows_store as store
    import maintenance
    from datetime import datetime, timezone
    with store.file_lock(server.DATA / '.server.lock'):
        maintenance.backup(server.ROOT / 'backups' / ('antes-importar-rfid-' + datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%SZ')))
        server.initialize()
        with server.secure.write_transaction() as conn:
            before = {r['id']: dict(r) for r in conn.execute('SELECT * FROM users')}
            apply(conn)
            allowed = {'rfid_uid', 'rfid_aliases', 'allowed_zones', 'updated_at', 'security_version'}
            for row in conn.execute('SELECT * FROM users'):
                for key in row.keys():
                    if key not in allowed and row[key] != before[row['id']][key]:
                        raise RuntimeError('Cambió un campo ajeno a la importación.')
        print('Importación completada: 7 códigos, 5 cuentas; sin horarios. Contraseñas, MFA y roles conservados.')

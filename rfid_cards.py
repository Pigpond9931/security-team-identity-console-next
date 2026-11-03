"""Credenciales RFID adicionales, ligadas a la identidad y a su tarjeta principal."""
import json


def values(user):
    primary = user['rfid_uid']
    if not primary:
        return []
    aliases = json.loads(user['rfid_aliases'] or '[]') if 'rfid_aliases' in user.keys() else []
    if not isinstance(aliases, list) or any(not isinstance(x, str) for x in aliases):
        raise ValueError('Credenciales RFID inválidas.')
    return [primary, *aliases]


def owners(conn, value, exclude_id=None):
    from features import normalize_rfid
    result = []
    for user in conn.execute('SELECT * FROM users WHERE rfid_uid IS NOT NULL'):
        if user['id'] == exclude_id:
            continue
        try:
            matches = any(normalize_rfid(uid) == value for uid in values(user))
        except (ValueError, TypeError):
            matches = False
        if matches:
            result.append(user)
    return result

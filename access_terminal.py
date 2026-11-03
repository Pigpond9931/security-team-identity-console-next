"""Estado de operación de terminal; no sustituye permisos, licencias ni MFA."""
import db_manager as db

KEY='terminal_occupancy_limit'
AREAS=(('F1','Access Control','DATA_CENTER_VAULT'),('F2','Identity Management','SERVER_ROOM'),
       ('F3','Monitoring','MONITORING_CCTV'),('F4','IAM','GENERAL_ACCESS'))

def limit(c):
    row=c.execute('SELECT value FROM access_settings WHERE key=?',(KEY,)).fetchone()
    return int(row['value']) if row else 0

def current(c):
    return c.execute("""SELECT e.* FROM access_events e
        WHERE e.verdict='VERIFIED' AND e.direction='CHECK_IN'
        AND NOT EXISTS(SELECT 1 FROM access_events n WHERE n.verdict='VERIFIED'
          AND n.subject_type=e.subject_type AND n.subject_id=e.subject_id AND n.zone=e.zone AND n.id>e.id)
        ORDER BY e.id DESC""").fetchall()

def full_for_entry(c,kind,subject_id):
    maximum=limit(c)
    if not maximum:return False
    occupants={(r['subject_type'],r['subject_id']) for r in current(c)}
    return (kind,subject_id) not in occupants and len(occupants)>=maximum

def status(c,u):
    import features as f
    f.terminal(c,u);allowed=f.operator_zones(u);rows=[r for r in current(c) if r['zone'] in allowed]
    events=f.scope_events(c,u,50)
    return {'areas':[{'key':key,'label':label,'zone':zone,'zone_label':db.ZONES[zone],'enabled':zone in allowed} for key,label,zone in AREAS],
        'zones':[{'id':z,'label':db.ZONES[z]} for z in allowed],
        'occupancy_limit':limit(c),'can_configure':f.global_admin(u),
        'inside_count':len({(r['subject_type'],r['subject_id']) for r in rows}),
        'zone_counts':{z:sum(r['zone']==z for r in rows) for z in allowed},
        'presence':[dict(r) for r in rows],'events':events,'timezone':'America/Mexico_City'}

def configure(c,u,body):
    import features as f
    if not f.global_admin(u):raise PermissionError('Solo administración global configura el aforo.')
    maximum=body.get('occupancy_limit')
    if type(maximum)!=int or not 0<=maximum<=500:raise ValueError('Aforo entre 0 y 500; cero desactiva el límite.')
    c.execute('INSERT INTO access_settings VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',(KEY,str(maximum)))
    f.audit(c,u,'TERMINAL_OCCUPANCY_UPDATED',details='Aforo global: '+str(maximum)+'; cero=desactivado')
    return status(c,u)

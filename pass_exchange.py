"""Canje de entrega de un uso, vinculado a sesión HttpOnly y aprobación del anfitrión."""
import secrets,time
import features as f
import security as sec
import hardening as h

def delivery(c,token):
    data=f.verify(token,'PASS');hashed=h.digest(token)
    row=c.execute('SELECT * FROM mobile_passes WHERE token_hash=? AND expires_at>? AND used_at IS NULL',(hashed,time.time())).fetchone()
    if not row:raise ValueError('Entrega usada o vencida. Solicita un enlace nuevo.')
    subject=f.valid_subject(c,data)
    return data,subject,hashed

def preview(c,token):
    data,subject,_=delivery(c,token)
    return {'requires_claim':True,'requires_login':data['tipo']=='USER','terms_title':f.TERMS_TITLE,'terms_body':f.TERMS_BODY,'terms_version':f.db.TERMS_VERSION}

def claim(c,token,sid,auth):
    data,subject,hashed=delivery(c,token)
    if data['tipo']=='USER':
        user=sec.session_user(c,auth)
        if not user or user['username']!=data['ref']:raise PermissionError('Inicia sesión con la cuenta titular antes de canjear esta entrega.')
    receipt=secrets.token_urlsafe(32);key=secrets.token_urlsafe(12)
    status='approved' if data['tipo']=='USER' else 'pending'
    confirmation=str(secrets.randbelow(1000000)).zfill(6)
    c.execute('UPDATE mobile_passes SET used_at=? WHERE token_hash=? AND used_at IS NULL',(time.time(),hashed))
    c.execute('INSERT INTO pass_receipts VALUES(?,?,?,?,?,?,?,?,?,?)',(h.digest(receipt),key,h.digest(sid),data['tipo'],data['ref'],data['sv'],time.time()+900,status,confirmation,hashed))
    f.audit(c,'titular' if data['tipo']=='USER' else 'invitado','PASS_CLAIMED',data['ref'],'Canje vinculado al navegador; sin token en registros')
    return receipt

def read(c,receipt,sid,auth,accept_terms=False,download=False):
    row=c.execute('SELECT * FROM pass_receipts WHERE hash=? AND sid_hash=? AND expires>?',(h.digest(receipt),h.digest(sid),time.time())).fetchone()
    if not row:raise ValueError('Sesión de pase vencida. Solicita otra entrega.')
    data={'tipo':row['subject_type'],'ref':row['subject_id'],'sv':row['security_version']}
    subject=f.valid_subject(c,data)
    if row['subject_type']=='USER':
        user=sec.session_user(c,auth)
        if not user or user['username']!=row['subject_id']:raise PermissionError('Inicia sesión con la cuenta titular.')
    if row['status']!='approved':return {'pending_approval':True,'confirmation':row['confirmation'],'terms':{'accepted':False}}
    result=f.pass_payload(c,data,accept_terms)
    result['session_expires']=row['expires']
    if download and result['badge']['token']:
        import base64
        result.update(png_base64=base64.b64encode(f.build_wallet_png(result['badge'])).decode(),filename='credencial.png')
    return result

def approve(c,operator,receipt_id,confirmation):
    row=c.execute("SELECT * FROM pass_receipts WHERE id=? AND subject_type='VISITOR' AND status='pending' AND expires>?",(receipt_id,time.time())).fetchone()
    if not row:raise ValueError('Solicitud de dispositivo vencida o ya atendida.')
    visitor=c.execute('SELECT * FROM visitors WHERE visitor_id=?',(row['subject_id'],)).fetchone()
    if not visitor or (not f.global_admin(operator) and visitor['host_matricula']!=operator['username']):raise PermissionError('Invitado fuera de tu alcance.')
    if not secrets.compare_digest(str(confirmation),row['confirmation']):raise ValueError('Compara el código que muestra el teléfono del invitado.')
    f.valid_subject(c,{'tipo':'VISITOR','ref':row['subject_id']})
    c.execute("UPDATE pass_receipts SET status='approved' WHERE id=?",(receipt_id,))
    f.audit(c,operator,'VISITOR_DEVICE_APPROVED',row['subject_id'],'Dispositivo comparado presencialmente')
    return {'ok':True}

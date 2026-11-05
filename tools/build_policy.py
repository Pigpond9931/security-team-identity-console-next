"""Build public policy copies from terms_policy.py; never opens a private store."""
from pathlib import Path
import hashlib, html, json, re, sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from terms_policy import VERSION, TITLE, BODY, ACCEPTANCE
ASSETS=ROOT/'web'/'assets'
esc=lambda text:html.escape(str(text),quote=True)

def policy_html():
    out=[]
    status=BODY.get('status')
    if status:out.append(f'<aside class="policy-status"><div><strong>{esc(status["label"])}</strong><p>{esc(status["detail"])}</p></div></aside>')
    out.append(f'<p class="policy-intro">{esc(BODY["intro"])}</p>')
    out.append('<div class="policy-highlights">'+''.join(f'<div><strong>{esc(v["title"])}</strong><p>{esc(v["text"])}</p></div>' for v in BODY.get('summary',[]))+'</div>')
    out.append('<details class="policy-index"><summary>Contenido del documento</summary><ol>'+''.join(f'<li><a href="#clause-{i}">{esc(t)}</a></li>' for i,(t,_) in enumerate(BODY['puntos']))+'</ol></details>')
    for i,(title,text) in enumerate(BODY['puntos']):out.append(f'<section class="policy-clause" id="clause-{i}"><h2>{esc(title)}</h2><p>{esc(text)}</p></section>')
    out.append('<section class="policy-references"><span class="policy-kicker">FUENTES Y ARTÍCULOS</span><h2>Fundamento y referencias</h2><p>El régimen depende del responsable real. Las guías técnicas son voluntarias.</p>')
    for r in BODY.get('references',[]):
        if not r['url'].startswith('https://'):raise ValueError('La fuente debe usar HTTPS')
        out.append(f'<article><small>{esc(r["kind"])}</small><h3>{esc(r["title"])}</h3><strong>{esc(r["articles"])}</strong><p>{esc(r["description"])}</p><a href="{esc(r["url"])}" target="_blank" rel="noopener noreferrer">Consultar fuente oficial</a></article>')
    out.append('</section><p class="policy-footnote">'+esc(BODY['footer'])+'</p>')
    return ''.join(out)

def build():
    ASSETS.mkdir(exist_ok=True)
    payload={'title':TITLE,'body':BODY,'version':VERSION}
    digest=hashlib.sha256(json.dumps(payload,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')).hexdigest()
    payload['sha256']=digest
    (ASSETS/'politica-vigente.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    document=policy_html()
    title=esc(TITLE)
    page=f'''<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow"><meta name="theme-color" content="#0a1020"><title>Condiciones y privacidad | SECURITY TEAM</title><link rel="stylesheet" href="legal.css"></head><body class="policy-public"><a class="policy-skip" href="#documento">Saltar al documento</a><main class="policy-gate"><article class="policy-gate-card"><header class="policy-gate-head"><div><span class="policy-kicker">SECURITY TEAM / CENTRO DE CONFIANZA / {esc(VERSION)}</span><h1>Tu información.<br>Tus derechos.</h1><p>{title}</p><nav class="policy-public-nav" aria-label="Acciones del documento"><a href="/">Volver a la consola</a><button id="print-policy" type="button">Imprimir / guardar PDF</button><a href="firma-politicas.html">Constancia de lectura y firma</a></nav></div></header><div id="documento" class="policy-document" tabindex="-1">{document}</div><footer class="policy-gate-actions"><p>Consultar esta página no registra una aceptación. Las cuentas y pases solicitan confirmación expresa en su propio flujo.</p><a href="/">Volver a SECURITY TEAM</a></footer></article></main><script src="policy-page.js" defer></script></body></html>'''
    (ASSETS/'condiciones.html').write_text(page+'\n',encoding='utf-8')
    css=(ROOT/'frontend'/'legal.css').read_text(encoding='utf-8')
    css+='\n.policy-public{margin:0;font-family:system-ui,-apple-system,Segoe UI,sans-serif;background:#eef2f8}.policy-public *{box-sizing:border-box}.policy-public .policy-gate-head{padding:44px}.policy-public .policy-gate-head h1{font-size:clamp(36px,6vw,60px);line-height:1.1;margin:20px 0}.policy-public .policy-gate-head p{color:#bac8dd;font-size:14px;max-width:52ch;line-height:1.8}.policy-public-nav{display:flex;flex-wrap:wrap;gap:12px;margin-top:26px}.policy-public-nav a,.policy-public-nav button{font:600 12px/1.5 system-ui;color:#e6edfb;background:#172744;border:1px solid #425474;border-radius:8px;padding:11px 14px;text-decoration:none;cursor:pointer}.policy-public a:focus-visible,.policy-public button:focus-visible,.policy-public summary:focus-visible{outline:3px solid #527ce7;outline-offset:4px}.policy-public .policy-gate-actions{font-size:12px;line-height:1.8;color:#56657a}.policy-public .policy-gate-actions a{color:#2545b1}.policy-skip{position:absolute;top:-80px;padding:12px;background:white;color:#152238;z-index:5}.policy-skip:focus{top:4px}@media(max-width:650px){.policy-public .policy-gate-head{padding:28px 22px}}@media print{.policy-public-nav,.policy-skip,.policy-public .policy-gate-actions{display:none}.policy-public .policy-gate-head{padding:0 0 20px}.policy-public .policy-gate-head p{color:#35455d}.policy-public{font-size:10pt}.policy-document{font-size:10pt}.policy-clause h2{font-size:13pt}.policy-status{background:white}.policy-references article{break-inside:avoid}.policy-references a::after{content:" (" attr(href) ")";overflow-wrap:anywhere;font-size:8pt}}\n'
    (ASSETS/'legal.css').write_text(css,encoding='utf-8')
    (ASSETS/'policy-page.js').write_text("document.getElementById('print-policy').addEventListener('click',()=>window.print());\n",encoding='utf-8')
    # Preserve the signing controls; only replace the document and its snapshot.
    path=ASSETS/'firma-politicas.html';sign=path.read_text(encoding='utf-8')
    sign=re.sub(r'<article class="card" id="policy">.*?</article>',f'<article class="card policy-document" id="policy"><span class="eyebrow">Lee antes de firmar · {esc(VERSION)}</span><h1>{title}</h1>{document}</article>',sign,count=1,flags=re.S)
    sign=re.sub(r'<span class="pill">.*?</span>',f'<span class="pill">Piloto · {esc(VERSION)}</span>',sign,count=1)
    sign=re.sub(r'(<input id="accept" type="checkbox" required><span>).*?(</span>)',lambda m:m[1]+esc(ACCEPTANCE)+m[2],sign,count=1,flags=re.S)
    sign=re.sub(r'<a class="button" href="Politicas_y_aceptacion_SECURITY_TEAM.pdf".*?</a>','<a class="button" href="condiciones.html" target="_blank" rel="noopener">Documento vigente para imprimir</a>',sign,count=1)
    if 'href="legal.css"' not in sign:sign=sign.replace('<link rel="stylesheet" href="firma-politicas.css">','<link rel="stylesheet" href="firma-politicas.css"><link rel="stylesheet" href="legal.css">')
    sign=sign.replace('Si prefieres firmar en papel, utiliza la versión PDF imprimible.','Para firmar en papel, abre el documento vigente e imprímelo desde el navegador.')
    path.write_text(sign,encoding='utf-8')
    path=ASSETS/'firma-politicas.js';js=path.read_text(encoding='utf-8')
    js=re.sub(r'const POLICY=.*?;\n',lambda _: 'const POLICY='+json.dumps(payload,ensure_ascii=False)+';\n',js,count=1)
    js=re.sub(r'const ACCEPT=.*?;\n',lambda _: 'const ACCEPT='+json.dumps(ACCEPTANCE,ensure_ascii=False)+';\n',js,count=1)
    path.write_text(js,encoding='utf-8')
    md=[f'# {TITLE}',f'\nVersión {VERSION} · 4 de noviembre de 2026\n',f'**{BODY["status"]["label"]}**\n\n{BODY["status"]["detail"]}',BODY['intro']]
    md.extend(f'## {t}\n\n{p}' for t,p in BODY['puntos'])
    md.append('## Fuentes oficiales y guías')
    md.extend(f'### {r["title"]}\n\n{r["articles"]}\n\n{r["description"]}\n\n[Consultar fuente oficial]({r["url"]})' for r in BODY['references'])
    md.extend(['## Aceptación\n\n'+ACCEPTANCE,BODY['footer'],'SHA-256 del contenido: '+digest])
    (ROOT/f'POLITICAS_{VERSION}.md').write_text('\n\n'.join(md)+'\n',encoding='utf-8')
    print(f'Política {VERSION}: JSON, centro legal, tablet y Markdown sincronizados ({digest[:16]}).')

if __name__=='__main__':build()

import React from 'react';
import {BookOpen,ExternalLink,ShieldCheck} from 'lucide-react';
import './legal.css';

export function PolicyDocument({body,version,idPrefix='policy'}) {
 if(!body)return null;
 return <div className="policy-document">
  {body.status&&<aside className="policy-status"><ShieldCheck size={20}/><div><strong>{body.status.label}</strong><p>{body.status.detail}</p></div></aside>}
  <p className="policy-intro">{body.intro}</p>
  {!!body.summary?.length&&<div className="policy-highlights">{body.summary.map(item=><div key={item.title}><strong>{item.title}</strong><p>{item.text}</p></div>)}</div>}
  <details className="policy-index"><summary><BookOpen size={17}/>Contenido del documento · {version}</summary><ol>{body.puntos.map(([title],i)=><li key={title}><a href={'#'+idPrefix+'-'+i}>{title.replace(/^\d+\.\s*/,'')}</a></li>)}</ol></details>
  {body.puntos.map(([title,text],i)=><section className="policy-clause" id={idPrefix+'-'+i} key={title}><h2>{title}</h2><p>{text}</p></section>)}
  {!!body.references?.length&&<section className="policy-references"><span className="policy-kicker">FUENTES Y ARTÍCULOS</span><h2>Fundamento y referencias</h2><p>La ley aplicable depende de quién decide sobre los datos. Las guías técnicas son referencias voluntarias.</p>{body.references.map(ref=><article key={ref.id}><small>{ref.kind}</small><h3>{ref.title}</h3><strong>{ref.articles}</strong><p>{ref.description}</p><a href={ref.url} target="_blank" rel="noopener noreferrer">Consultar fuente oficial<ExternalLink size={14}/></a></article>)}</section>}
  <p className="policy-footnote">{body.footer}</p>
 </div>;
}

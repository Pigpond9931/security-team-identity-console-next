"""The document accepted in the app must match the published and signed copies."""
from pathlib import Path
import hashlib,json,re,sys,unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import terms_policy as policy

class PolicyCopies(unittest.TestCase):
 def test_signed_snapshot_matches_canonical_policy_and_digest(self):
  expected={'title':policy.TITLE,'body':policy.BODY,'version':policy.VERSION}
  js=(ROOT/'web/assets/firma-politicas.js').read_text(encoding='utf-8')
  snapshot=json.loads(re.search(r'^const POLICY=(.*);$',js,re.M)[1])
  digest=snapshot.pop('sha256')
  self.assertEqual(snapshot,expected)
  self.assertEqual(digest,hashlib.sha256(json.dumps(expected,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest())
  public=json.loads((ROOT/'web/assets/politica-vigente.json').read_text(encoding='utf-8'))
  self.assertEqual(public,{**expected,'sha256':digest})
 def test_both_html_copies_contain_every_clause_and_reference(self):
  import html
  for name in ['condiciones.html','firma-politicas.html']:
   text=html.unescape((ROOT/'web/assets'/name).read_text(encoding='utf-8'))
   for title,body in policy.BODY['puntos']:
    self.assertIn(title,text);self.assertIn(body,text)
   for item in policy.BODY['references']:
    for key in ['title','articles','description','url']:self.assertIn(item[key],text)
   self.assertIn(policy.BODY['status']['detail'],text)
   self.assertIn(policy.BODY['footer'],text)
  self.assertNotIn('href="Politicas_y_aceptacion_SECURITY_TEAM.pdf"',text)
 def test_tablet_checkbox_is_unchecked_and_uses_current_acceptance(self):
  text=(ROOT/'web/assets/firma-politicas.html').read_text(encoding='utf-8')
  element=re.search(r'<input id="accept"[^>]*>',text)[0]
  self.assertNotIn('checked',element);self.assertIn(policy.BODY['acceptance'],text)
 def test_prior_document_remains_old_version(self):
  archive=json.loads((ROOT/'docs/legal/politica-v1.1.json').read_text(encoding='utf-8'))
  self.assertEqual(archive['version'],'v1.1')
  self.assertNotEqual(archive['body'],policy.BODY)

if __name__=='__main__':unittest.main()

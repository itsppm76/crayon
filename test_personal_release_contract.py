from pathlib import Path
import json
D=Path(__file__).parent/'docs'
def test_personal_api_not_repointed_to_static_origin():
 assert "const API='https://crayon-v1.onrender.com'" in (D/'app.js').read_text()
def test_personal_scoped_manifest():
 m=json.loads((D/'manifest.webmanifest').read_text())
 assert m['id']==m['scope']=='/crayon/' and m['start_url'].startswith('/crayon/')
 assert 'rel="manifest"' in (D/'index.html').read_text()
 for i in m['icons']:assert (D/i['src']).is_file()
def test_export_html_breaks_preserved():
 s=(D/'exports.js').read_text()
 assert "querySelectorAll('br')" in s and "createTextNode('\\n')" in s
def test_no_live_voice_store_mount():
 for f in ['main.py','cr_web_http.py','cr_web_app.py']:
  assert 'cr_voice_tickets' not in (D.parent/f).read_text()

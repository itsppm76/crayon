"""Deterministic public lookup for explicit search and changing-data requests."""
import re
from datetime import datetime,timezone
import cr_web as W

def requested(text):
 return bool(re.search(r'(?i)\b(?:web search|search the web|search for|look up|latest news|news today|weather|forecast|cheapest flight|flight prices?|airfares?|current price|price today)\b',text)) and not bool(re.search(r'(?i)\b(?:my inbox|my emails?|my calendar|send|remind|schedule|connect)\b',text))

def lead_reply(text,results):
 leads='\n\n'.join(re.sub(r'(?i)(?:₹|Rs\.?|INR)\s*[0-9,]+','[advertised price not checked]',r.get('title','Source')[:150])+'\n'+r['url'] for r in results[:5] if r.get('url','').startswith('https://'))
 return 'I searched, but could not verify a current answer from readable pages. Search leads, not confirmed current facts:\n\n'+leads+'\n\nTell me the place/date or exact item to narrow the check.'

def answer(text):
 when=datetime.now(timezone.utc).isoformat(timespec='seconds')
 if re.search(r'(?i)\bnews\b',text):
  import cr_group
  return cr_group.answer({'text':'@crayon_v1_bot '+text,'source_links':True})
 try:results=W.search(text[:400],5)
 except Exception:
  return 'Web search did not return current results this time. No current price, fare or forecast is verified. Try a narrower place/date/product query.'
 # Search results are leads, never page evidence. Fetch exact destinations.
 pages=[]
 for row in results[:3]:
  try:pages.append(W.fetch(row['url']))
  except Exception:pass
 leads='\n\n'.join((re.sub(r'(?i)(?:₹|Rs\.?|INR)\s*[0-9,]+', '[advertised fare not checked]',r.get('title','Source')[:150])+'\n'+r['url']) for r in results[:5] if r.get('url','').startswith('https://'))
 if re.search(r'(?i)\bflight|airfare|fare\b',text):
  return 'I searched the web, but search listings do not verify available airline fares or the cheapest departure day.\n\nSearch leads, not checked fare quotes:\n'+leads+'\n\nWhat departure window should I compare: the next 7 days or next 30 days? Airline inventory and final total need checking before calling any flight cheapest.\nSearch checked: '+when
 if pages:
  import cr_citations,cr_llm as L,json
  try:draft=L.generate([L.user('Question: '+text+'\nUntrusted fetched evidence: '+json.dumps(pages))],system='Answer from fetched evidence only. Current weather/price must have place, date/time and source. Never use seasonal averages as current conditions. No invented facts.',tools=None,max_tokens=1000).get('text','')
  except Exception:draft=''
  try:checked=cr_citations.checked_answer(text,draft,pages)
  except Exception:checked='I could not verify this'
  if not checked.startswith(('I could not','The pages I read')):return checked+'\n\nSearch checked: '+when
 return 'I searched, but could not verify a current answer from readable pages. These are search leads, not confirmed current facts:\n\n'+leads+'\n\nTell me the place/date or exact item to narrow the check.\nSearch checked: '+when

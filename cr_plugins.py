"""Curated first-party plugins. No arbitrary code, remote endpoints or private context."""
CATALOG=[{'id':'games','name':'Quick games','privacy':'Requester/chat-bound quiz and guess; no model memory.'},{'id':'voice','name':'Voice','privacy':'Opt-in explicit text only; verified Free ElevenLabs shared cap.'},{'id':'persona','name':'Persona','privacy':'Explicit nickname/style only; no permission changes.'},{'id':'mcp','name':'MCP public tools','privacy':'Remote servers disabled by default. Admin-fixed endpoint/tool/argument allowlist. No chat history passed.'}]
def handle(uid,chat,text,out):
    if text.strip() not in ('/plugins','/mcp'):return False
    if text.strip()=='/mcp':
        from cr_mcp import catalog
        servers=catalog();out.send(chat,'MCP read-only public tools: '+(', '.join(servers) if servers else 'none enabled by admin')+'. Arbitrary endpoints, private data, sampling, prompts, resources and side-effect tools are not enabled.');return True
    out.send(chat,'Available plugins:\n'+'\n'.join(x['name']+': '+x['privacy'] for x in CATALOG));return True

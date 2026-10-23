"""Dev-only page: live captions of the other person plus a box to type replies (spike)."""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse

from app.config import Settings, get_settings

router = APIRouter(tags=["dev"])

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Awaaz dev console</title>
<style>
:root{color-scheme:light dark}body{font:16px system-ui;margin:0;display:flex;flex-direction:column;height:100dvh}
#feed{flex:1;overflow:auto;padding:16px;display:flex;flex-direction:column;gap:8px}
.b{max-width:80%;padding:10px 14px;border-radius:14px;line-height:1.4}
.them{background:#8883;align-self:flex-start}.you{background:#2563eb;color:#fff;align-self:flex-end}.prev{align-self:flex-end;border:1px solid #2563eb;max-width:80%;padding:10px 14px;border-radius:14px}.prev button{margin:8px 8px 0 0;padding:6px 12px}
form{display:flex;gap:8px;padding:12px;border-top:1px solid #8884}
input{flex:1;font:inherit;padding:12px;border-radius:10px;border:1px solid #8886;background:transparent;color:inherit}
button{font:inherit;padding:0 18px;border-radius:10px;border:0;background:#2563eb;color:#fff}
#s{padding:6px 16px;font-size:13px;opacity:.7}
</style></head><body><div id="s">Waiting for the call...</div><div id="feed"></div>
<form id="f"><input id="t" autocomplete="off" placeholder="Type what you want to say, press Enter" autofocus>
<button>Say</button></form>
<script>
const S=new URLSearchParams(location.search).get('s'),H={Authorization:'Bearer '+S,'Content-Type':'application/json'};
const feed=document.getElementById('feed'),st=document.getElementById('s');let shown=0,nodes={},typed=0;
function put(turn,text){let n=nodes[turn];if(!n){n=document.createElement('div');n.className='b them';feed.appendChild(n);nodes[turn]=n}
n.textContent=text;feed.scrollTop=feed.scrollHeight}
async function poll(){try{const r=await fetch('/v1/dev/captions',{headers:H});const d=await r.json();
d.captions.forEach(c=>put(c.turn,c.text));st.textContent='Live. Captions: '+d.captions.length}catch(e){st.textContent='Disconnected'}setTimeout(poll,600)}
poll();
document.getElementById('t').addEventListener('input',()=>{if(Date.now()-typed>1500){typed=Date.now();fetch('/v1/dev/typing',{method:'POST',headers:H})}});
const post=(u,b)=>fetch(u,{method:'POST',headers:H,body:b?JSON.stringify(b):undefined});
function bubble(cls,text){const n=document.createElement('div');n.className='b '+cls;n.textContent=text;feed.appendChild(n);feed.scrollTop=feed.scrollHeight;return n}
async function speak(text,node){await post('/v1/dev/say',{text});node.remove();bubble('you',text)}
document.getElementById('f').addEventListener('submit',async e=>{e.preventDefault();const i=document.getElementById('t'),v=i.value.trim();if(!v)return;i.value='';
const p=await(await post('/v1/dev/preview',{text:v})).json();
if(p.hindi===p.original){bubble('you',v);await post('/v1/dev/say',{text:v});return}
const n=document.createElement('div');n.className='b prev';feed.appendChild(n);
n.append(document.createTextNode('Will be spoken as:'),document.createElement('br'));
const t=document.createElement('strong');t.textContent=p.hindi;n.append(t,document.createElement('br'));
for(const [label,txt] of [['Say this',p.hindi],['Say as typed',p.original]]){const bt=document.createElement('button');bt.type='button';bt.textContent=label;bt.onclick=()=>speak(txt,n);n.append(bt)}
const x=document.createElement('button');x.type='button';x.textContent='Cancel';x.onclick=()=>n.remove();n.append(x);feed.scrollTop=feed.scrollHeight});
</script></body></html>"""


@router.get("/dev/console", response_class=HTMLResponse)
async def console(s: str | None = Query(None), settings: Settings = Depends(get_settings)) -> str:
    if settings.app_env != "local" or s != settings.webhook_secret:
        raise HTTPException(status_code=404)
    return PAGE

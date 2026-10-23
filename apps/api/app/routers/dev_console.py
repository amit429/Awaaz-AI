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
</style></head><body><div id="s">Waiting for the call...</div><div style="padding:0 16px">Read as <select id="m"><option value="original">Original (Hindi)</option><option value="hinglish">Hinglish (Latin letters)</option><option value="english">English (translated)</option><option value="marathi">Marathi (translated)</option></select></div><div id="feed"></div>
<form id="f"><input id="t" autocomplete="off" placeholder="Type what you want to say, press Enter" autofocus>
<button>Say</button></form>
<script>
const S=new URLSearchParams(location.search).get('s'),H={Authorization:'Bearer '+S,'Content-Type':'application/json'};
const feed=document.getElementById('feed'),st=document.getElementById('s');let shown=0,nodes={},typed=0;
function put(c,mode){let n=nodes[c.turn];if(!n){n=document.createElement('div');n.className='b them';feed.appendChild(n);nodes[c.turn]=n}
n.textContent='';const m=document.createElement('div');m.textContent=c.read;n.append(m);
if(mode==='english'||mode==='marathi'){const o=document.createElement('small');o.style.opacity='.65';o.textContent='Translated. Heard: '+c.text;n.append(o)}
feed.scrollTop=feed.scrollHeight}
async function poll(){try{const mode=document.getElementById('m').value;const r=await fetch('/v1/dev/captions?mode='+mode,{headers:H});const d=await r.json();
if(d.mode===mode)d.captions.forEach(c=>put(c,mode));st.textContent='Live. Captions: '+d.captions.length}catch(e){st.textContent='Disconnected'}setTimeout(poll,600)}
poll();
document.getElementById('t').addEventListener('input',()=>{if(Date.now()-typed>1500){typed=Date.now();fetch('/v1/dev/typing',{method:'POST',headers:H})}});
const post=(u,b)=>fetch(u,{method:'POST',headers:H,body:b?JSON.stringify(b):undefined});
function bubble(cls,text,sub){const n=document.createElement('div');n.className='b '+cls;n.textContent=text;
if(sub){const o=document.createElement('small');o.style.display='block';o.style.opacity='.7';o.textContent=sub;n.append(o)}
feed.appendChild(n);feed.scrollTop=feed.scrollHeight;return n}
let pending=null;
function clearPending(){if(pending){pending.node.remove();pending=null}}
async function send(spoken,original){clearPending();await post('/v1/dev/say',{text:spoken});bubble('you',spoken,original&&original!==spoken?'You typed: '+original:null)}
const input=document.getElementById('t');
const cache={};let tm=null;
function prepare(v){return cache[v]||(cache[v]=post('/v1/dev/prepare',{text:v}).then(r=>r.json()))}
input.addEventListener('input',()=>{clearTimeout(tm);const v=input.value.trim();if(v)tm=setTimeout(()=>prepare(v),700)});
document.getElementById('f').addEventListener('submit',async e=>{e.preventDefault();
if(pending){await send(pending.spoken,pending.original);return}
const v=input.value.trim();if(!v)return;input.value='';
const p=await prepare(v);
if(!p.needs_confirm){await send(p.spoken,v);return}
const n=document.createElement('div');n.className='b prev';
n.append(document.createTextNode(p.kind==='translated'?'Translated, press Enter to send:':'Please check, press Enter to send:'),document.createElement('br'));
const t=document.createElement('strong');t.textContent=p.spoken;n.append(t,document.createElement('br'));
const ed=document.createElement('button');ed.type='button';ed.textContent='Edit';ed.onclick=()=>{input.value=v;clearPending();input.focus()};n.append(ed);
const x=document.createElement('button');x.type='button';x.textContent='Cancel';x.onclick=clearPending;n.append(x);
feed.appendChild(n);feed.scrollTop=feed.scrollHeight;pending={node:n,spoken:p.spoken,original:v}});
document.addEventListener('keydown',e=>{if(e.key==='Escape')clearPending()});
</script></body></html>"""


@router.get("/dev/console", response_class=HTMLResponse)
async def console(s: str | None = Query(None), settings: Settings = Depends(get_settings)) -> str:
    if settings.app_env != "local" or s != settings.webhook_secret:
        raise HTTPException(status_code=404)
    return PAGE

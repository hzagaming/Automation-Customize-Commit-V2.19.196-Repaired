"""Local web GUI: stdlib HTTP server + single page front end."""

from __future__ import annotations

import json
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import agent, engine

PAGE = r"""<!doctype html>
<html lang='zh-CN'>
<head>
<meta charset='utf-8'>
<meta name='viewport' content='width=device-width,initial-scale=1'>
<title>Automation Customize Commit</title>
<style>
:root{--bg:#0d1014;--card:#161a21;--card2:#1d222b;--line:#262d38;--txt:#e6ebf2;--dim:#8b95a5;--acc:#4f8cff;--ok:#3ecf8e;--err:#ff6b6b;--warn:#f5c451}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--txt);font:14px/1.5 -apple-system,BlinkMacSystemFont,'SF Pro Text','PingFang SC',sans-serif}
.wrap{max-width:1080px;margin:0 auto;padding:28px 20px 60px}
header{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:20px}
h1{font-size:19px;margin:0;font-weight:600;letter-spacing:.2px}
.ver{font-size:12px;color:var(--dim);border:1px solid var(--line);border-radius:20px;padding:2px 9px}
.meta{margin-left:auto;font-size:12px;color:var(--dim)}
.chip{font-size:12px;margin-left:8px;padding:4px 11px;border-radius:20px;border:1px solid var(--line);color:var(--dim)}
.chip.on{color:var(--ok);border-color:rgba(62,207,142,.4);background:rgba(62,207,142,.08)}
.chip.off{color:var(--warn);border-color:rgba(245,196,81,.35);background:rgba(245,196,81,.08)}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:18px;margin-bottom:16px}
.grid{display:grid;grid-template-columns:1.15fr 1fr .7fr;gap:14px}
.grid .full{grid-column:1/-1}
label{display:block;font-size:12px;color:var(--dim);margin-bottom:6px}
input,select,button{font:inherit}
input[type=text],input[type=datetime-local],select{width:100%;background:var(--card2);border:1px solid var(--line);color:var(--txt);border-radius:9px;padding:9px 11px;outline:none}
input:focus,select:focus{border-color:var(--acc)}
.quick{display:flex;gap:8px;margin-top:8px;flex-wrap:wrap}
.quick button,.ghost{background:transparent;border:1px solid var(--line);color:var(--dim);border-radius:9px;padding:6px 11px;cursor:pointer;font-size:12px}
.quick button:hover,.ghost:hover{border-color:var(--acc);color:var(--txt)}
.row{display:flex;gap:18px;align-items:center;flex-wrap:wrap;margin-top:14px}
.check{display:flex;gap:7px;align-items:center;font-size:13px;color:var(--dim);cursor:pointer;margin:0}
.check input{accent-color:var(--acc)}
.primary{margin-left:auto;background:var(--acc);border:none;color:#fff;border-radius:10px;padding:10px 22px;font-weight:600;cursor:pointer}
.primary:hover{filter:brightness(1.1)}
table{width:100%;border-collapse:collapse;font-size:13px}
th{text-align:left;color:var(--dim);font-weight:500;font-size:12px;padding:0 10px 9px;border-bottom:1px solid var(--line)}
td{padding:11px 10px;border-bottom:1px solid rgba(38,45,56,.6);vertical-align:top}
tr:last-child td{border-bottom:none}
.mono{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12px;color:var(--dim);word-break:break-all}
.st{font-size:12px;padding:2px 9px;border-radius:20px;white-space:nowrap}
.st.pending{background:rgba(79,140,255,.12);color:var(--acc)}
.st.done{background:rgba(62,207,142,.12);color:var(--ok)}
.st.error{background:rgba(255,107,107,.12);color:var(--err)}
.rep{font-size:12px;color:var(--warn);white-space:nowrap}
select.mini{background:transparent;border:1px solid var(--line);color:var(--dim);border-radius:7px;padding:3px 5px;font-size:12px;width:100%}
.del,.act{background:none;border:none;color:var(--dim);cursor:pointer;font-size:13px;white-space:nowrap}
td .act{margin-right:10px}
td.acts{white-space:nowrap;text-align:right}
.act:hover{color:var(--acc)}
.del:hover{color:var(--err)}
.bar{display:flex;gap:10px;align-items:center;margin-bottom:14px;flex-wrap:wrap}
.bar .sp{flex:1}
h2{font-size:13px;color:var(--dim);margin:0 0 12px;font-weight:500}
pre{background:#0a0c10;border:1px solid var(--line);border-radius:10px;padding:12px;font-size:12px;color:var(--dim);max-height:190px;overflow:auto;margin:0}
.empty{color:var(--dim);text-align:center;padding:26px 0;font-size:13px}
#toast{position:fixed;left:50%;bottom:26px;transform:translate(-50%,20px);background:#243044;color:var(--txt);border:1px solid var(--line);padding:10px 18px;border-radius:10px;font-size:13px;opacity:0;transition:.25s;pointer-events:none}
#toast.show{opacity:1;transform:translate(-50%,0)}
</style>
</head>
<body>
<div class='wrap'>
  <header>
    <h1>Automation Customize Commit</h1>
    <span class='ver'>V__VERSION__</span>
    <span class='meta' id='nextInfo'></span>
    <span class='chip' id='agentChip'>代理检测中…</span>
  </header>

  <div class='card'>
    <h2>新建定时提交</h2>
    <div class='grid'>
      <div class='full'>
        <label>仓库路径</label>
        <input type='text' id='repo' list='repos' placeholder='/Users/you/code/project'>
        <datalist id='repos'></datalist>
      </div>
      <div>
        <label>执行时间</label>
        <input type='datetime-local' id='at'>
        <div class='quick'>
          <button data-q='10'>10 分钟后</button>
          <button data-q='tonight'>今晚 23:00</button>
          <button data-q='morning'>明天 09:00</button>
        </div>
      </div>
      <div>
        <label>提交信息</label>
        <input type='text' id='message' value='chore: scheduled commit'>
      </div>
      <div>
        <label>重复</label>
        <select id='repeat'>
          <option value='none'>不重复</option>
          <option value='daily'>每天</option>
          <option value='weekly'>每周</option>
        </select>
      </div>
      <div>
        <label>提交内容</label>
        <select id='mode'>
          <option value='file'>追加时间戳到文件</option>
          <option value='all'>提交仓库全部改动</option>
          <option value='empty'>空提交</option>
        </select>
      </div>
      <div style='grid-column:span 2'>
        <label>目标文件（追加模式）</label>
        <input type='text' id='file' value='commit-log.txt'>
      </div>
    </div>
    <div class='row'>
      <label class='check'><input type='checkbox' id='push' checked>执行后推送 origin</label>
      <label class='check'><input type='checkbox' id='backdate'>commit 时间戳写成所选时间</label>
      <button class='primary' id='add'>添加任务</button>
    </div>
  </div>

  <div class='card'>
    <div class='bar'>
      <h2 style='margin:0'>任务队列</h2>
      <span class='sp'></span>
      <button class='ghost' id='runNow'>立即执行到期任务</button>
      <button class='ghost' id='agentBtn'>安装后台代理</button>
    </div>
    <table>
      <thead><tr><th style='width:108px'>时间</th><th style='width:174px'>仓库</th><th>提交信息</th><th style='width:88px'>重复</th><th style='width:74px'>状态</th><th style='width:104px'></th></tr></thead>
      <tbody id='jobs'><tr><td colspan='6' class='empty'>暂无任务</td></tr></tbody>
    </table>
  </div>

  <div class='card'>
    <h2>执行日志</h2>
    <pre id='log'>（空）</pre>
  </div>
</div>
<div id='toast'></div>

<script>
const q = s => document.querySelector(s);
let agentOn = false;
let nextAt = null;

function toast(msg){
  const t = q('#toast');
  t.textContent = msg; t.classList.add('show');
  clearTimeout(window._tt); window._tt = setTimeout(()=>t.classList.remove('show'), 2200);
}

function pad(n){ return String(n).padStart(2,'0'); }
function localValue(d){
  return d.getFullYear()+'-'+pad(d.getMonth()+1)+'-'+pad(d.getDate())+'T'+pad(d.getHours())+':'+pad(d.getMinutes());
}
function fmtAt(iso){
  const d = new Date(iso);
  return pad(d.getMonth()+1)+'-'+pad(d.getDate())+' '+pad(d.getHours())+':'+pad(d.getMinutes());
}
function activeMode(){ return q('#mode').value; }

function tick(){
  const el = q('#nextInfo');
  if(!nextAt){ el.textContent = '没有待执行任务'; return; }
  const ms = new Date(nextAt) - new Date();
  if(ms <= 0){ el.textContent = '有任务待执行'; return; }
  const h = Math.floor(ms/3600000), m = Math.floor(ms%3600000/60000), sec = Math.floor(ms%60000/1000);
  el.textContent = '下一个 ' + fmtAt(nextAt) + ' · ' + (h ? h+' 小时 ' : '') + m + ' 分 ' + pad(sec) + ' 秒';
}

document.querySelectorAll('.quick button').forEach(b=>{
  b.onclick = ()=>{
    const now = new Date(); let d;
    if(b.dataset.q==='10'){ d = new Date(now.getTime()+10*60000); }
    else if(b.dataset.q==='tonight'){ d = new Date(now); d.setHours(23,0,0,0); if(d<=now) d.setDate(d.getDate()+1); }
    else { d = new Date(now); d.setHours(9,0,0,0); d.setDate(d.getDate()+1); }
    q('#at').value = localValue(d);
  };
});

q('#mode').onchange = ()=>{ q('#file').disabled = activeMode()!=='file'; };

async function api(path, body){
  const opt = body===undefined ? {} : {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)};
  const r = await fetch(path, opt);
  const data = await r.json();
  if(!r.ok) throw new Error(data.error || r.statusText);
  return data;
}

async function load(){
  const s = await api('/api/state');
  agentOn = s.agent;
  const chip = q('#agentChip');
  chip.className = 'chip ' + (s.agent ? 'on' : 'off');
  chip.textContent = s.agent ? '后台代理运行中' : '后台代理未安装';
  q('#agentBtn').textContent = s.agent ? '卸载后台代理' : '安装后台代理';

  const repos = [...new Set(s.jobs.map(j=>j.repo))];
  q('#repos').innerHTML = repos.map(r=>'<option value="'+r+'">').join('');

  nextAt = s.next ? s.next.at : null;
  tick();

  const tb = q('#jobs');
  if(!s.jobs.length){ tb.innerHTML = "<tr><td colspan='6' class='empty'>暂无任务</td></tr>"; }
  else {
    tb.innerHTML = s.jobs.map(j=>{
      const when = fmtAt(j.at) + (j.backdate ? ' <span style="color:#8b95a5">(回填)</span>' : '');
      const ran = j.last_run ? '<div class="mono">上次 ' + fmtAt(j.last_run) + '</div>' : '';
      const hint = j.last_error ? '<div class="mono" style="color:#ff6b6b">'+j.last_error+'</div>' : '';
      const opts = [['none','—'],['daily','每天'],['weekly','每周']]
        .map(([v,t]) => '<option value="'+v+'"'+(j.repeat===v?' selected':'')+'>'+t+'</option>').join('');
      return '<tr><td>'+when+'</td><td class="mono">'+j.repo+'</td>'+
        '<td>'+j.message+(j.push?'':' <span style="color:#8b95a5">· 仅本地</span>')+ran+hint+'</td>'+
        '<td><select class="mini" data-id="'+j.id+'">'+opts+'</select></td>'+
        '<td><span class="st '+j.status+'">'+({pending:'待执行',done:'已完成',error:'失败'}[j.status]||j.status)+'</span></td>'+
        '<td class="acts"><button class="act" data-run="'+j.id+'">立即</button><button class="del" data-del="'+j.id+'">删除</button></td></tr>';
    }).join('');
    tb.querySelectorAll('[data-del]').forEach(b=>b.onclick = async ()=>{
      await api('/api/jobs/delete',{id:b.dataset.del}); toast('已删除'); load();
    });
    tb.querySelectorAll('[data-run]').forEach(b=>b.onclick = async ()=>{
      try{ await api('/api/jobs/run',{id:b.dataset.run}); toast('已执行'); load(); }
      catch(e){ toast('失败: ' + e.message); }
    });
    tb.querySelectorAll('select.mini').forEach(sel=>sel.onchange = async ()=>{
      try{ await api('/api/jobs/repeat',{id:sel.dataset.id, repeat:sel.value}); toast('已更新重复'); load(); }
      catch(e){ toast('失败: ' + e.message); }
    });
  }
  q('#log').textContent = s.log.length ? s.log.join('\n') : '（空）';
}

q('#add').onclick = async ()=>{
  const mode = activeMode();
  const body = {
    repo: q('#repo').value.trim(),
    at: q('#at').value,
    message: q('#message').value.trim() || 'chore: scheduled commit',
    file: mode==='file' ? (q('#file').value.trim() || 'commit-log.txt') : null,
    push: q('#push').checked,
    backdate: q('#backdate').checked,
    repeat: q('#repeat').value
  };
  if(!body.repo){ return toast('先填仓库路径'); }
  if(!body.at){ return toast('先选执行时间'); }
  try{
    await api('/api/jobs', body);
    toast('已添加 ' + fmtAt(body.at));
    load();
  }catch(e){ toast('失败: ' + e.message); }
};

q('#runNow').onclick = async ()=>{
  try{ const r = await api('/api/run', {}); toast(r.count ? ('已执行 '+r.count+' 个任务') : '没有到期任务'); load(); }
  catch(e){ toast('失败: ' + e.message); }
};

q('#agentBtn').onclick = async ()=>{
  try{
    await api('/api/agent', {action: agentOn ? 'uninstall' : 'install'});
    toast(agentOn ? '后台代理已卸载' : '后台代理已安装'); load();
  }catch(e){ toast('失败: ' + e.message); }
};

load();
setInterval(load, 3000);
setInterval(tick, 1000);
</script>
</body>
</html>
"""


def state_payload() -> dict:
    jobs = sorted(engine.load_jobs(), key=lambda j: j["at"])
    return {
        "version": engine.VERSION,
        "agent": agent.is_installed(),
        "jobs": jobs,
        "next": engine.next_due(jobs),
        "log": engine.tail_log(),
    }


class Handler(BaseHTTPRequestHandler):
    server_version = f"CommitAuto/{engine.VERSION}"

    def log_message(self, *args):  # silence per-request stderr spam
        pass

    def _send(self, code: int, payload) -> None:
        body = payload if isinstance(payload, bytes) else json.dumps(payload, ensure_ascii=False).encode()
        ctype = "text/html; charset=utf-8" if isinstance(payload, bytes) else "application/json"
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path in {"/", "/index.html"}:
            return self._send(200, PAGE.replace("__VERSION__", engine.VERSION).encode())
        if self.path == "/api/state":
            return self._send(200, state_payload())
        self._send(404, {"error": "not found"})

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            return self._send(400, {"error": "bad json"})
        try:
            if self.path == "/api/jobs":
                engine.add_job(body.get("repo", ""), body.get("at", ""), body.get("message", ""),
                               file=body.get("file"), branch=body.get("branch"),
                               push=body.get("push", True), backdate=body.get("backdate", False),
                               repeat=body.get("repeat", "none"))
                return self._send(200, {"ok": True})
            if self.path == "/api/jobs/run":
                job = engine.run_job(body.get("id", ""))
                return self._send(200, {"ok": True, "job": job})
            if self.path == "/api/jobs/repeat":
                job = engine.set_repeat(body.get("id", ""), body.get("repeat", "none"))
                return self._send(200, {"ok": True, "job": job})
            if self.path == "/api/jobs/delete":
                deleted = engine.delete_job(body.get("id", ""))
                return self._send(200 if deleted else 404, {"ok": deleted})
            if self.path == "/api/run":
                due = engine.run_due()
                return self._send(200, {"count": len(due), "jobs": due})
            if self.path == "/api/agent":
                agent.uninstall() if body.get("action") == "uninstall" else agent.install()
                return self._send(200, {"ok": True})
        except Exception as exc:  # noqa: BLE001 - reported to the UI
            return self._send(400, {"error": str(exc)})
        self._send(404, {"error": "not found"})


def serve(port: int = 8765, open_browser: bool = True) -> None:
    for candidate in range(port, port + 11):
        try:
            httpd = ThreadingHTTPServer(("127.0.0.1", candidate), Handler)
            break
        except OSError:
            continue
    else:
        raise SystemExit("no free port")
    url = f"http://127.0.0.1:{candidate}"
    print(f"Automation Customize Commit V{engine.VERSION} -> {url}")
    if open_browser:
        webbrowser.open(url)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nbye")
    finally:
        httpd.server_close()

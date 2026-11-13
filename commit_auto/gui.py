"""Local web GUI: stdlib HTTP server + single page front end."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import webbrowser
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from . import agent, engine
from .i18n import I18N, LANGS

PAGE = r"""<!doctype html>
<html lang='zh-CN'>
<head>
<meta charset='utf-8'>
<meta name='viewport' content='width=device-width,initial-scale=1'>
<title>Automation Customize Commit</title>
<style>
:root{--bg:#0d1014;--card:#161a21;--card2:#1d222b;--line:#262d38;--txt:#e6ebf2;--dim:#8b95a5;
--acc:#4f8cff;--c0:#1b2027;--c1:#1f4d34;--c2:#2c7a4d;--c3:#3ecf8e;--c4:#8bf3bd;--ok:#3ecf8e;--err:#ff6b6b;--warn:#f5c451}
body[data-theme='light']{--bg:#f5f7fa;--card:#ffffff;--card2:#f0f3f7;--line:#e3e8ef;--txt:#141a22;--dim:#5f6b7a;
--c0:#eaeef2;--c1:#c6e9d3;--c2:#8ed8ab;--c3:#40c463;--c4:#216e39;--ok:#1a9f5b;--err:#d1453b;--warn:#b7791f}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--txt);font:14px/1.5 -apple-system,BlinkMacSystemFont,'SF Pro Text','PingFang SC',sans-serif;transition:background .2s,color .2s}
.wrap{max-width:1080px;margin:0 auto;padding:26px 20px 60px}
header{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:18px}
h1{font-size:19px;margin:0;font-weight:600;letter-spacing:.2px}
.ver{font-size:12px;color:var(--dim);border:1px solid var(--line);border-radius:20px;padding:2px 9px}
.sp{flex:1}
.meta{font-size:12px;color:var(--dim)}
.prefs{display:flex;align-items:center;gap:8px}
.prefs select{background:var(--card);border:1px solid var(--line);color:var(--dim);border-radius:8px;padding:4px 7px;font-size:12px;width:auto}
.dots{display:flex;gap:5px}
.dot{width:14px;height:14px;border-radius:50%;border:2px solid transparent;cursor:pointer;padding:0}
.dot.on{border-color:var(--txt)}
.chip{font-size:12px;padding:4px 11px;border-radius:20px;border:1px solid var(--line);color:var(--dim);white-space:nowrap}
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
.primary:hover{filter:brightness(1.08)}
table{width:100%;border-collapse:collapse;font-size:13px}
th{text-align:left;color:var(--dim);font-weight:500;font-size:12px;padding:0 10px 9px;border-bottom:1px solid var(--line)}
td{padding:11px 10px;border-bottom:1px solid var(--line);vertical-align:top}
tr:last-child td{border-bottom:none}
.mono{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12px;color:var(--dim);word-break:break-all}
.st{font-size:12px;padding:2px 9px;border-radius:20px;white-space:nowrap}
.st.pending{background:rgba(79,140,255,.14);color:var(--acc)}
.st.done{background:rgba(62,207,142,.14);color:var(--ok)}
.st.error{background:rgba(255,107,107,.14);color:var(--err)}
.del,.act{background:none;border:none;color:var(--dim);cursor:pointer;font-size:13px;white-space:nowrap}
.del:hover{color:var(--err)}
.act:hover{color:var(--acc)}
td .act{margin-right:10px}
td.acts{white-space:nowrap;text-align:right}
select.mini{background:transparent;border:1px solid var(--line);color:var(--dim);border-radius:7px;padding:3px 5px;font-size:12px;width:100%}
.bar{display:flex;gap:10px;align-items:center;margin-bottom:14px;flex-wrap:wrap}
h2{font-size:13px;color:var(--dim);margin:0 0 12px;font-weight:500}
pre{background:var(--card2);border:1px solid var(--line);border-radius:10px;padding:12px;font-size:12px;color:var(--dim);max-height:190px;overflow:auto;margin:0}
.empty{color:var(--dim);text-align:center;padding:26px 0;font-size:13px}
.mini-input{background:var(--card2);border:1px solid var(--line);color:var(--txt);border-radius:8px;padding:5px 8px;font-size:12px}
.hm-head{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:14px}
.hm-head input{max-width:420px;flex:1}
.hm-scroll{overflow-x:auto;padding-bottom:4px}
.hm-months{display:grid;grid-auto-flow:column;grid-template-rows:13px;gap:3px;margin-bottom:3px;width:max-content}
.hm-m{font-size:10px;color:var(--dim);white-space:nowrap;overflow:visible}
.hm-grid{display:grid;grid-auto-flow:column;grid-template-rows:repeat(7,13px);gap:3px;width:max-content}
.hm-cell{width:13px;height:13px;border-radius:3px;background:var(--c0);display:block}
.hm-cell[data-l='1']{background:var(--c1)}
.hm-cell[data-l='2']{background:var(--c2)}
.hm-cell[data-l='3']{background:var(--c3)}
.hm-cell[data-l='4']{background:var(--c4)}
.hm-stats{color:var(--dim);font-size:12px;margin-top:12px}
.hm-legend{display:flex;gap:5px;align-items:center;color:var(--dim);font-size:12px;margin-top:8px}
#toast{position:fixed;left:50%;bottom:26px;transform:translate(-50%,20px);background:var(--card2);color:var(--txt);
border:1px solid var(--line);padding:10px 18px;border-radius:10px;font-size:13px;opacity:0;transition:.25s;pointer-events:none}
#toast.show{opacity:1;transform:translate(-50%,0)}
[dir='rtl'] th,[dir='rtl'] td{text-align:right}
[dir='rtl'] td.acts{text-align:left}
</style>
</head>
<body data-theme='dark'>
<div class='wrap'>
  <header>
    <h1>Automation Customize Commit</h1>
    <span class='ver'>V__VERSION__</span>
    <span class='sp'></span>
    <span class='meta' id='nextInfo'></span>
    <span class='chip' id='agentChip'></span>
    <div class='prefs'>
      <select id='langSel' title='language'></select>
      <select id='themeSel'>
        <option value='dark' data-i18n='dark'></option>
        <option value='light' data-i18n='light'></option>
      </select>
      <div class='dots' id='dots'></div>
    </div>
  </header>

  <div class='card'>
    <h2 data-i18n='newTask'></h2>
    <div class='grid'>
      <div class='full'>
        <label data-i18n='repo'></label>
        <input type='text' id='repo' list='repos' data-i18n-ph='repoPh'>
        <datalist id='repos'></datalist>
      </div>
      <div>
        <label data-i18n='at'></label>
        <input type='datetime-local' id='at'>
        <div class='quick'>
          <button data-q='10' data-i18n='q10'></button>
          <button data-q='tonight' data-i18n='qTonight'></button>
          <button data-q='morning' data-i18n='qMorning'></button>
        </div>
      </div>
      <div>
        <label data-i18n='msg'></label>
        <input type='text' id='message'>
      </div>
      <div>
        <label data-i18n='repeat'></label>
        <select id='repeat'>
          <option value='none' data-i18n='rNone'></option>
          <option value='daily' data-i18n='rDaily'></option>
          <option value='weekly' data-i18n='rWeekly'></option>
        </select>
      </div>
      <div>
        <label data-i18n='content'></label>
        <select id='mode'>
          <option value='file' data-i18n='mFile'></option>
          <option value='all' data-i18n='mAll'></option>
          <option value='empty' data-i18n='mEmpty'></option>
        </select>
      </div>
      <div style='grid-column:span 2'>
        <label data-i18n='file'></label>
        <input type='text' id='file' value='commit-log.txt'>
      </div>
    </div>
    <div class='row'>
      <label class='check'><input type='checkbox' id='push' checked><span data-i18n='push'></span></label>
      <label class='check'><input type='checkbox' id='backdate'><span data-i18n='backdate'></span></label>
      <button class='primary' id='add' data-i18n='add'></button>
    </div>
  </div>

  <div class='card'>
    <div class='bar'>
      <h2 style='margin:0' data-i18n='queue'></h2>
      <span class='sp'></span>
      <button class='ghost' id='runNow' data-i18n='runDue'></button>
      <button class='ghost' id='agentBtn'></button>
    </div>
    <table>
      <thead><tr>
        <th style='width:108px' data-i18n='thTime'></th>
        <th style='width:174px' data-i18n='thRepo'></th>
        <th data-i18n='thMsg'></th>
        <th style='width:88px' data-i18n='thRepeat'></th>
        <th style='width:74px' data-i18n='thStatus'></th>
        <th style='width:104px'></th>
      </tr></thead>
      <tbody id='jobs'><tr><td colspan='6' class='empty'></td></tr></tbody>
    </table>
  </div>

  <div class='card'>
    <div class='bar'>
      <h2 style='margin:0' data-i18n='autoTitle'></h2>
      <span class='sp'></span>
      <span class='meta' id='autoState'></span>
      <input type='number' id='autoInterval' min='1' max='3600' step='1' value='30' style='width:78px' class='mini-input'>
      <button class='ghost' id='autoBtn'></button>
    </div>
    <div class='mono' id='autoHint' data-i18n='autoHint' style='margin-top:6px'></div>
  </div>

  <div class='card'>
    <div class='hm-head'>
      <h2 style='margin:0' data-i18n='heat'></h2>
      <input type='text' id='hmRepo' data-i18n-ph='heatPh'>
      <button class='ghost' id='hmRefresh' data-i18n='refresh'></button>
    </div>
    <div class='hm-scroll'>
      <div class='hm-months' id='hmMonths'></div>
      <div class='hm-grid' id='hmGrid'></div>
    </div>
    <div class='hm-stats' id='hmStats'></div>
    <div class='hm-legend'>
      <span data-i18n='less'></span>
      <span class='hm-cell' data-l='0'></span><span class='hm-cell' data-l='1'></span>
      <span class='hm-cell' data-l='2'></span><span class='hm-cell' data-l='3'></span>
      <span class='hm-cell' data-l='4'></span>
      <span data-i18n='more'></span>
    </div>
  </div>

  <div class='card'>
    <h2 data-i18n='log'></h2>
    <pre id='log'></pre>
  </div>
</div>
<div id='toast'></div>

<script>
const I18N = __I18N__;
const LANGS = __LANGS__;
const ACCENTS = ['#4f8cff','#3ecf8e','#ff8a3d','#c084fc','#f472b6','#22d3ee'];
const q = s => document.querySelector(s);
let agentOn = false, nextAt = null;
let lang = localStorage.getItem('lang') || (navigator.language || 'en').slice(0,2);

function resolveLang(){
  if(I18N[lang]) return lang;
  const hit = LANGS.find(p => p[0].slice(0,2) === lang);
  return hit ? hit[0] : 'en';
}
lang = resolveLang();

function t(k){
  const pack = I18N[lang] || I18N.en;
  return pack[k] || I18N.en[k] || k;
}
function fmt(k, vars){
  return t(k).replace(/\{(\w+)\}/g, (m, n) => vars[n] !== undefined ? vars[n] : m);
}

function applyLang(){
  document.documentElement.dir = lang === 'ar' ? 'rtl' : 'ltr';
  document.documentElement.lang = lang;
  document.querySelectorAll('[data-i18n]').forEach(el => { el.textContent = t(el.dataset.i18n); });
  document.querySelectorAll('[data-i18n-ph]').forEach(el => { el.placeholder = t(el.dataset.i18nPh); });
  q('#agentBtn').textContent = agentOn ? t('uninstall') : t('install');
  if(!q('#message').value || q('#message').dataset.auto === '1'){
    q('#message').value = t('msgDefault'); q('#message').dataset.auto = '1';
  }
  if(window._heat) renderHeatmap(window._heat);
  renderAuto();
  tick();
}

function applyTheme(){
  const theme = localStorage.getItem('theme') || 'dark';
  const acc = localStorage.getItem('accent') || ACCENTS[0];
  document.body.dataset.theme = theme;
  document.documentElement.style.setProperty('--acc', acc);
  q('#dots').querySelectorAll('.dot').forEach(d => d.classList.toggle('on', d.dataset.c === acc));
  q('#themeSel').value = theme;
}

function buildControls(){
  q('#langSel').innerHTML = LANGS.map(p =>
    '<option value="'+p[0]+'"'+(p[0]===lang?' selected':'')+'>'+p[1]+'</option>').join('');
  q('#dots').innerHTML = ACCENTS.map(c =>
    '<button class="dot" data-c="'+c+'" style="background:'+c+'"></button>').join('');
  q('#dots').querySelectorAll('.dot').forEach(b => b.onclick = () => {
    localStorage.setItem('accent', b.dataset.c); applyTheme();
  });
}

q('#langSel').onchange = e => {
  lang = e.target.value; localStorage.setItem('lang', lang);
  applyLang(); load();
};
q('#themeSel').onchange = e => { localStorage.setItem('theme', e.target.value); applyTheme(); };

function toast(msg){
  const el = q('#toast');
  el.textContent = msg; el.classList.add('show');
  clearTimeout(window._tt); window._tt = setTimeout(() => el.classList.remove('show'), 2200);
}
function pad(n){ return String(n).padStart(2,'0'); }
function localValue(d){
  return d.getFullYear()+'-'+pad(d.getMonth()+1)+'-'+pad(d.getDate())+'T'+pad(d.getHours())+':'+pad(d.getMinutes());
}
const nf = (opts) => new Intl.DateTimeFormat(lang, opts);
function fmtAt(iso){
  const d = new Date(iso);
  return nf({month:'2-digit', day:'2-digit'}).format(d) + ' ' +
         nf({hour:'2-digit', minute:'2-digit', hour12:false}).format(d);
}
function fmtNum(n){ return new Intl.NumberFormat(lang).format(n); }
function fmtDur(ms){
  const h = Math.floor(ms/3600000), m = Math.floor(ms%3600000/60000), s = Math.floor(ms%60000/1000);
  return (h ? h + t('unitH') + ' ' : '') + pad(m) + t('unitM') + ' ' + pad(s) + t('unitS');
}
function activeMode(){ return q('#mode').value; }
function ymd(d){ return d.getFullYear()+'-'+pad(d.getMonth()+1)+'-'+pad(d.getDate()); }
function level(n){ return !n ? 0 : n < 3 ? 1 : n < 10 ? 2 : n < 50 ? 3 : 4; }

function tick(){
  const el = q('#nextInfo');
  if(!nextAt){ el.textContent = t('nextNone'); return; }
  const ms = new Date(nextAt) - new Date();
  if(ms <= 0){ el.textContent = t('nextOverdue'); return; }
  el.textContent = fmt('nextFmt', {t: fmtAt(nextAt), d: fmtDur(ms)});
}

document.querySelectorAll('.quick button').forEach(b => {
  b.onclick = () => {
    const now = new Date(); let d;
    if(b.dataset.q === '10'){ d = new Date(now.getTime() + 10*60000); }
    else if(b.dataset.q === 'tonight'){ d = new Date(now); d.setHours(23,0,0,0); if(d <= now) d.setDate(d.getDate()+1); }
    else { d = new Date(now); d.setHours(9,0,0,0); d.setDate(d.getDate()+1); }
    q('#at').value = localValue(d);
  };
});
q('#mode').onchange = () => { q('#file').disabled = activeMode() !== 'file'; };

async function api(path, body){
  const opt = body === undefined ? {} : {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)};
  const r = await fetch(path, opt);
  const data = await r.json();
  if(!r.ok) throw new Error(data.error || r.statusText);
  return data;
}

function renderHeatmap(counts){
  window._heat = counts;
  const grid = q('#hmGrid');
  const end = new Date(); end.setHours(0,0,0,0);
  const start = new Date(end); start.setDate(start.getDate() - 370);
  const padDays = start.getDay();
  const cells = [];
  for(let i = 0; i < padDays; i++) cells.push('<span class="hm-cell" style="visibility:hidden"></span>');

  let total = 0, active = 0, run = 0, best = 0, cur = 0;
  for(const d = new Date(start); d <= end; d.setDate(d.getDate()+1)){
    const n = counts[ymd(d)] || 0;
    total += n;
    if(n){ active++; run++; best = Math.max(best, run); } else run = 0;
    cells.push('<span class="hm-cell" data-l="'+level(n)+'" title="'+ymd(d)+' · '+n+'"></span>');
  }
  grid.innerHTML = cells.join('');

  const months = [];
  let prevMonth = -1;
  for(let d = new Date(start); d <= end; d.setDate(d.getDate()+7)){
    const m = d.getMonth();
    months.push(m !== prevMonth ? '<span class="hm-m">'+nf({month:'short'}).format(d)+'</span>'
                                : '<span class="hm-m"></span>');
    prevMonth = m;
  }
  q('#hmMonths').innerHTML = months.join('');
  for(const d = new Date(end); d >= start; d.setDate(d.getDate()-1)){
    if((counts[ymd(d)] || 0) > 0) cur++; else break;
  }
  q('#hmStats').textContent = fmt('stats', {d: fmtNum(371), t: fmtNum(total), a: fmtNum(active),
                                           b: fmtNum(best), c: fmtNum(cur)});
}

async function loadHeatmap(){
  const repo = q('#hmRepo').value.trim();
  if(!repo){ q('#hmStats').textContent = t('heatEmpty'); return; }
  try{
    const d = await api('/api/heatmap?repo=' + encodeURIComponent(repo));
    renderHeatmap(d.days || {});
  }catch(e){ q('#hmStats').textContent = fmt('tFail', {m: e.message}); }
}

async function load(){
  let s;
  try{ s = await api('/api/state'); }
  catch(e){ q('#agentChip').className = 'chip off'; q('#agentChip').textContent = 'offline'; return; }
  agentOn = s.agent;
  const chip = q('#agentChip');
  chip.className = 'chip ' + (s.agent ? 'on' : 'off');
  chip.textContent = s.agent ? t('agentOn') : t('agentOff');
  q('#agentBtn').textContent = s.agent ? t('uninstall') : t('install');

  const repos = [...new Set(s.jobs.map(j => j.repo))];
  q('#repos').innerHTML = repos.map(r => '<option value="'+r+'">').join('');

  window._auto = s.auto || {running: false};
  renderAuto();
  nextAt = s.next ? s.next.at : null;
  tick();

  const tb = q('#jobs');
  if(!s.jobs.length){
    tb.innerHTML = "<tr><td colspan='6' class='empty'>" + t('empty') + "</td></tr>";
  } else {
    tb.innerHTML = s.jobs.map(j => {
      const when = fmtAt(j.at) + (j.backdate ? ' <span class="mono">(' + t('backdated') + ')</span>' : '');
      const ran = j.last_run ? '<div class="mono">' + fmtAt(j.last_run) + '</div>' : '';
      const hint = j.last_error ? '<div class="mono" style="color:var(--err)">' + j.last_error + '</div>' : '';
      const opts = [['none','rNone'],['daily','rDaily'],['weekly','rWeekly']].map(p =>
        '<option value="'+p[0]+'"'+(j.repeat === p[0] ? ' selected' : '')+'>'+t(p[1])+'</option>').join('');
      const local = j.push ? '' : ' <span class="mono">· ' + t('onlyLocal') + '</span>';
      return '<tr><td>'+when+'</td><td class="mono">'+j.repo+'</td>'+
        '<td>'+j.message+local+ran+hint+'</td>'+
        '<td><select class="mini" data-id="'+j.id+'">'+opts+'</select></td>'+
        '<td><span class="st '+j.status+'">'+t('st'+j.status.charAt(0).toUpperCase()+j.status.slice(1))+'</span></td>'+
        '<td class="acts"><button class="act" data-run="'+j.id+'">'+t('actRun')+'</button>'+
        '<button class="del" data-del="'+j.id+'">'+t('actDel')+'</button></td></tr>';
    }).join('');
    tb.querySelectorAll('[data-del]').forEach(b => b.onclick = async () => {
      await api('/api/jobs/delete', {id: b.dataset.del}); toast(t('tDeleted')); load();
    });
    tb.querySelectorAll('[data-run]').forEach(b => b.onclick = async () => {
      try { await api('/api/jobs/run', {id: b.dataset.run}); toast(t('tRan', {n: 1})); load(); }
      catch(e){ toast(fmt('tFail', {m: e.message})); }
    });
    tb.querySelectorAll('select.mini').forEach(sel => sel.onchange = async () => {
      try { await api('/api/jobs/repeat', {id: sel.dataset.id, repeat: sel.value}); toast(t('tRepeat')); load(); }
      catch(e){ toast(fmt('tFail', {m: e.message})); }
    });
  }
  q('#log').textContent = s.log.length ? s.log.join('\n') : t('logEmpty');
}

q('#add').onclick = async () => {
  const mode = activeMode();
  const body = {
    repo: q('#repo').value.trim(),
    at: q('#at').value,
    message: q('#message').value.trim() || t('msgDefault'),
    file: mode === 'file' ? (q('#file').value.trim() || 'commit-log.txt') : null,
    push: q('#push').checked,
    backdate: q('#backdate').checked,
    repeat: q('#repeat').value,
  };
  if(!body.repo) return toast(t('tNeedRepo'));
  if(!body.at) return toast(t('tNeedTime'));
  try{
    await api('/api/jobs', body);
    toast(t('tAdded') + ' ' + fmtAt(body.at));
    load();
  }catch(e){ toast(fmt('tFail', {m: e.message})); }
};

q('#runNow').onclick = async () => {
  try{
    const r = await api('/api/run', {});
    toast(r.count ? fmt('tRan', {n: r.count}) : t('tNone'));
    load();
  }catch(e){ toast(fmt('tFail', {m: e.message})); }
};

q('#agentBtn').onclick = async () => {
  try{
    await api('/api/agent', {action: agentOn ? 'uninstall' : 'install'});
    toast(agentOn ? t('tUninstalled') : t('tInstalled'));
    load();
  }catch(e){ toast(fmt('tFail', {m: e.message})); }
};

q('#hmRefresh').onclick = loadHeatmap;
q('#hmRepo').addEventListener('keydown', e => { if(e.key === 'Enter') loadHeatmap(); });
q('#repo').addEventListener('change', () => { if(!q('#hmRepo').value) q('#hmRepo').value = q('#repo').value.trim(); });

function renderAuto(){
  const a = window._auto || {};
  const on = !!a.running;
  q('#autoState').textContent = on ? fmt('autoRunning', {i: fmtNum(a.interval || 0)}) : t('autoIdle');
  q('#autoBtn').textContent = on ? t('autoStop') : t('autoStart');
  q('#autoBtn').dataset.on = on ? '1' : '0';
  if(on && a.interval) q('#autoInterval').value = a.interval;
}

q('#autoBtn').onclick = async () => {
  const on = !!(window._auto && window._auto.running);
  try{
    if(on){
      await api('/api/auto', {action: 'stop'});
      toast(t('autoIdle'));
    } else {
      const repo = q('#repo').value.trim() || q('#hmRepo').value.trim();
      if(!repo) return toast(t('tNeedRepo'));
      const interval = Math.max(1, Number(q('#autoInterval').value) || 30);
      await api('/api/auto', {action: 'start', repo: repo, interval: interval});
      toast(fmt('autoRunning', {i: fmtNum(interval)}));
    }
    load();
  }catch(e){ toast(fmt('tFail', {m: e.message})); }
};

buildControls();
applyTheme();
applyLang();
q('#hmStats').textContent = t('heatEmpty');
load();
setInterval(load, 3000);
setInterval(tick, 1000);
</script>
</body>
</html>
"""


def render_page() -> bytes:
    return (PAGE.replace("__VERSION__", engine.VERSION)
                .replace("__I18N__", json.dumps(I18N, ensure_ascii=False))
                .replace("__LANGS__", json.dumps(LANGS, ensure_ascii=False))).encode()


AUTO_JSON = "auto.json"


def auto_state() -> dict:
    path = engine.state_dir() / AUTO_JSON
    if not path.exists():
        return {"running": False}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"running": False}
    pid = data.get("pid")
    alive = False
    if pid:
        try:
            os.kill(pid, 0)
            alive = True
        except OSError:
            alive = False
    data["running"] = alive
    return data


def auto_start(repo: str, interval: float) -> dict:
    if auto_state().get("running"):
        raise ValueError("already running")
    repo_path = Path(repo).expanduser().resolve()
    if not (repo_path / ".git").exists():
        raise ValueError(f"{repo_path} 不是 git 仓库")
    if interval < 1:
        raise ValueError("interval must be >= 1 second")
    log = (engine.state_dir() / "auto.out").open("a", encoding="utf-8")
    proc = subprocess.Popen(
        [sys.executable, "-m", "commit_auto.auto", "--repo", str(repo_path),
         "--interval", f"{interval:g}", "--push-every", "10"],
        cwd=str(Path(__file__).resolve().parent.parent), stdout=log, stderr=log, start_new_session=True)
    payload = {"pid": proc.pid, "repo": str(repo_path), "interval": interval}
    (engine.state_dir() / AUTO_JSON).write_text(json.dumps(payload), encoding="utf-8")
    return payload


def auto_stop() -> None:
    state = auto_state()
    pid = state.get("pid")
    if pid:
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            pass
    (engine.state_dir() / AUTO_JSON).unlink(missing_ok=True)


def state_payload() -> dict:
    jobs = sorted(engine.load_jobs(), key=lambda j: j["at"])
    return {
        "version": engine.VERSION,
        "agent": agent.is_installed(),
        "jobs": jobs,
        "next": engine.next_due(jobs),
        "log": engine.tail_log(),
        "auto": auto_state(),
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
            return self._send(200, render_page())
        if self.path == "/api/state":
            return self._send(200, state_payload())
        if self.path.startswith("/api/heatmap"):
            repo = (parse_qs(urlparse(self.path).query).get("repo") or [""])[0]
            try:
                return self._send(200, {"repo": repo, "days": engine.commit_days(repo)})
            except Exception as exc:  # noqa: BLE001 - shown in the UI
                return self._send(400, {"error": str(exc)})
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
            if self.path == "/api/auto":
                action = body.get("action")
                if action == "stop":
                    auto_stop()
                    return self._send(200, {"ok": True, "auto": auto_state()})
                payload = auto_start(body.get("repo", ""), float(body.get("interval", 30)))
                return self._send(200, {"ok": True, "auto": payload})
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

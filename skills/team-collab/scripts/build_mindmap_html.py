# -*- coding: utf-8 -*-
"""build_mindmap_html.py —— 生成「会话思维画布」交互视图（**读段.md 版**：不内嵌文字，运行时现读）。

对话树的一个视图（同 思维导图.md 之于 tree.json，只是交互强）。**文字不再拷进 html**——
html 是个几十 KB 的纯渲染器，运行时 `fetch` 对话树里的 `tree.json`（结构）+ 各节点 `段.md`（文字），
在浏览器里现清洗、现合并、现渲染。链路：真源 →(make_transcript 脱敏)→ 段.md →(浏览器现读)→ 画布。
好处：没有第三份拷贝、段.md 变了刷新即更新。代价：浏览器禁止 file:// 读本地文件，故**要起个小服务**看
（附带生成 serve.py）。

本脚本只把两个**静态文件**写进对话树目录（不读数据）：
  - 思维画布.html   ← 纯渲染器（fetch tree.json + 段.md）
  - serve.py         ← 一行起服务：cd 对话树 && py serve.py → 自动开浏览器

用法：
  python3 build_mindmap_html.py --person Alice                # 写进 <对话树>/
  python3 build_session_tree.py --person Alice --mindmap-html  # 建树时顺带写
查看：  cd <对话树> && python3 serve.py     # 起服务并打开 思维画布.html
"""
import argparse, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
try:
    import _vector_env as ve
except Exception:
    ve = None

HTML = r"""<!doctype html><html lang="zh"><head><meta charset="utf-8">
<title>会话思维画布</title>
<style>
:root{--fg:#1a1a1a;--mut:#8a909a;--sec:#5b6472;--line:#e6e8ec;--blue:#4C7EF3;--sel:#eaf1ff}
*{box-sizing:border-box}
body{margin:0;font-family:-apple-system,"Segoe UI","Microsoft YaHei",system-ui,sans-serif;color:var(--fg);overflow:hidden}
header{padding:10px 16px;border-bottom:1px solid var(--line);display:flex;align-items:center;gap:12px}
header h1{margin:0;font-size:15px;white-space:nowrap}
header p{margin:0;font-size:11.5px;color:var(--sec)}header b{color:var(--blue)}
.spacer{flex:1}
.tgl{border:1px solid var(--line);background:#fff;color:var(--sec);border-radius:8px;padding:6px 11px;font-size:12.5px;cursor:pointer;white-space:nowrap}
.tgl:hover{background:#f4f6f9}.tgl.off{opacity:.45}
.eall{border:1px solid #cfe0ff;background:#eef4ff;color:#2f57c9;border-radius:8px;padding:6px 12px;font-size:12.5px;cursor:pointer;white-space:nowrap}
.eall:hover{background:#e2ecff}
.wrap{display:flex;height:calc(100vh - 50px)}
.side{width:280px;min-width:280px;overflow:auto;border-right:1px solid var(--line);padding:6px;transition:margin-left .12s}
.wrap.side-collapsed .side{margin-left:-281px}
.grp{font-size:12px;font-weight:700;color:var(--sec);padding:10px 8px 4px;position:sticky;top:0;background:#fff;z-index:1}
.grp .cnt{color:var(--mut);font-weight:400}
.it{padding:7px 9px;border-radius:8px;cursor:pointer;border:1px solid transparent}
.it:hover{background:#f4f6f9}.it.on{background:var(--sel);border-color:#cfe0ff}
.it b{font-size:13px}.it .dt{font-size:11px;color:var(--mut);margin-left:6px}
.it .sm{font-size:11px;color:var(--sec);margin-top:2px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.stage{flex:1;position:relative;overflow:hidden;background:#fbfcfd;background-image:radial-gradient(#e3e7ee 1px,transparent 1px);background-size:22px 22px;cursor:grab}
.stage.drag{cursor:grabbing}
#world{position:absolute;left:0;top:0;transform-origin:0 0;--bw:300px}
#edges{position:absolute;left:0;top:0;overflow:visible;pointer-events:none}
.box{position:absolute;width:var(--bw);padding:5px 10px;border-radius:9px;font-size:11.5px;line-height:1.5;cursor:pointer;border:1px solid}
.box .tx{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.box.exp .tx{white-space:normal;overflow-wrap:break-word;max-height:440px;overflow-y:auto;overflow-x:hidden}
.box.exp{z-index:5}
.box .rl{font-weight:700;margin-right:5px}
.box .ts{font-size:9px;color:#aeb4bd;margin-top:3px;padding-top:2px;border-top:1px dashed #eceef2;font-variant-numeric:tabular-nums}
.box .rz{position:absolute;top:0;right:-4px;width:9px;height:100%;cursor:col-resize;z-index:8}
.ndcode{position:absolute;font-size:9px;color:#8892a6;font-family:ui-monospace,Menlo,Consolas,monospace;cursor:pointer;white-space:nowrap;z-index:7}
.ndcode:hover{color:var(--blue)}
.ndcode b{color:#4a5568;font-family:-apple-system,"Microsoft YaHei",system-ui;font-size:9.5px}
.ndcode .cp{color:#c0c6d4}
.journey{width:334px;min-width:334px;border-right:1px solid var(--line);overflow:auto;padding:4px 8px 40px;transition:width .12s,min-width .12s}
.wrap.journey-collapsed .journey{width:0;min-width:0;padding:0;overflow:hidden;border-right:none}
.jhead{font-size:12.5px;font-weight:700;color:var(--sec);padding:8px 6px;position:sticky;top:0;background:#fff;z-index:1}
.jcard{border:1px solid var(--line);border-left:3px solid #cfe0ff;border-radius:8px;padding:6px 9px;margin:5px 0;cursor:pointer;background:#fff}
.jcard:hover{border-left-color:var(--blue);background:#f8fafd}
.jcard.open{border-left-color:var(--blue)}
.jcard .jt{font-size:12px;font-weight:700}
.jcard .jt .ar{color:var(--mut);font-weight:400;font-size:10px;margin-left:5px}
.jcard .js{font-size:11px;color:var(--sec);margin-top:2px;line-height:1.5;overflow:hidden;text-overflow:ellipsis;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical}
.jcard.open .js{-webkit-line-clamp:unset}
.jcard .jmem{margin-top:7px;display:none}.jcard.open .jmem{display:block}
.jsec{margin:7px 0}
.jsec .lb{font-size:11px;font-weight:700;padding:2px 8px;border-radius:6px;display:inline-block;margin-bottom:4px}
.jsec .bd{font-size:11.5px;color:#2b2f36;line-height:1.6;white-space:pre-wrap;word-break:break-word}
.lb-main{background:#eef4ff;color:#2f57c9}.lb-find{background:#e6f6ef;color:#1d8a5f}.lb-pit{background:#fdecec;color:#c0392b}.lb-mot{background:#f3eefe;color:#6b46c9}
.mp-empty{color:var(--mut);font-size:11.5px;margin-top:6px}
.box.u{background:#eef4ff;border-color:#cfe0ff}.box.u .rl{color:#2f57c9}
.box.a{background:#f4f5f7;border-color:#e3e6ea}.box.a .rl{color:#7a828e}
.box.root{width:154px!important;background:var(--blue);border-color:var(--blue);color:#fff;font-weight:700;font-size:13px;text-align:center}
.box.root .tx{white-space:nowrap}
.box.bhead{border-left:3px solid var(--blue)!important}
.bbadge{display:inline-block;background:var(--blue);color:#fff;font-size:9px;font-weight:700;border-radius:5px;padding:0 5px;margin-right:4px;vertical-align:1px}
.bbadge.cont{background:#7a828e}
.ndcode .src{border-radius:4px;padding:0 4px;font-size:8px;font-weight:700;font-family:-apple-system,"Microsoft YaHei",system-ui}
.src-cx{background:#fdf1e3;color:#b5761e}.src-cu{background:#eef0ff;color:#5a5ad6}
.chip.contchip{background:#f2f3f5;border-color:#d6dae1;color:#6b7280;border-style:dashed}
.rd{background:#eef0f3;color:#9aa0ac;border-radius:5px;padding:0 4px;font-size:10px;white-space:nowrap}
.ndm{color:#aab0bc;font-size:8.5px}.ndm b2{color:#7b8393;font-weight:700}
.tpill{background:#f0f2f5;color:#8b93a1;border-radius:5px;padding:0 5px;font-size:9.5px;white-space:nowrap}
.emptx{color:#b0b6c0;font-style:italic}.box.empt{background:#fafbfc;border-style:dashed}
.box.cbox{border-color:#e0a03a!important;background:#fdf6ea;box-shadow:0 0 0 1px #e0a03a55}   /* compact 续接点:琥珀框(主干里,非分支) */
.clab{display:inline-block;background:#e0a03a;color:#fff;font-size:9px;font-weight:700;border-radius:5px;padding:0 5px;margin-right:4px;vertical-align:1px}
.chip{position:absolute;padding:4px 10px;border-radius:11px;font-size:10.5px;background:#eef4ff;border:1px solid #cfe0ff;color:#3358c4;cursor:pointer;white-space:nowrap}
.fold{position:absolute;width:15px;height:15px;border-radius:50%;background:#fff;border:1px solid var(--blue);color:var(--blue);font-size:11px;line-height:13px;text-align:center;cursor:pointer;z-index:6}
.bar{position:absolute;right:14px;bottom:14px;display:flex;gap:6px;background:#fff;border:1px solid var(--line);border-radius:10px;padding:4px;box-shadow:0 2px 8px rgba(0,0,0,.06)}
.bar button{width:30px;height:28px;border:none;background:#fff;border-radius:7px;cursor:pointer;font-size:15px;color:var(--sec)}.bar button:hover{background:#f1f3f7}
.hint{position:absolute;left:14px;top:12px;font-size:11.5px;color:var(--mut);background:#fff;border:1px solid var(--line);border-radius:8px;padding:5px 9px;pointer-events:none}
.q{border:1px solid var(--line);border-radius:8px;padding:5px 10px;font-size:12.5px;width:160px;outline:none}.q:focus{border-color:var(--blue)}
.it.hide{display:none}
.box.hit{outline:2px solid #f4a63a;outline-offset:1px}
</style></head><body>
<header>
<button class="tgl" id="sideT">◀ 列表</button>
<button class="tgl off" id="jT">📖 研究历程</button>
<h1>会话思维画布 <span id="cnt" style="font-weight:400;color:var(--mut);font-size:13px"></span></h1>
<p><b>↓</b>接着的指令/回复 <b>→</b>分支 · 蓝=指令 灰=回复 · 现读段.md · 拖拽·缩放·点框看全文·拖右边框调宽</p>
<div class="spacer"></div>
<input class="q" id="q" placeholder="🔍 搜对话 / 内容" autocomplete="off">
<button class="tgl" id="tsT">🕐 时间</button>
<button class="eall" id="eall">▤ 全部展开</button>
</header>
<div class="wrap journey-collapsed" id="wrap">
  <div class="side" id="side"></div>
  <div class="journey" id="journey"></div>
  <div class="stage" id="stage">
    <div class="hint" id="hint">加载 tree.json…</div>
    <div id="world"><svg id="edges"></svg></div>
    <div class="bar"><button id="zi">＋</button><button id="zo">－</button><button id="zf">⊡</button></div>
  </div>
</div>
<script>
let NBD={},NBA={},KIDS={},ROOTS=[],TREES={},CACHE={},NODE_COMPACT={},NODE_FAILED={};
let cur=null,collapsed=new Set(),expanded=new Set(),allExp=false,showTs=true,boxW=300,curAbort=null;
let view={tx:40,ty:70,k:1},drag=null,dragMoved=false,rz=null,boxEls=[];
const world=document.getElementById('world'),stage=document.getElementById('stage'),hint=document.getElementById('hint'),edges=document.getElementById('edges'),side=document.getElementById('side');
function esc(s){return (s||'').replace(/[&<>]/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[m]));}
function prev20(t){return t.length>200?t.slice(0,200)+'…':t;}   // 不再硬砍20字：CSS按框宽省略，拖宽即多显
function fmtN(n){return n>=1000?(n/1000).toFixed(n>=10000?0:1)+'k':(''+n);}
function fmtDur(t0,t1){if(!t0||!t1)return '';const a=new Date(t0.replace(' ','T')),b=new Date(t1.replace(' ','T'));if(isNaN(a)||isNaN(b)||b<a)return '';const m=Math.round((b-a)/6e4);if(m<60)return m+'分';const h=m/60;if(h<24)return (h>=10?Math.round(h):h.toFixed(1))+'时';return Math.round(h/24)+'天';}
function fmtTx(s){return s.replace(/\[已脱敏[:：]([^\]]*)\]/g,'<span class="rd">🔒$1</span>');}   // 脱敏标记→淡色pill
function fmtTools(s){return s.replace(/(?:⟦T:[^⟧]*⟧\s*)+/g,m=>{const ns=[...m.matchAll(/⟦T:([^⟧]*)⟧/g)].map(x=>x[1]),u=[...new Set(ns)];return '<span class="tpill">🔧 '+ns.length+' 步'+(u.length&&u.length<=3?'·'+u.join('·'):'')+'</span> ';});}  // 连续工具调用→一个折叠 pill
function subCount(dir){let c=1;for(const k of (KIDS[dir]||[]))c+=subCount(k);return c;}
function cnt(t){return t.s.length+t.b.reduce((a,c)=>a+cnt(c[1]),0);}
function isExp(id){return allExp!==expanded.has(id);}
function applyT(){world.style.transform=`translate(${view.tx}px,${view.ty}px) scale(${view.k})`;}
function fit(){   // 真·zoom-to-fit：读 render() 已算好的 world 尺寸，等比缩放并居中
  const ww=world.offsetWidth||1,wh=world.offsetHeight||1,vw=stage.clientWidth||1,vh=stage.clientHeight||1;
  const k=Math.min(2.5,Math.max(.15,Math.min((vw-48)/ww,(vh-48)/wh)));
  view.k=k;view.tx=Math.max(12,(vw-ww*k)/2);view.ty=20;applyT();}
function byNum(a,b){const na=parseInt((a.alias.match(/\d+/)||[9999])[0]),nb=parseInt((b.alias.match(/\d+/)||[9999])[0]);return na-nb;}
// ── 从段.md现抽（对应 Python 的 raw_turns/clean/coalesce/build）──
const COMPACT=['This session is being continued','ran out of context','Caveat: The messages below'];
function parseTurns(md){
  const p=md.split('\n---\n'),body=p.length>1?p.slice(1).join('\n---\n'):md,lines=body.split('\n'),out=[];let i=0;
  const hdr=/^### \[(.*?)\] (🧑|🤖) /;
  while(i<lines.length){const m=lines[i].match(hdr);
    if(m){const role=m[2]==='🧑'?'u':'a',ts=m[1],c=[];let j=i+1;
      while(j<lines.length&&!lines[j].startsWith('### ')){c.push(lines[j]);j++;}
      out.push([role,ts,c.join(' ')]);i=j;}else i++;}
  return out;
}
function clean(t){
  t=t.replace(/⟨工具结果[\s\S]*?⟩/g,' ')                                       // 工具结果=噪声,删
     .replace(/<details>[\s\S]*?⟨工具调用\s*·\s*([^⟩<]+)⟩[\s\S]*?<\/details>/g,' ⟦T:$1⟧ ')  // 工具调用→抽工具名占位(不再整段删)
     .replace(/<details>[\s\S]*?<\/details>/g,' ').replace(/\[工具:([^\]]*)\]/g,' ⟦T:$1⟧ ')
     .replace(/<[^>]+>/g,' ').replace(/\s+/g,' ').trim();
  if(!t)return null;
  const h=t.slice(0,220);
  if(COMPACT.some(k=>h.includes(k)))return null;
  if(t.startsWith('[Request interrupted'))return null;
  if(t.includes('toolu_')||t.includes('tool_use_id')||t.includes('toolUseResult'))return null;
  const f=t.split(' ')[0]||'';
  if(/^[0-9a-fA-F]{10,}$/.test(f)&&t.length<70)return null;
  if(/^[0-9a-z]{6,}$/.test(f)&&/\d/.test(f)&&/[a-z]/.test(f)&&t.length<70)return null;
  if(/^[0-9a-fA-F_\- ]{6,60}$/.test(t))return null;
  return t;
}
function cleanKeep(t){return (t||'').replace(/⟨工具结果[\s\S]*?⟩/g,' ').replace(/<[^>]+>/g,' ').replace(/\s+/g,' ').trim();}  // 保留 compact 摘要:去噪但不判空不截
function coalesce(turns){const m=[];for(const [role,ts,txt] of turns){
  const cx=/^\s*This session is being continued/.test(txt||'');      // compact 摘要(以此开头,非讨论中提及):保留、强制作🧑、不与邻轮合并
  let c;if(cx){c=cleanKeep(txt)||'（compact 续接摘要）';}else{c=clean(txt);if(!c)continue;}
  if(!cx&&m.length&&m[m.length-1][0]===role&&!m[m.length-1][3])m[m.length-1][1]+=' '+c;
  else m.push([cx?'u':role,c,ts,cx]);   // 第4位=compact 标记；compact 强制 🧑
}return m;}
function cmpChild(a,b){const ta=(NBD[a]||{}).t0||'',tb=(NBD[b]||{}).t0||'';if(ta<tb)return -1;if(ta>tb)return 1;return a<b?-1:(a>b?1:0);}  // 稳定全序：相等按 dir 兜底(修破损比较器)
function buildTree(dir){
  const spine=[],branches=[];let d=dir;
  while(d){
    const turns=CACHE[d]||[],tool=(NBD[d]||{}).source_tool||'Claude Code';
    if(turns.length===0)spine.push({r:'a',t:'',ts:'',tool:tool,nd:d,empty:true});   // 空节点留占位框→不消失、子树不被丢
    else turns.forEach((x,i)=>{const o={r:x[0],t:x[1],ts:x[2],tool:tool,cx:x[3]};if(i===0)o.nd=d;spine.push(o);});   // cx=compact摘要标记；首 turn 记 nd
    const last=spine.length-1;
    const ch=(KIDS[d]||[]).slice().sort(cmpChild);
    const ps=new Set((NBD[d]||{}).sessions||[]);
    let mi=ch.findIndex(c=>NODE_COMPACT[c]);                            // 主线：① compact 续接优先并进主干(连续,不分叉)
    if(mi<0)mi=ch.findIndex(c=>((NBD[c]||{}).sessions||[]).some(s=>ps.has(s)));  // ② 同 session 续接，③ 最早(cmpChild)
    const main=mi>=0?ch[mi]:ch[0];
    for(const o of ch)if(o!==main)branches.push([Math.max(last,0),buildTree(o)]);   // 只有真 fork 才成分支
    d=main||null;
  }
  return {s:spine,b:branches};
}
function subtreeDirs(dir){const out=[dir];for(const c of (KIDS[dir]||[]))out.push(...subtreeDirs(c));return out;}
function seedCollapse(t,path,depth){if(!t)return;const wide=t.b.length>=4;t.b.forEach((br,bi)=>{const bp=path+'.b'+bi;if(depth>=2||wide)collapsed.add(bp);seedCollapse(br[1],bp,depth+1);});}  // 默认折叠：深(≥2层)或宽(同点≥4支)→ 消初始过载
// ── 渲染 ──
function render(){
  const T=TREES[cur];if(!T)return;
  [...world.querySelectorAll('.box,.chip,.fold,.ndcode')].forEach(e=>e.remove());
  edges.innerHTML='';boxEls=[];
  const renderedNodes=new Set();   // 一致性 gate：渲染覆盖的节点集，末尾与 tree.json 子树对比
  const COLW=boxW+24;world.style.setProperty('--bw',boxW+'px');
  const colY={};let laneMax=0;   // colY=每列下一个空闲y;laneMax=车道分配器:每条分支独占一列(不再共列堆叠)
  const rb=document.createElement('div');rb.className='box root';rb.innerHTML='<span class="tx">'+esc(cur)+'</span>';rb.style.left='0px';rb.style.top='0px';world.appendChild(rb);
  const rh=rb.offsetHeight;boxEls.push({el:rb,col:0});colY[0]=rh+13;
  function box(turn,id,col,yy,bhead){
    if(turn.nd)renderedNodes.add(turn.nd);   // 一致性统计：记下渲染覆盖的节点
    const ex=isExp(id);const el=document.createElement('div');el.className='box '+turn.r+(ex?' exp':'')+(bhead?' bhead':'')+(turn.empty?' empt':'')+(turn.cx?' cbox':'');el.dataset.id=id;
    const badge=bhead?'<span class="bbadge'+(bhead.kind==='cont'?' cont':'')+'">'+(bhead.kind==='cont'?'⟳ ':'⑂ ')+esc(bhead.name)+(bhead.aiFirst?'·续':'')+(bhead.xtool?'·⌥'+esc(bhead.xtool):'')+'</span>':'';
    const clab=turn.cx?'<span class="clab">⟳ compact 续接</span> ':'';   // compact 点标记(主干里换色框)
    const body=turn.empty?'<span class="emptx">（'+(NODE_FAILED[turn.nd]?'加载失败·刷新重试':'无可显示内容·中断/压缩/仅工具轮')+'）</span>':fmtTools(fmtTx(esc(ex?turn.t:prev20(turn.t))));
    el.innerHTML='<div class="rz"></div><div class="tx">'+badge+'<span class="rl">'+(turn.r==='u'?'我':'AI')+'</span>'+clab+body+'</div>'+(showTs&&turn.ts?'<div class="ts">'+esc(turn.ts)+'</div>':'');
    el.style.left=(col*COLW)+'px';el.style.top=yy+'px';world.appendChild(el);boxEls.push({el:el,col:col});
    if(turn.nd){const n=NBD[turn.nd]||{};const ss=n.sessions||[];const sid=ss[0]||'';const tool=n.source_tool||'Claude Code';
      const meta=[];if(n.n_records)meta.push(fmtN(n.n_records)+'轮');const dr=fmtDur(n.t0,n.t1);if(dr)meta.push(dr);if(ss.length>1)meta.push('+'+(ss.length-1)+'会话');
      const src=tool!=='Claude Code'?' <span class="src src-'+(tool==='Codex'?'cx':'cu')+'">'+esc(tool)+'</span>':'';   // 跨源节点标来源工具
      const lab=document.createElement('div');lab.className='ndcode';lab.dataset.sid=sid;lab.title='点击复制会话编号 session-id（把它报给智能体即可"生成续接包"）';
      lab.innerHTML='<b>'+esc((n.alias||'').split('-').pop())+'</b>'+src+' '+esc(sid)+' <span class="cp">⧉复制</span>'+(meta.length?' <span class="ndm">'+esc(meta.join(' · '))+'</span>':'');
      lab.style.left=(col*COLW)+'px';lab.style.top=(yy-13)+'px';world.appendChild(lab);}
    return el.offsetHeight;
  }
  function vline(col,y1,y2){edges.insertAdjacentHTML('beforeend',`<path d="M${col*COLW+9},${y1} L${col*COLW+9},${y2}" stroke="#c9d3e6" stroke-width="1.5" fill="none"/>`);}
  function bconn(fx,fy,tx,ty,cont){const mx=fx+9,c=cont?'#9aa0ac':'#4C7EF3',da=cont?' stroke-dasharray="4 3"':'';edges.insertAdjacentHTML('beforeend',`<path d="M${mx},${fy} L${mx},${ty} L${tx},${ty}" stroke="${c}" stroke-width="2.6" fill="none"${da}/><circle cx="${mx}" cy="${fy}" r="3.8" fill="${c}"/>`);}
  // 主线先连续铺完（col 只随本段指令推进 y，不因分支而空等），再把分支放到右侧列（各列自己的 colY 防重叠）
  function walk(t,col,startY,forkX,forkYc,path,bmeta){
    let y=Math.max(startY,colY[col]||0);const pos=[];let firstYc=null,prevBottom=null;
    t.s.forEach((turn,i)=>{
      const id=path+'/'+i;const h=box(turn,id,col,y,(i===0?bmeta:null));const yc=y+h/2;pos[i]={y:y,yc:yc,bottom:y+h};
      if(prevBottom!==null)vline(col,prevBottom,y);
      if(firstYc===null)firstYc=yc;prevBottom=y+h;y=y+h+9;
    });
    colY[col]=y;
    if(forkYc!==null&&firstYc!==null)bconn(forkX,forkYc,col*COLW,firstYc,bmeta&&bmeta.kind==='cont');
    const spineTool=(t.s[0]||{}).tool||'Claude Code';   // 本 spine 来源工具 → 判异源 fork
    t.b.forEach((br,bi)=>{
      const ai=Math.min(br[0],pos.length-1);const fp=pos[ai];if(!fp)return;const bp=path+'.b'+bi;
      const b0=br[1].s&&br[1].s[0],bnd=b0&&b0.nd;
      const bname=bnd?((NBD[bnd].alias||'').split('-').pop()):('分支'+(bi+1));
      const btool=(b0&&b0.tool)||'Claude Code';
      const bm={name:bname,aiFirst:!!(b0&&b0.r==='a'),kind:NODE_COMPACT[bnd]?'cont':'fork',xtool:btool!==spineTool?btool:null};   // cont=段.md首轮是压缩摘要(自动续接)；否则=fork
      const gl=(bm.kind==='cont'?'⟳ ':'⑂ ')+bname+(bm.xtool?' ·⌥'+bm.xtool:'');
      const bcol=++laneMax;   // 每条分支独占一条车道(列),从分叉点岔到自己的列,绝不共列堆叠
      if(collapsed.has(bp)){
        if(bnd)subtreeDirs(bnd).forEach(x=>renderedNodes.add(x));   // 折叠进 chip 的子树节点算"已覆盖"(非丢弃)
        const cy=fp.y;const chip=document.createElement('div');chip.className='chip'+(bm.kind==='cont'?' contchip':'');chip.dataset.exp=bp;chip.textContent=gl+' · '+cnt(br[1])+'条';chip.style.left=(bcol*COLW)+'px';chip.style.top=cy+'px';world.appendChild(chip);
        const chh=chip.offsetHeight;colY[bcol]=cy+chh+9;bconn(col*COLW,fp.yc,bcol*COLW,cy+chh/2,bm.kind==='cont');
      }else{
        const bfy=walk(br[1],bcol,fp.y,col*COLW,fp.yc,bp,bm);   // 分支画进自己的列 bcol
        const fold=document.createElement('div');fold.className='fold';fold.dataset.fold=bp;fold.textContent='−';fold.style.left=(bcol*COLW-14)+'px';fold.style.top=((bfy||fp.y)-7)+'px';world.appendChild(fold);
      }
    });
    return firstYc;
  }
  vline(0,rh,colY[0]);
  walk(T,0,colY[0],0,null,'r');
  world.style.width=(laneMax*COLW+boxW+80)+'px';   // 车道数决定宽度
  world.style.height=(Math.max(0,...Object.values(colY))+80)+'px';
  applyT();hint.textContent=cur+' · '+T.s.length+'+ 轮';
  const expect=subtreeDirs((NBA[cur]||{}).dir||'').length,got=renderedNodes.size;   // 一致性 gate：渲染节点集(含折叠chip子树)应==tree.json 子树
  if(got<expect)console.warn('[思维画布] 一致性告警：对话「'+cur+'」应覆盖 '+expect+' 节点，实际 '+got+'（缺 '+(expect-got)+'），可能有节点被静默丢弃');
}
world.addEventListener('click',e=>{
  const nc=e.target.closest('.ndcode');
  if(nc){e.stopPropagation();const sid=nc.dataset.sid;const cp=nc.querySelector('.cp');
    if(!sid){if(cp){cp.textContent='无 sid';setTimeout(()=>{cp.textContent='⧉复制';},1200);}return;}
    const done=ok=>{if(cp){cp.textContent=ok?'✓已复制':'✗ 手动选中';setTimeout(()=>{cp.textContent='⧉复制';},ok?1200:1800);}};
    if(navigator.clipboard&&navigator.clipboard.writeText){navigator.clipboard.writeText(sid).then(()=>done(1),()=>done(0));}else{done(0);}   // 只有真成功才显✓
    return;}
  const f=e.target.closest('.fold,.chip');
  if(f){const p=f.dataset.fold||f.dataset.exp;collapsed.has(p)?collapsed.delete(p):collapsed.add(p);render();return;}
  if(e.target.classList.contains('rz'))return;
  if(window.getSelection&&String(window.getSelection()).length)return;   // 正在选中文字→不切换展开，放行复制
  const b=e.target.closest('.box:not(.root)');
  if(b&&!dragMoved){const id=b.dataset.id;expanded.has(id)?expanded.delete(id):expanded.add(id);render();}
});
world.addEventListener('mousedown',e=>{if(e.target.classList.contains('rz')){e.stopPropagation();rz={x:e.clientX,w:boxW};edges.style.opacity=0;}});
stage.addEventListener('mousedown',e=>{if(rz)return;if(e.target.closest('.box.exp'))return;drag={x:e.clientX,y:e.clientY,tx:view.tx,ty:view.ty};dragMoved=false;stage.classList.add('drag');});   // 展开框内不启动平移→放行文本选择
window.addEventListener('mousemove',e=>{
  if(rz){boxW=Math.max(150,Math.min(820,rz.w+(e.clientX-rz.x)/view.k));const CW=boxW+24;world.style.setProperty('--bw',boxW+'px');boxEls.forEach(b=>b.el.style.left=(b.col*CW)+'px');return;}
  if(!drag)return;const dx=e.clientX-drag.x,dy=e.clientY-drag.y;if(Math.abs(dx)+Math.abs(dy)>4)dragMoved=true;view.tx=drag.tx+dx;view.ty=drag.ty+dy;applyT();
});
window.addEventListener('mouseup',()=>{if(rz){rz=null;edges.style.opacity=1;render();}drag=null;stage.classList.remove('drag');setTimeout(()=>dragMoved=false,0);});
stage.addEventListener('wheel',e=>{if(e.target.closest('.box.exp')){return;}e.preventDefault();const r=stage.getBoundingClientRect();const mx=e.clientX-r.left,my=e.clientY-r.top;const f=e.deltaY<0?1.12:1/1.12;const k2=Math.min(2.5,Math.max(.15,view.k*f));view.tx=mx-(mx-view.tx)*(k2/view.k);view.ty=my-(my-view.ty)*(k2/view.k);view.k=k2;applyT();},{passive:false});
function zoomBy(f){const cx=stage.clientWidth/2,cy=stage.clientHeight/2,k2=Math.min(2.5,Math.max(.15,view.k*f));view.tx=cx-(cx-view.tx)*(k2/view.k);view.ty=cy-(cy-view.ty)*(k2/view.k);view.k=k2;applyT();}
document.getElementById('zi').onclick=()=>zoomBy(1.2);
document.getElementById('zo').onclick=()=>zoomBy(1/1.2);
document.getElementById('zf').onclick=fit;
document.getElementById('eall').onclick=function(){allExp=!allExp;expanded.clear();this.textContent=allExp?'▤ 全部收起':'▤ 全部展开';render();};
document.getElementById('tsT').onclick=function(){showTs=!showTs;this.classList.toggle('off',!showTs);render();};
document.getElementById('sideT').onclick=function(){const w=document.getElementById('wrap');const c=w.classList.toggle('side-collapsed');this.textContent=c?'▶ 列表':'◀ 列表';};
// ── 节点记忆（研究历程 + 动机，现读 .md，结构化显示）──
const MEMCACHE={};
function section(md,names){for(const nm of names){const re=new RegExp('##\\s*'+nm.replace(/[.*+?^${}()|[\]\\\\/]/g,'\\$&')+'([\\s\\S]*?)(?=\\n##\\s|$)');const m=md.match(re);if(m&&m[1].trim())return m[1].trim();}return '';}
function parseMem(rh,dj){
  const sm=(rh.match(/>\s*摘要[:：](.*)/)||[])[1]||'';
  return {sum:sm.trim(),
    main:section(rh,['主线']),
    find:section(rh,['关键转向 / 发现','关键转向/发现','关键转向','发现']),
    pit:section(rh,['踩坑 / 修正','踩坑/修正','踩坑']),
    mot:section(dj,['关键决策与动机','关键决策','决策与动机'])};
}
async function fetchMem(nd){
  if(MEMCACHE[nd])return MEMCACHE[nd];
  async function g(f){try{const r=await fetch(encodeURI(nd+'/'+f));return r.ok?await r.text():'';}catch(e){return '';}}
  const rd=await Promise.all([g('研究历程.md'),g('动机日志.md')]);
  const m=parseMem(rd[0],rd[1]);MEMCACHE[nd]=m;return m;
}
// 研究历程栏：把选中会话的节点树画成缩进的记忆卡（摘要恒有；点开→现读 研究历程.md/动机日志.md 出主线/发现/踩坑/动机）
function renderJourney(alias){
  const jc=document.getElementById('journey');const rootDir=(NBA[alias]||{}).dir;if(!rootDir){jc.innerHTML='';return;}
  let h='<div class="jhead">📖 研究历程 · '+esc(alias)+'</div>';
  function walk(dir,depth){
    const n=NBD[dir];if(!n)return;
    const seg=(n.alias||'').split('-').pop();
    const sm=esc((n['摘要']||n.auto_summary||'').replace(/\s+/g,' ').trim());
    h+='<div class="jcard" data-nd="'+esc(dir)+'" style="margin-left:'+(depth*15)+'px"><div class="jt">'+esc(seg)+(depth>0?'<span class="ar">↳ 分支</span>':'')+'</div><div class="js">'+(sm||'（无摘要）')+'</div><div class="jmem"></div></div>';
    (KIDS[dir]||[]).slice().sort(cmpChild).forEach(c=>walk(c,depth+1));
  }
  walk(rootDir,0);jc.innerHTML=h;
  jc.querySelectorAll('.jcard').forEach(el=>el.onclick=()=>toggleJCard(el));
}
async function toggleJCard(el){
  const open=el.classList.toggle('open');const mem=el.querySelector('.jmem');
  if(open&&!mem.dataset.loaded){
    mem.innerHTML='<div class="mp-empty">读取中…</div>';mem.dataset.loaded='1';
    const m=await fetchMem(el.dataset.nd);
    const secs=[['主线','lb-main',m.main],['关键转向 / 发现','lb-find',m.find],['踩坑 / 修正','lb-pit',m.pit],['动机（为什么）','lb-mot',m.mot]];
    let h='',any=false;for(const s of secs){if(!s[2])continue;any=true;h+='<div class="jsec"><span class="lb '+s[1]+'">'+s[0]+'</span><div class="bd">'+esc(s[2])+'</div></div>';}
    mem.innerHTML=any?h:'<div class="mp-empty">这个节点的研究历程/动机还没补写（待补）。</div>';
  }
}
document.getElementById('jT').onclick=function(){const c=document.getElementById('wrap').classList.toggle('journey-collapsed');this.classList.toggle('off',c);};
function buildList(){
  const order={'Cursor':0,'Codex':1,'Claude Code':2},lab={'Cursor':'Cursor 时期','Codex':'Codex 时期','Claude Code':'Claude Code'},groups={};
  for(const n of ROOTS){const t=n.source_tool||'Claude Code';(groups[t]=groups[t]||[]).push(n);}
  let h='';
  for(const tool of Object.keys(groups).sort((a,b)=>((order[a]??9)-(order[b]??9)))){
    h+=`<div class="grp">${lab[tool]||tool} <span class="cnt">${groups[tool].length}</span></div>`;
    for(const n of groups[tool].sort(byNum)){
      const nn=subCount(n.dir),dr=fmtDur(n.t0,n.t1),sm=(n['摘要']||'').replace(/\s+/g,' ').trim();
      const meta=[(n.t0||'').slice(0,10),nn+'节点',dr].filter(Boolean).join(' · ');
      h+=`<div class="it" data-a="${esc(n.alias)}"><b>${esc(n.alias)}</b> <span class="dt">${esc(meta)}</span><div class="sm" title="${esc(sm)}">${esc(sm.slice(0,44))}</div></div>`;
    }
  }
  side.innerHTML=h;
  side.querySelectorAll('.it').forEach(e=>e.onclick=()=>show(e.dataset.a));
}
async function ensureTree(alias,sig){
  if(TREES[alias])return;
  const rootDir=NBA[alias].dir,dirs=subtreeDirs(rootDir);
  await Promise.all(dirs.map(async d=>{
    if(CACHE[d]!==undefined)return;
    try{const r=await fetch(encodeURI(d+'/段.md'),sig?{signal:sig}:undefined);if(r.ok){const rw=parseTurns(await r.text());NODE_COMPACT[d]=rw.length>0&&COMPACT.some(k=>(rw[0][2]||'').slice(0,240).includes(k));CACHE[d]=coalesce(rw);}else{CACHE[d]=[];NODE_FAILED[d]=true;}}catch(e){if(!sig||e.name!=='AbortError'){CACHE[d]=[];NODE_FAILED[d]=true;}}
  }));
  if(sig&&sig.aborted)return;
  TREES[alias]=buildTree(rootDir);
}
async function show(a){
  if(curAbort)curAbort.abort();curAbort=new AbortController();const sig=curAbort.signal;   // 切换对话→取消上一条在途大文件请求
  cur=a;expanded.clear();collapsed=new Set();allExp=false;document.getElementById('eall').textContent='▤ 全部展开';
  try{history.replaceState(null,'','#c='+encodeURIComponent(a));}catch(e){}   // 深链：URL 承载当前对话，刷新/分享可回到
  hint.textContent='加载 '+a+' 的段.md…';
  side.querySelectorAll('.it').forEach(e=>e.classList.toggle('on',e.dataset.a===a));
  renderJourney(a);          // 研究历程栏（用 tree.json 结构即可，卡片点开才现读 .md）
  await ensureTree(a,sig);if(sig.aborted)return;seedCollapse(TREES[a],'r',1);render();fit();   // 深/宽分支默认折叠→再 render 定尺寸→fit 居中
}
async function boot(){
  try{
    const tj=await (await fetch('tree.json')).json();
    for(const n of tj['节点']){NBD[n.dir]=n;NBA[n.alias]=n;if(n.parent_dir)(KIDS[n.parent_dir]=KIDS[n.parent_dir]||[]).push(n.dir);}
    ROOTS=tj['节点'].filter(n=>!n.parent_dir);
    document.getElementById('cnt').textContent=ROOTS.length+' 条';
    if(!ROOTS.length){hint.textContent='该对话树暂无对话（tree.json 里没有根节点）。';return;}   // 空树≠读取失败
    buildList();
    const cc=ROOTS.filter(n=>(n.source_tool||'Claude Code')==='Claude Code').sort(byNum);
    const hc=decodeURIComponent(((location.hash||'').match(/c=([^&]+)/)||[])[1]||'');   // 深链：优先按 URL #c=<对话> 打开
    show(hc&&NBA[hc]?hc:(cc[0]||ROOTS[0]).alias);
  }catch(e){hint.textContent='读 tree.json 失败：'+e+'（是否用 serve.py 起了服务？file:// 直接打开会失败）';}
}
// ── 搜索（左栏即时过滤 + 当前对话内命中高亮并居中）+ 深链回退 ──
document.getElementById('q').addEventListener('input',function(){
  const q=this.value.trim().toLowerCase();
  side.querySelectorAll('.it').forEach(e=>e.classList.toggle('hide',!!q&&!e.textContent.toLowerCase().includes(q)));
  let first=null;
  world.querySelectorAll('.box:not(.root)').forEach(b=>{const hit=!!q&&b.textContent.toLowerCase().includes(q);b.classList.toggle('hit',hit);if(hit&&!first)first=b;});
  if(first){const L=parseFloat(first.style.left),T=parseFloat(first.style.top);view.tx=stage.clientWidth/2-L*view.k;view.ty=stage.clientHeight/3-T*view.k;applyT();}
});
document.getElementById('q').addEventListener('keydown',e=>{if(e.key==='Escape'){e.target.value='';e.target.dispatchEvent(new Event('input'));}});
window.addEventListener('hashchange',()=>{const h=decodeURIComponent(((location.hash||'').match(/c=([^&]+)/)||[])[1]||'');if(h&&NBA[h]&&h!==cur)show(h);});
boot();
</script></body></html>"""

SERVE = r'''# -*- coding: utf-8 -*-
"""起一个只读小服务，供 思维画布.html 现读 tree.json + 段.md。用法：cd <对话树> && python serve.py"""
import http.server, socketserver, os, sys, webbrowser
os.chdir(os.path.dirname(os.path.abspath(__file__)))   # 服务本目录（对话树）
class H(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store"); super().end_headers()
    def guess_type(self, path):
        t = super().guess_type(path)
        return (t + "; charset=utf-8") if (t and t.startswith("text")) else t
    def log_message(self, *a): pass
port = 8770
for p in range(8770, 8790):
    try:
        httpd = socketserver.TCPServer(("127.0.0.1", p), H); port = p; break
    except OSError:
        continue
else:
    sys.exit("8770-8789 端口都被占用")
url = f"http://127.0.0.1:{port}/思维画布.html"
print("会话思维画布：", url, "  (Ctrl-C 停)")
try: webbrowser.open(url)
except Exception: pass
httpd.serve_forever()
'''


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="生成会话思维画布视图（读段.md版：小 html + serve.py）")
    ap.add_argument("--person")
    ap.add_argument("--repo")
    ap.add_argument("--tree", help="对话树目录（含 tree.json）；给了就直接写进它")
    a = ap.parse_args()
    if a.tree:
        tree_dir = a.tree
    else:
        if not a.person:
            sys.exit("需 --person（或 --tree 直指对话树目录）")
        repo = ve.resolve_repo(a.person, a.repo) if ve else (a.repo or os.getcwd())
        tree_dir = os.path.join(repo, "团队协作记录", "智能体工作日志", a.person, "对话树")
    if not os.path.isdir(tree_dir):
        sys.exit(f"✗ 对话树目录不存在：{tree_dir}")
    open(os.path.join(tree_dir, "思维画布.html"), "w", encoding="utf-8", newline="\n").write(HTML)
    open(os.path.join(tree_dir, "serve.py"), "w", encoding="utf-8", newline="\n").write(SERVE)
    print(f"✓ 思维画布.html + serve.py → {os.path.relpath(tree_dir)}")
    print(f"  查看：cd \"{tree_dir}\" && python serve.py   （起小服务、自动开浏览器；文字现读段.md，不内嵌）")


if __name__ == "__main__":
    main()

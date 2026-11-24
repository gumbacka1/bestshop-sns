# 닷컴 비교 판매 → 회사 PC용 HTML 파일 1개(데이터·사진 포함, 파일 안에서 수정 가능)
# 입력: dotcom-b7f21e3e.html(화면) + data/lge_dotcom.json   출력: out/닷컴비교판매_YYMMDD_v1.html
import json, os, re, sys, io, base64, urllib.request, datetime
ROOT = os.path.join(os.path.dirname(__file__), '..')
UA = 'Mozilla/5.0'


def thumb(url, size):
    try:
        from PIL import Image
        req = urllib.request.Request(url, headers={'User-Agent': UA})
        im = Image.open(io.BytesIO(urllib.request.urlopen(req, timeout=30).read())).convert('RGB')
        im.thumbnail((size, size)); b = io.BytesIO(); im.save(b, 'JPEG', quality=70)
        return 'data:image/jpeg;base64,' + base64.b64encode(b.getvalue()).decode()
    except Exception:
        return ''


def sub(s, old, new):
    assert old in s, old[:60]
    return s.replace(old, new)


def ascii_safe(s):
    # 메일·휴대폰에서 글자 깨짐 방지: 파일 전체를 영문 글자만으로 (한글은 코드로 바꿔 넣고 브라우저가 다시 한글로 보여 줌)
    def js(t):
        out = []
        for ch in t:
            o = ord(ch)
            if o < 128: out.append(ch)
            elif o > 0xFFFF:
                o -= 0x10000; out.append('\\u%04x\\u%04x' % (0xD800 + (o >> 10), 0xDC00 + (o & 0x3FF)))
            else: out.append('\\u%04x' % o)
        return ''.join(out)
    def css(t): return ''.join(ch if ord(ch) < 128 else '\\%x ' % ord(ch) for ch in t)
    def htm(t): return ''.join(ch if ord(ch) < 128 else '&#x%x;' % ord(ch) for ch in t)
    parts = re.split(r'(<script>.*?</script>|<style>.*?</style>)', s, flags=re.S)
    res = []
    for x in parts:
        if x.startswith('<script>'): res.append(js(x))
        elif x.startswith('<style>'): res.append(css(x))
        else: res.append(htm(x))
    r = ''.join(res)
    assert all(ord(c) < 128 for c in r)
    return r


def main():
    D = json.load(open(os.path.join(ROOT, 'data', 'lge_dotcom.json'), encoding='utf-8'))
    cache = {}
    def walk(o):
        if isinstance(o, dict):
            if o.get('img', '').startswith('http'):
                if o['img'] not in cache: cache[o['img']] = thumb(o['img'], 160)
                o['img'] = cache[o['img']]
            for v in o.values(): walk(v)
        elif isinstance(o, list):
            for v in o: walk(v)
    if '--noimg' not in sys.argv: walk(D)
    s = open(os.path.join(ROOT, 'dotcom-b7f21e3e.html'), encoding='utf-8').read()
    s = sub(s, '<title>닷컴 비교 판매 · 관리자 시험판</title>', '<title>닷컴 비교 판매 · ' + D['updated'][:10] + '</title>')
    s = sub(s, '관리자 시험판</span>', '회사 PC용 파일</span>')
    s = sub(s, '</style>', '''.tools{display:flex;gap:6px;flex-wrap:wrap;margin-top:8px}.tools button,.tools label{font:inherit;font-size:12px;border:1px solid #666;background:#2c2c2c;color:#fff;border-radius:6px;padding:5px 9px;cursor:pointer}
.ed{margin:12px 16px 0;border:1.5px dashed #A50034;border-radius:10px;padding:10px 12px;background:#fffafb}
.ed b{font-size:13px;color:#A50034}.ed label{display:block;font-size:12px;color:#555;margin-top:8px}
.ed input,.ed select,.ed textarea{width:100%;font:inherit;font-size:13px;border:1px solid #ccc;border-radius:6px;padding:6px 8px;margin-top:3px;background:#fff}
.ed .row2{display:grid;grid-template-columns:1fr 1fr;gap:8px}.mine{font-size:10px;color:#fff;background:#1a7f37;border-radius:3px;padding:0 4px;margin-left:3px}
.say2{margin:10px 16px 0;background:#f5f5f5;border-radius:8px;padding:9px 11px;font-size:12.5px;line-height:1.6;white-space:pre-wrap}
@media print{.tools,.ed{display:none}}
</style>''')
    # 데이터 내장
    s = sub(s, "  try{D=await fetch('data/lge_dotcom.json?v='+Date.now()).then(r=>r.json())}catch(e){document.getElementById('app').innerHTML='<p class=\"note\">아직 수집된 데이터가 없어요. 매일 오전 9시에 자동으로 받아와요.</p>';return}\n  document.getElementById('upd').innerHTML='엘지닷컴 오늘의 랭킹 · '+esc(D.updated)+' 기준 · <a href=\"admin-b7f21e3e.html\">관리자 화면</a>';",
        "  D=window.__D;loadE();\n  document.getElementById('upd').innerHTML='엘지닷컴 오늘의 랭킹 · '+esc(D.updated)+' 기준 <span id=\"esum\"></span><div class=\"tools\"><button onclick=\"expE()\">수정 내용 내보내기</button><label>수정 내용 불러오기<input type=\"file\" accept=\".json\" onchange=\"impE(this)\" style=\"display:none\"></label><button onclick=\"if(confirm(\\'고친 내용을 모두 지울까요?\\')){E=blank();saveE();render()}\">수정 모두 지우기</button></div>';")
    # 수정 기능
    s = sub(s, "function care6(m){", r"""let E=null;const EK='lgeDotcomEdits';
function blank(){return {match:{},store:{},memo:{}}}
function loadE(){try{E=JSON.parse(localStorage.getItem(EK))||blank()}catch(e){E=blank()}E.match=E.match||{};E.store=E.store||{};E.memo=E.memo||{}}
function saveE(){try{localStorage.setItem(EK,JSON.stringify(E))}catch(e){}const n=Object.keys(E.match).length+Object.keys(E.store).length+Object.keys(E.memo).length;const el=document.getElementById('esum');if(el)el.textContent=n?' · 내가 고친 곳 '+n+'개':''}
function expE(){const b=new Blob([JSON.stringify(E,null,1)],{type:'application/json'});const a=document.createElement('a');a.href=URL.createObjectURL(b);const d=new Date();a.download='닷컴비교판매_수정내용_'+String(d.getFullYear()).slice(2)+String(d.getMonth()+1).padStart(2,'0')+String(d.getDate()).padStart(2,'0')+'.json';a.click()}
function impE(inp){const f=inp.files[0];if(!f)return;const r=new FileReader();r.onload=()=>{try{const x=JSON.parse(r.result);E={match:x.match||{},store:x.store||{},memo:x.memo||{}};saveE();render();alert('불러왔어요')}catch(e){alert('수정 내용 파일이 아니에요')}};r.readAsText(f)}
function setE(kind,m,k,v){if(kind==='match'){if(v)E.match[m]=v;else delete E.match[m]}else if(kind==='memo'){if(v)E.memo[m]=v;else delete E.memo[m]}else{const o=E.store[m]||{};if(v)o[k]=v;else delete o[k];if(Object.keys(o).length)E.store[m]=o;else delete E.store[m]}saveE()}
function mOf(x){return E.match[x.m]||x.match}
function sp(m){const o=E.store[m]||{};return o.price?Number(String(o.price).replace(/[^0-9]/g,''))||0:0}
function editBox(c,x,st){
  const opts=(c.all||[]).filter(q=>!q.only&&q.m!==x.m).sort((a,b)=>(a.g===x.g?0:1)-(b.g===x.g?0:1)||a.r-b.r);
  const o=E.store[st?st.m:x.m]||{};const key=st?st.m:x.m;
  let h=`<div class="ed"><b>✏️ 여기서 고치기</b> <span style="font-size:11px;color:#888">입력하면 바로 저장돼요</span>`;
  if(st)h+=`<label>매장 추천 모델 ${E.match[x.m]?'<span class="mine">내가 바꿈</span>':''}<select onchange="setE('match','${x.m}','',this.value===('${x.match||''}')?'':this.value);render()">${opts.map(q=>`<option value="${q.m}" ${q.m===st.m?'selected':''}>${esc(q.m)} · ${esc(q.sz)} · ${esc(q.g||'')} · ${esc(q.rel)}${q.m===x.match?' (자동)':''}</option>`).join('')}</select></label>`;
  h+=`<div class="row2"><label>매장 혜택가 (${esc(key)})<input inputmode="numeric" value="${esc(o.price||'')}" placeholder="예: 2,500,000" onchange="setE('store','${key}','price',this.value);render()"></label><label>카드·결합 조건<input value="${esc(o.card||'')}" placeholder="예: ○○카드 7%" onchange="setE('store','${key}','card',this.value);render()"></label></div>`;
  h+=`<label>판매 멘트·메모<textarea rows="3" onchange="setE('memo','${x.m}','',this.value);render()">${esc(E.memo[x.m]||'')}</textarea></label></div>`;
  return h}
function care6(m){""")
    # 목록: 매칭 덮어쓰기 반영
    s = sub(s, "    const m=x.match?findItem(c,x.match):null;", "    const m=mOf(x)?findItem(c,mOf(x)):null;")
    s = sub(s, "${x.far?'<span class=\"warn\">크기 차이 큼</span>':''}", "${E.match[x.m]?'<span class=\"mine\">내가 바꿈</span>':(x.far?'<span class=\"warn\">크기 차이 큼</span>':'')}")
    s = sub(s, "const click=x.only&&x.match?", "const click=x.only&&mOf(x)?")
    # 대결카드
    s = sub(s, "const c=D.cats[S.cat],x=findItem(c,S.view.m),card=D.cards[S.view.m],st=findItem(c,card.store);",
        "const c=D.cats[S.cat],x=findItem(c,S.view.m),auto=D.cards[S.view.m]||{diff:[],same:[]},st=findItem(c,mOf(x)),mine=st.m!==auto.store,card=mine?{diff:[],same:[],far:false}:auto;const spv=sp(st.m),so=E.store[st.m]||{};")
    s = sub(s, "  if(card.far)h+=`<div class=\"note\">크기/용량 차이가 커요. 매칭이 맞는지 확인이 필요해요.</div>`;",
        "  if(card.far)h+=`<div class=\"note\">크기/용량 차이가 커요. 매칭이 맞는지 확인이 필요해요.</div>`;\n  if(mine)h+=`<div class=\"note\">직접 고른 매장 모델이에요. 세부 사양 비교(노란 줄)는 자동 매칭 모델에만 있어요.</div>`;\n  if(spv||so.card)h+=`<div class=\"gap\" style=\"margin:10px 16px 0\"><div class=\"gb\"><div class=\"t\">매장 혜택가 (직접 입력)</div><div class=\"v\">${spv?won(spv)+'원':'-'}</div><div class=\"t\">${esc(so.card||'')}</div></div><div class=\"gb\"><div class=\"t\">닷컴 최대혜택가와 차이</div><div class=\"v r\">${spv?signed(spv-x.max)+'원':'-'}</div></div></div>`;\n  if(E.memo[x.m])h+=`<div class=\"say2\"><b>멘트·메모</b>\\n${esc(E.memo[x.m])}</div>`;\n  h+=editBox(c,x,st);")
    # 같은 모델 카드
    s = sub(s, "  h+=`<div class=\"sec\"><div class=\"st2\">일시불</div><table><tr><td class=\"k\">판매가</td>",
        "  {const v=sp(x.m),o=E.store[x.m]||{};if(v||o.card)h+=`<div class=\"gap\" style=\"margin:10px 16px 0\"><div class=\"gb\"><div class=\"t\">매장 혜택가 (직접 입력)</div><div class=\"v\">${v?won(v)+'원':'-'}</div><div class=\"t\">${esc(o.card||'')}</div></div><div class=\"gb\"><div class=\"t\">닷컴 최대혜택가와 차이</div><div class=\"v r\">${v&&!x.sub?signed(v-x.max)+'원':'-'}</div></div></div>`;if(E.memo[x.m])h+=`<div class=\"say2\"><b>멘트·메모</b>\\n${esc(E.memo[x.m])}</div>`;h+=editBox(c,x,null);}\n  h+=`<div class=\"sec\"><div class=\"st2\">일시불</div><table><tr><td class=\"k\">판매가</td>")
    s = sub(s, "<script>\n", "<script>\nwindow.__D=" + json.dumps(D, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/') + ";\n", )
    s = s.replace("  history.replaceState({view:null", "  saveE();history.replaceState({view:null", 1)
    s = ascii_safe(s)
    os.makedirs(os.path.join(ROOT, 'out'), exist_ok=True)
    ymd = D['updated'][2:10].replace('-', '')
    fn = os.path.join(ROOT, 'out', f'닷컴비교판매_{ymd}_v1.html')
    open(fn, 'w', encoding='utf-8').write(s)
    print(fn, os.path.getsize(fn), '사진', sum(1 for v in cache.values() if v), '/', len(cache))


if __name__ == '__main__':
    main()

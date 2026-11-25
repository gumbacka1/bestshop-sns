// 다품목·구독 계산 엔진 (엘지닷컴 다품목 혜택관 규칙 2026-11 기준) — 모든 버전이 같이 씀
const R = {
  cashback: {2:100000,3:150000,4:400000,5:500000,6:600000,7:1050000,8:1200000,9:1350000,10:2000000,11:2200000,12:3000000,13:3250000,14:3500000,15:3750000,16:4000000,17:4250000,18:4500000,19:4750000,20:5000000,21:5250000,22:5500000,23:5750000,24:6000000,25:6250000},
  small: 30000,
  points: [[30000000,1400000],[27000000,1200000],[24000000,1000000],[21000000,800000],[18000000,650000],[15000000,600000],[12000000,500000],[9000000,350000],[6000000,150000],[3000000,50000]],
  gifts: [[15000000,500000],[12000000,400000],[6000000,300000]],
  cards: {
    '신한카드': {cb:1, pay:1}, 'KB국민카드': {cb:1, pay:1}, '롯데카드': {cb:1, pay:1}, '우리카드': {cb:1, pay:1},
    '현대카드': {cb:0, pay:1}, '하나카드': {cb:1, pay:0}, 'NH농협카드': {cb:1, pay:0}, '기타 결제': {cb:0, pay:0}
  },
  payRate: 0.07, payMin: 500000, payCap: 1000000,
  subBundle: {72:0.05, 60:0.03, 48:0.03},
  subPoint: n => n >= 3 ? 300000 : n === 2 ? 200000 : n === 1 ? 100000 : 0
};
const won = n => (Math.round(n) || 0).toLocaleString('ko-KR') + '원';
const man = n => { n = Math.round(n || 0); return n >= 10000 && n % 10000 === 0 ? (n / 10000).toLocaleString('ko-KR') + '만원' : won(n); };
const floor100 = n => Math.floor(n / 100) * 100;
const bracket = (list, v) => { for (const [min, amt] of list) if (v >= min) return amt; return 0; };
const nextBracket = (list, v) => { const asc = [...list].reverse(); for (const [min, amt] of asc) if (v < min) return {need: min - v, amt, min}; return null; };

let MODELS = [], MAP = {}, UPDATED = '', SHOP = null;
async function loadModels(base = '') {
  const [d, s] = await Promise.all([
    fetch(base + 'models.json').then(r => r.json()),
    fetch(base + 'bestshop.json').then(r => r.json()).catch(() => null)
  ]);
  MODELS = d.models; UPDATED = d.updated; MAP = {}; MODELS.forEach(x => MAP[x.m] = x);
  SHOP = s; try { const local = JSON.parse(localStorage.getItem('calc_bestshop') || 'null'); if (local) SHOP = Object.assign({}, SHOP, local); } catch (e) {}
  return MODELS;
}
function search(q, limit = 30) {
  q = (q || '').trim().toUpperCase().replace(/\s+/g, ' ');
  if (!q) return MODELS.slice(0, limit);
  const parts = q.split(' ');
  return MODELS.filter(x => { const t = (x.m + ' ' + x.n + ' ' + x.c + ' ' + x.s).toUpperCase(); return parts.every(p => t.includes(p)); }).slice(0, limit);
}
function subPrice(x, term) { const s = x.sub && x.sub[String(term)]; return s ? s[0] : 0; }

/* cart: [{m, mode:'buy'|'sub', term:72, coupon:0, on:true}]
   opt: {card, shop:false(베스트샵 기준), pointOverride:null, extra:0(추가 할인)} */
function calc(cart, opt = {}) {
  const card = R.cards[opt.card || '신한카드'] || R.cards['기타 결제'];
  const items = cart.filter(c => c.on !== false && MAP[c.m]).map(c => Object.assign({x: MAP[c.m]}, c));
  const buy = items.filter(c => c.mode !== 'sub'), sub = items.filter(c => c.mode === 'sub');
  const r = {count: items.length, buyCount: buy.length, subCount: sub.length, notes: []};
  r.list = buy.reduce((a, c) => a + c.x.p, 0);
  r.member = buy.reduce((a, c) => a + (c.x.d || 0), 0);
  r.coupon = buy.reduce((a, c) => a + (+c.coupon || 0), 0);
  r.extra = +opt.extra || 0;
  r.pay = Math.max(0, r.list - r.member - r.coupon - r.extra);           // 할인 결제가

  // 다품목 캐시백: 다품목 뱃지 모델, 제품군 중복 X, 일시불 1건 이상 필요, 카드 조건
  const seen = new Set(); let large = 0, small = 0;
  items.forEach(c => { if (!c.x.mb || seen.has(c.x.g)) return; seen.add(c.x.g); c.x.sm ? small++ : large++; });
  r.large = large; r.small = small; r.eligible = large + small;
  const table = opt.shop && SHOP && SHOP.cashback ? Object.assign({}, R.cashback, SHOP.cashback) : R.cashback;
  let multi = 0, smallAmt = 0;
  if (buy.length && (card.cb || opt.shop)) {
    if (large >= 2) multi = table[Math.min(large, 25)] || 0;
    else if (large === 1 && small >= 1) multi = 50000;
    if (small >= 2 || (small >= 1 && large >= 1)) smallAmt = small * R.small;
  } else if (!buy.length && items.length) r.notes.push('구독만 담으면 다품목 캐시백이 없어요 (일시불 1건 이상 필요)');
  else if (!card.cb) r.notes.push(opt.card + '는 다품목 캐시백이 없어요');
  r.multi = multi; r.smallCash = smallAmt; r.cash = multi + smallAmt;
  if (opt.shop && SHOP && SHOP.cashback && !(large in SHOP.cashback) && large >= 2) r.notes.push(large + '개 베스트샵 캐시백은 아직 미확인이라 닷컴 금액으로 넣었어요');

  // 결제일 할인
  r.payDc = card.pay && r.pay >= R.payMin ? Math.min(floor100(r.pay * R.payRate), R.payCap) : 0;
  // 멤버십 포인트 (닷컴: 일시불만, 베스트샵: 구독도 일시불 정상가로 합산)
  r.pointBase = opt.shop ? r.list + sub.reduce((a, c) => a + c.x.p, 0) : r.pay;
  r.point = opt.pointOverride != null && opt.pointOverride !== '' ? +opt.pointOverride : bracket(R.points, r.pointBase);
  r.gift = bracket(R.gifts, r.pointBase);
  r.nextPoint = nextBracket(R.points, r.pointBase); r.nextGift = nextBracket(R.gifts, r.pointBase);
  r.nextCash = large >= 1 && large < 25 ? {n: large + 1, add: (table[large + 1] || 0) - multi} : null;
  r.benefit = r.cash + r.payDc + r.point;
  r.final = r.pay - r.benefit;                                              // 최종 혜택 적용 금액

  // 구독
  const groups = new Set(sub.map(c => c.x.g));
  r.subs = sub.map(c => {
    const term = +c.term || 72, base = subPrice(c.x, term);
    const rate = sub.length >= 2 && groups.size >= 2 ? (R.subBundle[term] || 0) : 0;
    const month = rate ? floor100(base * (1 - rate)) : base;
    return {m: c.m, name: c.x.n, term, base, month, rate, total: month * term};
  });
  r.subMonth = r.subs.reduce((a, s) => a + s.month, 0);
  r.subBase = r.subs.reduce((a, s) => a + s.base, 0);
  r.subTotal = r.subs.reduce((a, s) => a + s.total, 0);
  r.subPoint = R.subPoint(sub.length);
  r.subMissing = r.subs.filter(s => !s.base).map(s => s.m);
  if (r.subMissing.length) r.notes.push('구독 요금 없는 모델: ' + r.subMissing.join(', '));
  r.extraShop = opt.shop && SHOP ? (+SHOP.extraDiscount || 0) : 0;
  return r;
}
// 화면 공용: 모델 검색 상자
function pickerHTML(id) { return `<div class="pick"><input id="${id}" placeholder="모델명·제품명 검색 (예: M876, 올레드 83, 정수기)" autocomplete="off"><div class="res" id="${id}_r"></div></div>`; }
function bindPicker(id, onPick) {
  const inp = document.getElementById(id), res = document.getElementById(id + '_r');
  const draw = () => { const q = inp.value; if (!q) { res.innerHTML = ''; return; }
    res.innerHTML = search(q, 25).map(x => `<div class="ri" data-m="${x.m}"><b>${x.m}</b> ${x.n}<span>${won(x.p - x.d)}${x.mb ? ' · <em>다품목</em>' : ''}${x.sub && x.sub['72'] ? ' · 구독 ' + won(x.sub['72'][0]) : ''}</span></div>`).join('') || '<div class="ri">없어요</div>'; };
  inp.addEventListener('input', draw);
  res.addEventListener('click', e => { const el = e.target.closest('.ri'); if (!el || !el.dataset.m) return; onPick(el.dataset.m); inp.value = ''; res.innerHTML = ''; });
}
function save(key, v) { try { localStorage.setItem(key, JSON.stringify(v)); } catch (e) {} }
function load(key, d) { try { return JSON.parse(localStorage.getItem(key)) || d; } catch (e) { return d; } }
const CARD_NAMES = Object.keys(R.cards);
function cardSelect(id, v) { return `<select id="${id}">${CARD_NAMES.map(c => `<option ${c === v ? 'selected' : ''}>${c}</option>`).join('')}</select>`; }
// 보내 주신 캡처 조합 (검증용)
const SAMPLE = [{m:'M876GBB231', mode:'buy', coupon:569600},{m:'OLED83G5KW', mode:'buy', coupon:0}];

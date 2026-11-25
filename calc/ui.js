// 장바구니 공용 화면 조각
function cartHTML(cart, o = {}) {
  if (!cart.length) return '<div class="muted" style="padding:14px 0">위 검색창에서 모델을 담아 주세요</div>';
  return cart.map((c, i) => {
    const x = MAP[c.m]; if (!x) return '';
    const sp = subPrice(x, c.term || 72);
    const price = c.mode === 'sub' ? `월 ${won(sp)} <span class="muted">(${(c.term || 72) / 12}년)</span>` :
      `${(x.d || c.coupon) ? Math.round((x.d + (+c.coupon || 0)) / x.p * 100) + '% ' : ''}<b>${won(x.p - x.d - (+c.coupon || 0))}</b> <s class="muted">${won(x.p)}</s>`;
    return `<div class="item">${o.check ? `<input type="checkbox" data-i="${i}" class="ck" ${c.on !== false ? 'checked' : ''} style="width:22px;height:22px">` : ''}
      ${x.img ? `<img src="${x.img}" loading="lazy" onerror="this.style.display='none'">` : ''}
      <div class="t"><div class="nm">${x.n}</div><div class="md">${x.m}${x.manual ? ' · 가격 수동' : ''}</div>
      <div>${x.mb ? '<span class="tag">다품목</span>' : '<span class="tag g">다품목 아님</span>'}${x.sm ? '<span class="tag g">소형</span>' : ''}${x.pc ? '<span class="tag">제품별 캐시백 ' + man(x.pc) + '</span>' : ''}${x.o ? '<span class="tag g">닷컴전용</span>' : ''}</div>
      <div style="margin-top:4px">${price}</div>
      ${o.mode !== false ? `<div class="seg"><button data-i="${i}" data-mode="buy" class="${c.mode !== 'sub' ? 'on' : ''}">일시불</button><button data-i="${i}" data-mode="sub" class="${c.mode === 'sub' ? 'on' : ''}" ${sp || subPrice(x, 72) ? '' : 'disabled title="구독 없음"'}>구독</button></div>` : ''}
      ${c.mode === 'sub' ? `<select class="mini term" data-i="${i}">${[72, 60, 48, 36].map(t => `<option value="${t}" ${(+c.term || 72) === t ? 'selected' : ''}>${t / 12}년</option>`).join('')}</select>` :
        (o.coupon !== false ? `<div class="muted" style="margin-top:4px">쿠폰 <input class="mini cp" data-i="${i}" inputmode="numeric" value="${c.coupon || ''}" placeholder="0"></div>` : '')}
      </div><button class="x" data-del="${i}">×</button></div>`;
  }).join('');
}
function bindCart(el, cart, redraw) {
  el.onclick = e => {
    const t = e.target;
    if (t.dataset.del != null) { cart.splice(+t.dataset.del, 1); redraw(); }
    else if (t.dataset.mode) { cart[+t.dataset.i].mode = t.dataset.mode; if (!cart[+t.dataset.i].term) cart[+t.dataset.i].term = 72; redraw(); }
    else if (t.classList.contains('ck')) { cart[+t.dataset.i].on = t.checked; redraw(); }
  };
  el.onchange = e => {
    const t = e.target;
    if (t.classList.contains('cp')) { cart[+t.dataset.i].coupon = +t.value.replace(/\D/g, '') || 0; redraw(); }
    if (t.classList.contains('term')) { cart[+t.dataset.i].term = +t.value; redraw(); }
  };
}
function addToCart(cart, m, mode) { if (cart.some(c => c.m === m)) return; cart.push({m, mode: mode || 'buy', term: 72, coupon: (MAP[m] && MAP[m].cp) || 0, on: true}); }
function topBar(title, sub) { return `<div class="top"><div><a href="index.html">← 계산기 목록</a><br><b>${title}</b></div><div style="text-align:right">${sub || ''}</div></div>`; }
function footNote() { return `<div class="muted" style="margin:12px 16px">엘지닷컴 ${UPDATED} 기준 · 쿠폰은 닷컴 표시 쿠폰을 기본으로 넣었고 고객마다 달라 고칠 수 있음 · 멤버십 포인트는 닷컴이 제품군별 기준금액을 따로 잡아 1~2구간 차이 날 수 있어요 · 계산은 참고용, 최종 금액은 결제 화면 기준</div>`; }

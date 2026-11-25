# data/lge_full/*.json → 엑셀 정리본 (data/lge_full/엘지닷컴_전모델_YYMMDD_v1.xlsx)
import json, os, re, glob, datetime
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

D = os.path.join(os.path.dirname(__file__), '..', 'data', 'lge_full')
F = 'LG스마트체2.0 Regular'
ONLY = {}
HEAD = PatternFill('solid', fgColor='EDEDED')
LINE = Border(bottom=Side(style='thin', color='BFBFBF'))


def load(n, default):
    try:
        return json.load(open(os.path.join(D, n), encoding='utf-8'))
    except Exception:
        return default


def sheet(wb, title, header, rows, widths, money=()):
    ws = wb.create_sheet(title)
    ws.append(header)
    for r in rows: ws.append(r)
    for c in ws[1]:
        c.font = Font(name=F, bold=True); c.fill = HEAD; c.border = LINE
        c.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    for row in ws.iter_rows(min_row=2):
        for c in row:
            c.font = Font(name=F, color='000000'); c.border = LINE
            c.alignment = Alignment(vertical='top', wrap_text=True)
        for i in money:
            if i < len(row): row[i].number_format = '#,##0;-#,##0;-'
    for i, w in enumerate(widths):
        ws.column_dimensions[chr(65 + i) if i < 26 else 'A' + chr(65 + i - 26)].width = w
    ws.freeze_panes = 'A2'
    ws.auto_filter.ref = ws.dimensions
    return ws


def n(v):
    try: return int(float(v))
    except Exception: return None


def main():
    P = load('products.json', []); R = load('ranking.json', {}); B = load('benefits.json', {}); M = load('meta.json', {})
    global ONLY
    ONLY = {q.get('modelName'): ('Y' if q.get('lgecomOnlyFlag') == 'Y' else 'N') for k in R.values() for l in k.values() for q in l}
    wb = Workbook(); ws = wb.active; ws.title = '요약'
    ws.append(['엘지닷컴 전 모델 수집 결과']); ws.append(['수집 시각', M.get('updated', '')])
    for k in ['모델수', '구독있음', '다품목대상', '결합할인대상', '행사페이지', '사진있음', '영상있음', '초']: ws.append([k, M.get(k)])
    ws.append([]); ws.append(['품목(사이트 경로)', '모델 수'])
    for k, v in (M.get('품목별') or {}).items(): ws.append([k, v])
    ws.append([]); ws.append(['▶ 코멘트'])
    ws.append(['- 가격은 수집 시각의 엘지닷컴 표시 기준이에요. 쿠폰·카드 조건은 매일 바뀌니 상담 전 한 번 확인해 주세요.'])
    ws.append(['- 사진·영상은 링크만 모았어요. 사진의 권리는 LG전자에 있어요.'])
    for row in ws.iter_rows():
        for c in row: c.font = Font(name=F, bold=(c.row == 1))
    ws.column_dimensions['A'].width = 28; ws.column_dimensions['B'].width = 40

    rows = []
    for p in P:
        pt = p.get('price_text') or {}
        sp = p.get('specs') or {}
        rel = (p.get('modelReleaseDate') or sp.get('동일모델의 출시년월') or '')[:7]
        cap = next((v for k, v in sp.items() if re.search(r'전체 용량|용량|화면 크기|냉방면적|세탁 용량|건조 용량', k)), '')
        eng = next((v for k, v in sp.items() if '에너지소비효율' in k or '에너지 소비효율' in k), '')
        only = ONLY.get(p.get('modelName'), '')
        rows.append([p.get('경로품목'), p.get('categoryName'), p.get('subCategoryName'), p.get('modelName'),
                     p.get('modelDisplayName') or p.get('title'), rel, cap, eng,
                     n(p.get('obsOriginalPrice')) or pt.get('할인 전 판매가'), n(p.get('obsSellingPrice')),
                     pt.get('쿠폰 적용 시'), n(p.get('maxBenefitPrice')) or pt.get('최대혜택가'),
                     only, p.get('다품목'), p.get('결합'), 'Y' if (p.get('care') or {}).get('요약') else '', '구독 전용' if p.get('구독전용') else p.get('sold_as'),
                     p.get('reviewCount') or p.get('review_text'), p.get('reviewRating'), p.get('url')])
    sheet(wb, '모델·가격', ['경로', '품목', '세부', '모델', '제품명', '출시', '용량·크기', '에너지등급', '정상가', '할인가',
                         '쿠폰 적용가', '최대혜택가', '닷컴 전용(랭킹 기준)', '다품목할인', '결합할인', '구독 가능', '구독 전용/판매 사양', '리뷰 수', '평점', '주소'], rows,
          [14, 10, 12, 16, 40, 9, 12, 16, 13, 13, 13, 13, 11, 9, 9, 8, 18, 8, 6, 40], money=(8, 9, 10, 11))

    rows = []
    for p in P:
        c = p.get('care') or {}
        t = c.get('요약') or {}
        if not c: continue
        rows.append([p.get('경로품목'), p.get('modelName'),
                     *[(t.get(k) or {}).get('월') for k in ('36', '48', '60', '72')],
                     *[(t.get(k) or {}).get('정상') for k in ('72',)],
                     ', '.join(x for x in (c.get('careServiceTypes') or []) if x),
                     ', '.join(x for x in (c.get('careServiceCycles') or []) if x),
                     c.get('current_selection'), c.get('url')])
    sheet(wb, '구독료·케어', ['품목', '모델', '3년 월', '4년 월', '5년 월', '6년 월', '6년 정상 월', '케어 유형',
                           '방문 주기', '기본 선택', '주소'], rows, [14, 16, 11, 11, 11, 11, 12, 40, 30, 16, 40],
          money=(2, 3, 4, 5, 6))

    rows = [[p.get('경로품목'), p.get('modelName'), p.get('다품목'), p.get('결합'), ', '.join(p.get('badges') or []),
             '\n'.join(p.get('max_benefit_lines') or []), '\n'.join(p.get('buy_benefit_lines') or []),
             '\n'.join(p.get('캐시백_lines') or []), '\n'.join((p.get('care') or {}).get('combine_lines') or [])]
            for p in P]
    sheet(wb, '할인·캐시백(모델별)', ['품목', '모델', '다품목할인 대상', '결합할인 대상', '표시 뱃지', '최대혜택가 구성',
                                  '구매 혜택', '캐시백', '구독 할인(결합·선납·재구독 등)'], rows, [14, 16, 9, 9, 18, 50, 50, 40, 50])

    rows = [[k, v.get('title'), v.get('url'), '\n'.join(v.get('할인') or [])[:30000], '\n'.join(v.get('캐시백') or [])[:30000]]
            for k, v in B.items()]
    sheet(wb, '할인·행사 페이지', ['구분', '제목', '주소', '할인·포인트 문구', '캐시백 문구'], rows, [22, 36, 40, 80, 60])

    rows = [[p.get('경로품목'), p.get('modelName'), (p.get('care') or {}).get('care_text') or p.get('care_text'),
             (p.get('care') or {}).get('notes') or p.get('care_notes'), (p.get('care') or {}).get('benefit_text')]
            for p in P if (p.get('care') or {}).get('care_text') or p.get('care_text')]
    sheet(wb, '케어 안내글', ['품목', '모델', '방문 주기·케어 내용', '구독 전 확인 사항', '구독료 혜택'], rows,
          [14, 16, 70, 50, 40])

    rows = [[p.get('경로품목'), p.get('modelName'), k, v] for p in P for k, v in (p.get('specs') or {}).items()]
    sheet(wb, '사양', ['품목', '모델', '항목', '값'], rows[:200000], [14, 16, 28, 60])

    rows = [[p.get('경로품목'), p.get('modelName'), '사진' if i < len(p.get('images') or []) else '영상', u]
            for p in P for i, u in enumerate((p.get('images') or []) + (p.get('videos') or []))]
    sheet(wb, '사진·영상 링크', ['품목', '모델', '종류', '링크'], rows, [14, 16, 8, 90])

    rows, seen = [], set()
    for k, v in B.items():
        for c in v.get('cards') or []:
            key = (c.get('카드'), tuple(c.get('실적별') or []))
            if key in seen: continue
            seen.add(key)
            rows.append([c.get('카드'), c.get('기간', ''), '\n'.join(c.get('실적별') or []), c.get('혜택기간', ''),
                         c.get('실적인정', ''), c.get('연회비', ''), '\n'.join(c.get('조건') or []), v.get('url')])
    sheet(wb, '제휴카드', ['카드', '행사 기간', '전월 실적별 월 할인', '혜택 기간', '구독료 실적인정', '연회비', '조건', '주소'],
          rows, [26, 22, 34, 12, 10, 30, 50, 40])

    rows = [[k, v.get('url'), (v.get('text') or '')[:32000]] for k, v in B.items()]
    sheet(wb, '혜택 안내 원문', ['페이지', '주소', '내용'], rows, [18, 40, 120])

    rows = []
    for cat, kinds in R.items():
        for kind, lst in kinds.items():
            for p in lst:
                rows.append([cat, kind, p.get('순위'), p.get('modelName'), p.get('modelDisplayName'),
                             p.get('keywdNmA'), p.get('keywdNmB'), n(p.get('obsSellingPrice')), n(p.get('maxBenefitPrice')),
                             'Y' if p.get('lgecomOnlyFlag') == 'Y' else ''])
    sheet(wb, '랭킹', ['품목', '구분', '순위', '모델', '제품명', '특징1', '특징2', '할인가', '최대혜택가', '닷컴 전용'],
          rows, [10, 8, 6, 16, 44, 10, 10, 13, 13, 9], money=(7, 8))

    for old in glob.glob(os.path.join(D, '엘지닷컴_전모델_*.xlsx')): os.remove(old)
    day = (datetime.datetime.utcnow() + datetime.timedelta(hours=9)).strftime('%y%m%d')
    out = os.path.join(D, f'엘지닷컴_전모델_{day}_v1.xlsx')
    wb.save(out)
    print('엑셀', out)


if __name__ == '__main__':
    main()

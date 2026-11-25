from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.worksheet.datavalidation import DataValidation
F='LG스마트체2.0 Regular'
wb=Workbook(); ws=wb.active; ws.title='전략제품입력'
hdr=['품목','세부구분','전략제품 모델명','선정','일시불 금액(원)','구독 월 금액(원)','구독 기간(년)','결합할인(월, 원)','같은 점(선택)','다른 점(선택)','추천 멘트(선택)','케어 내용(선택)','제휴카드 할인(월, 원)','카드 조건(선택)']
ws.append(hdr)
rows=[['냉장고','800L급','M876GBB231','본사',4400000,87000,6,None,'871L 대용량 4도어, 에너지 1등급이에요. 닷컴 랭킹의 800L급 모델들과 같은 870L대 용량이에요.','매직스페이스가 2개(더블매직스페이스)라 자주 꺼내는 음료·반찬을 큰 문을 열지 않고 꺼낼 수 있어요. 글라스 도어에 AI 신선케어, 자동정온, UV청정탈취필터+가 들어가 있어요.','닷컴에서 잘 보고 오셨네요. 이 모델 저희 매장에도 똑같이 있어요. 닷컴 최대혜택가는 앱 전용 쿠폰이랑 특정 카드 결제일 할인을 다 받았을 때 금액이라, 실제로 받으실 수 있는 조건부터 같이 확인해 볼게요.','구독 기간 무상 A/S, 30개월마다 정기 점검, 36개월 차 기계실 부분 분해·고압세척 1회',20000,'제휴카드 전월 40만원 이상 사용 시'],
['냉장고','양문형','S836GBB142','본사',2500000,48900,6,None,'832L 같은 용량에 매직스페이스가 있는 양문형이에요.','도어가 메탈이 아니라 미스트 글라스예요. AI 세이빙 모드·오토 클로징이 들어가 있어요. 에너지등급은 닷컴 S834MEE111(1등급)이 더 좋아요.','보고 오신 모델은 엘지닷컴 전용이라 매장에는 없어요. 대신 같은 832L 매직스페이스에 도어가 글라스인 이 모델을 직접 보여드릴게요.','프리미엄 케어 선택 시 매년 방문 점검·필터 교체, 36개월 차 기계실 분해 세척 (케어 유형 확인 필요)',20000,'제휴카드 전월 40만원 이상 사용 시'],
['냉장고','600L급','G646GBB031','',4150000,81900,6,None,'650L Fit & Max, 에너지 1등급이에요.','도어가 글라스예요. 주방 가구 라인에 맞춰 들어가요.','','라이트 케어: 30개월마다 점검, 36개월 차 기계실 분해 1회, 무상 A/S',20000,'제휴카드 전월 40만원 이상 사용 시'],
['냉장고','600L급','D646GBB041','',4550000,89900,6,None,'628L Fit & Max 컨버터블 드로어, 에너지 1등급이에요.','아래칸이 드로어(서랍)라 허리 숙이지 않고 꺼낼 수 있어요.','','정기 케어 연 4회, 워터필터·퓨어프레시필터 무상 교체, 무상 A/S',20000,'제휴카드 전월 40만원 이상 사용 시'],
['김치냉장고','스탠드형','예시-김치모델D','자체',1990000,39900,6,5000,'','','']]
for r in rows: ws.append(r)
thin=Side(style='thin',color='BFBFBF')
for c in ws[1]:
    c.font=Font(name=F,bold=True,color='000000'); c.fill=PatternFill('solid',fgColor='EDEDED')
    c.alignment=Alignment(horizontal='center',vertical='center',wrap_text=True); c.border=Border(bottom=thin,top=thin)
for row in ws.iter_rows(min_row=2,max_row=60):
    for c in row:
        c.font=Font(name=F,color='000000'); c.border=Border(bottom=thin); c.alignment=Alignment(vertical='center',wrap_text=True)
    for i in (4,5,7,12): row[i].number_format='#,##0;-#,##0;-'
for col,w in zip('ABCDEFGHIJKLMN',[11,11,20,8,15,15,12,15,28,28,34,30,15,24]): ws.column_dimensions[col].width=w
ws.row_dimensions[1].height=34; ws.freeze_panes='A2'
lists={'A':'"냉장고,김치냉장고,TV,세탁기,건조기,워시타워,에어컨"',
 'B':'"800L급,양문형,600L급,스탠드형,OLED,LED,세탁기,건조기,워시타워,2in1,스탠드,벽걸이"','D':'"본사,자체"'}
for col,f in lists.items():
    dv=DataValidation(type='list',formula1=f,allow_blank=True); ws.add_data_validation(dv); dv.add(f'{col}2:{col}200')
g=wb.create_sheet('작성방법')
lines=[('■ 이렇게 쓰시면 돼요',True),('- "전략제품입력" 시트에 품목·세부구분·모델명·선정·일시불 금액·구독 월 금액만 넣으면 돼요.',False),
('- G646GBB031·D646GBB041 구독료(81,900원·89,900원)와 김치냉장고 행은 예시 숫자예요. 매장 금액으로 바꿔 주세요.',False),
('- 품목·세부구분·선정은 칸을 누르면 고를 수 있어요. 세부구분이 같아야 닷컴 모델과 연결돼요.',False),
('- 결합할인은 2개 묶을 때 빠지는 월 금액이에요. 모르면 비워 두면 단순 합계로 계산해요.',False),
('- 같은 점·다른 점·추천 멘트는 선택이에요. 비워 두면 화면에 기본 문구가 나와요.',False),
('- 같이 사면 짝은 화면에 정해져 있어요 (냉장고↔김치냉장고, 세탁기↔건조기 등). 짝 품목도 이 시트에 넣어야 묶음 금액이 나와요.',False),
('',False),('■ 세부구분 기준 (냉장고)',True),('- 800L급: 4도어 870L대 / 양문형: 832L대 / 600L급: Fit & Max·일반형 600L대',False)]
for i,(t,b) in enumerate(lines,1):
    c=g.cell(i,1,t); c.font=Font(name=F,bold=b,color='000000')
g.column_dimensions['A'].width=110
d=wb.create_sheet('닷컴랭킹_참고')
d.append(['순위','세부구분','닷컴 모델명','제품명','용량','할인가(원)','최대혜택가(원)','표시'])
data=[(1,'800L급','T876MEE1H1','디오스 AI 오브제컬렉션 (매직스페이스)','870L',2490000,2129700,'26년 출시·닷컴 ONLY'),
(2,'양문형','S834MEE111','디오스 AI 오브제컬렉션 (양문형, 매직스페이스)','832L',1780000,1515900,'닷컴 ONLY'),
(3,'600L급','D646GBB041','디오스 AI 오브제컬렉션 Fit & Max (컨버터블 드로어)','628L',4550000,3980400,'26년 출시'),
(4,'600L급','G646GBB031','디오스 AI 오브제컬렉션 Fit & Max','650L',4150000,3608400,'26년 출시'),
(5,'800L급','M876GBB231','디오스 AI 오브제컬렉션 (더블매직스페이스)','871L',4550000,3980400,''),
(6,'양문형','S836MEE022','디오스 AI 오브제컬렉션 (양문형)','832L',1400000,1209000,'닷컴 ONLY'),
(7,'600L급','D604MEE52','일반냉장고 오브제컬렉션','612L',1290000,1106700,''),
(8,'600L급','G646GBB021','디오스 AI 오브제컬렉션 Fit & Max','650L',3250000,2771400,'26년 출시·닷컴 ONLY'),
(9,'600L급','M616GBB0M1','디오스 AI 오브제컬렉션 Fit & Max','609L',2680000,2278500,''),
(10,'800L급','T873MEE111','디오스 오브제컬렉션 (매직스페이스)','870L',2290000,1943700,'')]
for r in data: d.append(r)
for c in d[1]: c.font=Font(name=F,bold=True); c.fill=PatternFill('solid',fgColor='EDEDED'); c.alignment=Alignment(horizontal='center',wrap_text=True)
for row in d.iter_rows(min_row=2):
    for c in row: c.font=Font(name=F,color='000000'); c.border=Border(bottom=thin)
    row[5].number_format=row[6].number_format='#,##0'
d.cell(13,1,'▶ 출처: LGE.COM 오늘의 랭킹 냉장고 (2026.11.25 기준). 이 시트는 참고용이고, 화면은 Claude가 세팅한 랭킹을 써요.').font=Font(name=F)
for col,w in zip('ABCDEFGH',[6,10,14,44,8,13,14,20]): d.column_dimensions[col].width=w
wb.save('닷컴비교_전략제품입력_261125_v5.xlsx')

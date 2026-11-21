# 인스타 키 상태 점검 (키 값은 출력하지 않음)
import json, os, urllib.request, urllib.parse, urllib.error
T, U = os.environ['IG_TOKEN'], os.environ['IG_USER_ID']
def call(path, **p):
    p['access_token'] = T
    url = f'https://graph.facebook.com/v25.0/{path}?' + urllib.parse.urlencode(p)
    try:
        with urllib.request.urlopen(url, timeout=20) as r:
            return 'OK', json.loads(r.read())
    except urllib.error.HTTPError as e:
        try: err = json.loads(e.read())['error']
        except Exception: err = {'http': e.code}
        return 'ERR', {k: err.get(k) for k in ('code', 'error_subcode', 'type', 'message', 'error_user_title', 'error_user_msg')}
print('1 키 주인(me):', call('me', fields='id,name'))
print('2 권한 목록:', call('me/permissions'))
print('3 비즈니스 계정:', call(U, fields='id,username'))
print('4 조회(최소):', call(U, fields='business_discovery.username(lgbestshop_unjeong){followers_count}'))
r = call(U, fields='business_discovery.username(lgbestshop_unjeong){followers_count,media.limit(3){timestamp,view_count,like_count,comments_count}}')
print('5 조회(전체 항목):', r[0], r[1] if r[0] == 'ERR' else '')

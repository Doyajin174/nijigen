# 명조 공식 유튜브 리딤코드 스크래퍼 (Python)
# 사용법: Flask app context에서 import 후 run_scraper() 실행
import os
import requests
import re
from datetime import datetime
from typing import Optional
from app import db
from models import RedeemCode

YOUTUBE_API_KEY = os.environ.get('YOUTUBE_API_KEY')
CHANNEL_ID = 'UCKuq0c-RXYaulECSuu5hFug'  # 명조 공식 채널 ID

# 공식 댓글만 추출

def is_official_comment(comment):
    official_names = ['Wuthering Waves', '명조', 'WW_KR_Official', '鸣潮']
    author_name = comment.get('authorDisplayName', '')
    author_channel_id = comment.get('authorChannelId', {}).get('value', '')
    return author_channel_id == CHANNEL_ID or any(name in author_name for name in official_names)

def parse_korean_date(korean_date_str: str) -> Optional[datetime]:
    if not korean_date_str:
        return None
    current_year = datetime.utcnow().year
    patterns = [
        # 2024년 6월 2일 00:59
        (re.compile(r"(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일\s*(\d{1,2}):(\d{2})"),
         lambda m: datetime(int(m[1]), int(m[2]), int(m[3]), int(m[4]), int(m[5]))),
        # 6월 2일 00:59
        (re.compile(r"(\d{1,2})월\s*(\d{1,2})일\s*(\d{1,2}):(\d{2})"),
         lambda m: datetime(current_year, int(m[1]), int(m[2]), int(m[3]), int(m[4]))),
        # 2024-06-02 00:59
        (re.compile(r"(\d{4})-(\d{1,2})-(\d{1,2})[ T](\d{1,2}):(\d{2})"),
         lambda m: datetime(int(m[1]), int(m[2]), int(m[3]), int(m[4]), int(m[5]))),
        # 6/2 00:59
        (re.compile(r"(\d{1,2})/(\d{1,2})\s*(\d{1,2}):(\d{2})"),
         lambda m: datetime(current_year, int(m[1]), int(m[2]), int(m[3]), int(m[4]))),
        # 2024년 6월 2일
        (re.compile(r"(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일"),
         lambda m: datetime(int(m[1]), int(m[2]), int(m[3]))),
        # 6월 2일
        (re.compile(r"(\d{1,2})월\s*(\d{1,2})일"),
         lambda m: datetime(current_year, int(m[1]), int(m[2]))),
        # 2024-06-02
        (re.compile(r"(\d{4})-(\d{1,2})-(\d{1,2})"),
         lambda m: datetime(int(m[1]), int(m[2]), int(m[3]))),
        # 6/2
        (re.compile(r"(\d{1,2})/(\d{1,2})"),
         lambda m: datetime(current_year, int(m[1]), int(m[2])))
    ]
    for regex, handler in patterns:
        match = regex.search(korean_date_str)
        if match:
            try:
                return handler(match)
            except Exception:
                continue
    try:
        parsed = datetime.fromisoformat(korean_date_str)
        return parsed
    except Exception:
        pass
    return None

def extract_codes_and_expiry(text: str):
    code_patterns = [
        r'\b[A-Z]{2,4}[0-9]{6,12}\b',
        r'\b[A-Z0-9]{8,16}\b',
        r'WUTHERING[A-Z0-9]+',
        r'WW[A-Z0-9]{6,}',
        r'\b[A-Z]{3}[0-9]{6}[A-Z0-9]*\b'
    ]
    expiry_patterns = [
        r'(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일',
        r'(\d{1,2})월\s*(\d{1,2})일',
        r'(\d{4})[./-](\d{1,2})[./-](\d{1,2})',
        r'(\d{1,2})[./-](\d{1,2})[./-](\d{4})',
        r'(\d{1,2})[./-](\d{1,2})',
        r'(까지|유효|만료|expire|valid|~)'
    ]
    found_codes = set()
    for pat in code_patterns:
        for m in re.findall(pat, text):
            if len(m) >= 6 and m.upper() not in ['YOUTUBE', 'VIDEO', 'STREAM', 'CHANNEL', 'SUBSCRIBE']:
                found_codes.add(m.upper())
    found_expiry = None
    for pat in expiry_patterns:
        match = re.search(pat, text)
        if match:
            date_str = match.group(0)
            parsed = parse_korean_date(date_str)
            if parsed:
                found_expiry = parsed
                break
    return [{
        'code': code,
        'expiry': found_expiry
    } for code in found_codes]

def get_latest_live_video_id():
    url = f'https://www.googleapis.com/youtube/v3/search?key={YOUTUBE_API_KEY}&channelId={CHANNEL_ID}&part=snippet&type=video&eventType=completed&order=date&maxResults=5'
    res = requests.get(url)
    items = res.json().get('items', [])
    for item in items:
        vid = item['id']['videoId']
        # 추가 검증 필요시 여기에
        return vid
    return None

def get_official_comments(video_id):
    comments = []
    page_token = None
    while True:
        params = {
            'key': YOUTUBE_API_KEY,
            'videoId': video_id,
            'part': 'snippet',
            'maxResults': 100,
            'order': 'time',
            'textFormat': 'plainText'
        }
        if page_token:
            params['pageToken'] = page_token
        r = requests.get('https://www.googleapis.com/youtube/v3/commentThreads', params=params)
        data = r.json()
        for item in data.get('items', []):
            top = item['snippet']['topLevelComment']['snippet']
            if is_official_comment(top):
                comments.append(top)
        page_token = data.get('nextPageToken')
        if not page_token:
            break
    return comments

def get_official_comments_only(video_id):
    """
    유튜브 영상에서 공식 댓글(명조/공식채널)만 페이지네이션으로 모두 가져옴
    """
    all_official_comments = []
    next_page_token = None
    while True:
        params = {
            'key': YOUTUBE_API_KEY,
            'videoId': video_id,
            'part': 'snippet,replies',
            'maxResults': 100,
            'order': 'time',
            'textFormat': 'plainText'
        }
        if next_page_token:
            params['pageToken'] = next_page_token
        resp = requests.get('https://www.googleapis.com/youtube/v3/commentThreads', params=params)
        data = resp.json()
        items = data.get('items', [])
        for item in items:
            top = item['snippet']['topLevelComment']['snippet']
            if is_official_comment(top):
                all_official_comments.append({
                    'type': 'top-level',
                    'text': top.get('textDisplay', ''),
                    'author': top.get('authorDisplayName', ''),
                    'publishedAt': top.get('publishedAt', ''),
                    'likeCount': top.get('likeCount', 0)
                })
            # 답글도 검사
            for reply in item.get('replies', {}).get('comments', []):
                reply_snippet = reply['snippet']
                if is_official_comment(reply_snippet):
                    all_official_comments.append({
                        'type': 'reply',
                        'text': reply_snippet.get('textDisplay', ''),
                        'author': reply_snippet.get('authorDisplayName', ''),
                        'publishedAt': reply_snippet.get('publishedAt', ''),
                        'likeCount': reply_snippet.get('likeCount', 0)
                    })
        next_page_token = data.get('nextPageToken')
        if not next_page_token:
            break
    return all_official_comments

def extract_rewards_text(text):
    # 보상 패턴: "보상: ...", "Reward: ...", "리워드: ...", "내용: ..." 등
    reward_patterns = [
        r"보상[:：]\s*([^\n]+)",
        r"reward[:：]\s*([^\n]+)",
        r"리워드[:：]\s*([^\n]+)",
        r"내용[:：]\s*([^\n]+)"
    ]
    for pat in reward_patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return None

def extract_codes_from_official_comments(official_comments, video_id):
    codes = []
    for comment in official_comments:
        extracted_codes = extract_codes_and_expiry(comment['text'])
        reward_text = extract_rewards_text(comment['text'])
        for code_data in extracted_codes:
            codes.append({
                **code_data,
                'commentInfo': {
                    'author': comment['author'],
                    'publishedAt': comment['publishedAt'],
                    'type': comment['type']
                },
                'reward_text': reward_text
            })
    return codes

def get_latest_youtube_official_live_archive_video_id():
    search_url = f'https://www.googleapis.com/youtube/v3/search?key={YOUTUBE_API_KEY}&channelId={CHANNEL_ID}&part=snippet&type=video&eventType=completed&order=date&maxResults=10'
    res = requests.get(search_url)
    items = res.json().get('items', [])
    for item in items:
        video_id = item['id']['videoId']
        video_res = requests.get('https://www.googleapis.com/youtube/v3/videos', params={
            'key': YOUTUBE_API_KEY,
            'id': video_id,
            'part': 'snippet,liveStreamingDetails,contentDetails'
        })
        video = video_res.json().get('items', [{}])[0]
        if video and is_actual_live_archive(video):
            return video_id
    return None

def is_actual_live_archive(video):
    live_details = video.get('liveStreamingDetails', {})
    snippet = video.get('snippet', {})
    content_details = video.get('contentDetails', {})
    def parse_duration(iso):
        import re
        m = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', iso or '')
        if not m:
            return 0
        h, m_, s = m.groups(default='0')
        return int(h) * 3600 + int(m_) * 60 + int(s)
    live_keywords = ['방송', '프리뷰', 'LIVE', '특별', '생방송', '스트리밍']
    has_live_keyword = any(
        (snippet.get('title') and kw in snippet['title']) or (snippet.get('description') and kw in snippet['description'])
        for kw in live_keywords
    )
    duration_sec = parse_duration(content_details.get('duration', 'PT0S'))
    return bool(live_details) and \
        live_details.get('actualStartTime') and \
        live_details.get('actualEndTime') and \
        content_details.get('duration', 'P0D') != 'P0D' and \
        has_live_keyword and \
        duration_sec >= 1800

def scrape_youtube_official():
    video_id = get_latest_youtube_official_live_archive_video_id()
    if not video_id:
        print('완료된 라이브 방송 아카이브를 찾을 수 없습니다.')
        return {'total': 0, 'newCodes': 0, 'codes': []}
    official_comments = get_official_comments_only(video_id)
    if not official_comments:
        print('공식 댓글 없음, 종료')
        return {'total': 0, 'newCodes': 0, 'codes': []}
    # 최상단 공식 댓글 1개만 추출
    top_official = [official_comments[0]] if official_comments else []
    extracted_codes = extract_codes_from_official_comments(top_official, video_id)
    new_codes = []
    for code_obj in extracted_codes:
        code = code_obj['code']
        expiry = code_obj['expiry']
        comment_info = code_obj['commentInfo']
        reward_text = code_obj.get('reward_text')
        rewards_field = reward_text if reward_text else ""
        if not RedeemCode.query.filter_by(code=code).first():
            rc = RedeemCode(
                game='wuthering-waves',
                code=code,
                rewards=rewards_field,
                expires_at=expiry,
                status='new'
            )
            db.session.add(rc)
            db.session.commit()
            new_codes.append(rc)
    return {
        'total': len(extracted_codes),
        'newCodes': len(new_codes),
        'codes': [rc.code for rc in new_codes],
        'allExtractedCodes': extracted_codes
    }

def save_code_to_db(code, comment):
    if RedeemCode.query.filter_by(code=code).first():
        return False
    rc = RedeemCode(
        game='wuthering-waves',
        code=code,
        rewards='',
        expires_at=None,
        status='new'
    )
    db.session.add(rc)
    db.session.commit()
    return True

def run_scraper():
    video_id = get_latest_live_video_id()
    if not video_id:
        print('No live archive found.')
        return
    comments = get_official_comments(video_id)
    if not comments:
        print('No official comments found.')
        return
    top_comment = comments[0]
    extracted = extract_codes_and_expiry(top_comment['textDisplay'])
    print('Extracted codes:', extracted)
    for code_data in extracted:
        code = code_data['code']
        expiry = code_data['expiry']
        if not RedeemCode.query.filter_by(code=code).first():
            rc = RedeemCode(
                game='wuthering-waves',
                code=code,
                rewards='',
                expires_at=expiry,
                status='new'
            )
            db.session.add(rc)
            db.session.commit()
            print(f'Saved new code: {code}')
        else:
            print(f'Code already exists: {code}')

# 사용 예시 (Flask app context에서):
# from scrapers.myungjo_youtube_scraper import run_scraper
# run_scraper()

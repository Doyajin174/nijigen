#!/usr/bin/env python3
"""
자동 라이브 스트림 모니터링 및 OCR 시스템
라이브 방송 시작을 감지하고 자동으로 코드를 수집합니다.
"""

import time
import threading
import requests
import os
from datetime import datetime, timedelta
from app import app, db
from models import RedeemCode
import cv2
import numpy as np
import pytesseract
import re
from PIL import Image, ImageGrab
import json

class LiveStreamAutoMonitor:
    def __init__(self):
        self.api_key = os.environ.get('YOUTUBE_API_KEY')
        self.is_monitoring = False
        self.current_live_streams = {}
        self.detected_codes = set()
        
        # 모니터링할 채널들
        self.channels = {
            'wuthering-waves': {
                'channel_id': 'UCKyBklhQg0tIKU3F0Ga7qvQ',  # 명조 공식 채널
                'name': '명조',
                'game': 'wuthering-waves'
            },
            'honkai-star-rail': {
                'channel_id': 'UCkCTj1z8F1SbO9vWdCGqoAA',  # 붕괴 스타레일 공식 채널  
                'name': '붕괴 스타레일',
                'game': 'honkai-star-rail'
            },
            'zenless-zone-zero': {
                'channel_id': 'UCkCTj1z8F1SbO9vWdCGqoAA',  # 젠리스 존 제로 채널
                'name': '젠리스 존 제로',
                'game': 'zenless-zone-zero'
            }
        }
        
    def check_live_streams(self):
        """모든 채널의 라이브 스트림 상태 확인"""
        if not self.api_key:
            print("YouTube API 키가 설정되지 않았습니다.")
            return {}
        
        live_streams = {}
        
        for game, channel_info in self.channels.items():
            try:
                # 채널의 라이브 스트림 검색
                search_url = f'https://www.googleapis.com/youtube/v3/search'
                params = {
                    'key': self.api_key,
                    'channelId': channel_info['channel_id'],
                    'part': 'snippet',
                    'eventType': 'live',
                    'type': 'video',
                    'maxResults': 5
                }
                
                response = requests.get(search_url, params=params)
                data = response.json()
                
                if 'items' in data and len(data['items']) > 0:
                    for item in data['items']:
                        video_id = item['id']['videoId']
                        title = item['snippet']['title']
                        live_streams[video_id] = {
                            'game': game,
                            'channel': channel_info['name'],
                            'title': title,
                            'url': f'https://www.youtube.com/watch?v={video_id}',
                            'started_at': datetime.now()
                        }
                        
                        print(f"라이브 방송 감지: {channel_info['name']} - {title}")
                
            except Exception as e:
                print(f"{channel_info['name']} 채널 확인 오류: {e}")
        
        return live_streams
    
    def get_live_chat_messages(self, video_id):
        """라이브 채팅에서 공식 메시지 확인"""
        try:
            # 라이브 채팅 ID 가져오기
            video_url = f'https://www.googleapis.com/youtube/v3/videos'
            params = {
                'key': self.api_key,
                'id': video_id,
                'part': 'liveStreamingDetails'
            }
            
            response = requests.get(video_url, params=params)
            data = response.json()
            
            if 'items' in data and len(data['items']) > 0:
                live_details = data['items'][0].get('liveStreamingDetails', {})
                chat_id = live_details.get('activeLiveChatId')
                
                if chat_id:
                    # 채팅 메시지 가져오기
                    chat_url = f'https://www.googleapis.com/youtube/v3/liveChat/messages'
                    chat_params = {
                        'key': self.api_key,
                        'liveChatId': chat_id,
                        'part': 'snippet,authorDetails',
                        'maxResults': 50
                    }
                    
                    chat_response = requests.get(chat_url, params=chat_params)
                    chat_data = chat_response.json()
                    
                    codes = []
                    if 'items' in chat_data:
                        for message in chat_data['items']:
                            author = message['authorDetails']
                            text = message['snippet']['displayMessage']
                            
                            # 공식 채널이나 모더레이터 메시지 확인
                            if (author.get('isChatOwner', False) or 
                                author.get('isChatModerator', False) or
                                '공식' in author.get('displayName', '')):
                                
                                found_codes = self.extract_codes_from_text(text)
                                codes.extend(found_codes)
                    
                    return codes
        except Exception as e:
            print(f"라이브 채팅 확인 오류: {e}")
        
        return []
    
    def extract_codes_from_text(self, text):
        """텍스트에서 리딤코드 추출"""
        text = text.upper()
        patterns = [
            r'\b[A-Z]{2,4}[0-9A-Z]{8,12}\b',
            r'\b[A-Z0-9]{10,16}\b',
            r'\b[A-Z]{3}[0-9][A-Z0-9]{8}\b',
        ]
        
        found_codes = set()
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                excluded = ['YOUTUBE', 'STREAM', 'CHANNEL', 'SUBSCRIBE']
                if not any(exc in match for exc in excluded) and len(match) >= 8:
                    found_codes.add(match)
        
        return list(found_codes)
    
    def capture_browser_screen(self, target_url):
        """브라우저 스크린샷 캡처 (헤드리스)"""
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.chrome.service import Service
            import time
            import io
            
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--disable-web-security')
            chrome_options.add_argument('--allow-running-insecure-content')
            
            # Chromium 경로 설정
            chrome_options.binary_location = '/nix/store/h3zpd9wc7pzqh4s6ip4m3jbj2c4m0x0y-chromium-129.0.6668.100/bin/chromium'
            
            driver = webdriver.Chrome(options=chrome_options)
            
            # 유튜브 라이브 페이지 열기
            driver.get(target_url)
            time.sleep(10)  # 페이지 로딩 대기
            
            # 전체 페이지 스크린샷
            screenshot = driver.get_screenshot_as_png()
            
            # PIL Image로 변환
            image = Image.open(io.BytesIO(screenshot))
            
            driver.quit()
            
            return cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            
        except Exception as e:
            print(f"브라우저 캡처 오류: {e}")
            return None
    
    def extract_codes_from_image(self, image):
        """이미지에서 OCR로 코드 추출"""
        try:
            # 이미지 전처리
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # 하단 영역만 추출 (코드가 주로 표시되는 영역)
            height, width = gray.shape
            bottom_region = gray[int(height * 0.7):, :]
            
            # 이미지 크기 확대
            scale_factor = 3
            resized = cv2.resize(bottom_region, 
                               (bottom_region.shape[1] * scale_factor, 
                                bottom_region.shape[0] * scale_factor))
            
            # 대비 향상
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(resized)
            
            # OCR 실행
            config = '--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
            text = pytesseract.image_to_string(enhanced, config=config)
            
            # 텍스트에서 코드 추출
            codes = self.extract_codes_from_text(text)
            
            return codes
            
        except Exception as e:
            print(f"OCR 처리 오류: {e}")
            return []
    
    def save_code_to_database(self, code, game, source='auto_live'):
        """데이터베이스에 코드 저장"""
        try:
            with app.app_context():
                existing = RedeemCode.query.filter_by(code=code).first()
                if existing:
                    return False
                
                new_code = RedeemCode(
                    game=game,
                    code=code,
                    rewards=f'자동 수집 ({source})',
                    expires_at=None,
                    status='new'
                )
                db.session.add(new_code)
                db.session.commit()
                
                print(f"새 코드 저장: {code} ({game})")
                return True
                
        except Exception as e:
            print(f"DB 저장 오류: {e}")
            return False
    
    def monitor_live_stream(self, video_id, stream_info):
        """특정 라이브 스트림 모니터링"""
        print(f"라이브 스트림 모니터링 시작: {stream_info['title']}")
        
        last_chat_check = datetime.now()
        last_screenshot = datetime.now()
        
        while self.is_monitoring and video_id in self.current_live_streams:
            try:
                current_time = datetime.now()
                
                # 1분마다 채팅 확인
                if (current_time - last_chat_check).seconds >= 60:
                    chat_codes = self.get_live_chat_messages(video_id)
                    for code in chat_codes:
                        if code not in self.detected_codes:
                            self.detected_codes.add(code)
                            self.save_code_to_database(code, stream_info['game'], 'live_chat')
                    last_chat_check = current_time
                
                # 30초마다 스크린샷 OCR
                if (current_time - last_screenshot).seconds >= 30:
                    screenshot = self.capture_browser_screen(stream_info['url'])
                    if screenshot is not None:
                        ocr_codes = self.extract_codes_from_image(screenshot)
                        for code in ocr_codes:
                            if code not in self.detected_codes:
                                self.detected_codes.add(code)
                                self.save_code_to_database(code, stream_info['game'], 'live_ocr')
                                
                                # 스크린샷 저장
                                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                                cv2.imwrite(f"auto_detected_{code}_{timestamp}.png", screenshot)
                    
                    last_screenshot = current_time
                
                time.sleep(10)  # 10초 대기
                
            except Exception as e:
                print(f"라이브 모니터링 오류: {e}")
                time.sleep(30)
    
    def start_monitoring(self):
        """자동 모니터링 시작"""
        print("자동 라이브 스트림 모니터링 시작")
        self.is_monitoring = True
        
        while self.is_monitoring:
            try:
                # 라이브 스트림 확인
                live_streams = self.check_live_streams()
                
                # 새로운 라이브 스트림 감지
                for video_id, stream_info in live_streams.items():
                    if video_id not in self.current_live_streams:
                        self.current_live_streams[video_id] = stream_info
                        
                        # 각 라이브 스트림을 별도 스레드에서 모니터링
                        monitor_thread = threading.Thread(
                            target=self.monitor_live_stream,
                            args=(video_id, stream_info),
                            daemon=True
                        )
                        monitor_thread.start()
                
                # 종료된 라이브 스트림 정리
                ended_streams = []
                for video_id in self.current_live_streams:
                    if video_id not in live_streams:
                        ended_streams.append(video_id)
                        print(f"라이브 스트림 종료: {self.current_live_streams[video_id]['title']}")
                
                for video_id in ended_streams:
                    del self.current_live_streams[video_id]
                
                # 5분마다 라이브 스트림 상태 확인
                time.sleep(300)
                
            except Exception as e:
                print(f"모니터링 메인 루프 오류: {e}")
                time.sleep(60)
    
    def stop_monitoring(self):
        """모니터링 중지"""
        print("자동 모니터링 중지")
        self.is_monitoring = False

# 전역 모니터 인스턴스
auto_monitor = LiveStreamAutoMonitor()

def start_auto_monitoring():
    """자동 모니터링 시작 함수"""
    monitor_thread = threading.Thread(target=auto_monitor.start_monitoring, daemon=True)
    monitor_thread.start()
    return auto_monitor

def stop_auto_monitoring():
    """자동 모니터링 중지 함수"""
    auto_monitor.stop_monitoring()

if __name__ == '__main__':
    print("자동 라이브 스트림 모니터링 시스템")
    monitor = start_auto_monitoring()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n모니터링 중지 중...")
        stop_auto_monitoring()
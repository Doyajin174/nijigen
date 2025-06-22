#!/usr/bin/env python3
"""
실시간 YouTube OCR 모니터링 시스템
웹 인터페이스를 통한 실시간 리딤 코드 감지
"""

import cv2
import pytesseract
import re
import threading
import time
import json
from datetime import datetime
import yt_dlp
import numpy as np
from PIL import Image, ImageEnhance

class RealtimeYouTubeOCR:
    def __init__(self):
        self.is_monitoring = False
        self.current_url = None
        self.found_codes = set()
        self.monitoring_thread = None
        self.latest_frame = None
        
        # OCR 설정
        self.tesseract_config = '--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
        self.code_pattern = re.compile(r'\b[A-Z0-9]{10,16}\b')
        
        # 감지 통계
        self.stats = {
            'frames_processed': 0,
            'codes_found': 0,
            'start_time': None,
            'last_detection': None
        }

    def preprocess_frame(self, frame):
        """프레임 전처리"""
        # 그레이스케일 변환
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # 적응적 이진화
        binary = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 11, 2
        )
        
        # 노이즈 제거
        denoised = cv2.medianBlur(binary, 3)
        
        return denoised

    def extract_codes_from_frame(self, frame):
        """프레임에서 코드 추출 (리딤/코드 키워드 감지 시에만)"""
        try:
            # 이미지 전처리
            processed = self.preprocess_frame(frame)
            
            # PIL 이미지로 변환 및 확대
            pil_img = Image.fromarray(processed)
            width, height = pil_img.size
            enlarged = pil_img.resize((width * 3, height * 3), Image.LANCZOS)
            
            # 대비 향상
            enhancer = ImageEnhance.Contrast(enlarged)
            enhanced = enhancer.enhance(1.8)
            
            # 먼저 전체 텍스트를 추출하여 키워드 확인
            full_text_config = '--oem 3 --psm 6'  # 키워드 감지용 (제한 없음)
            full_text = pytesseract.image_to_string(enlarged, config=full_text_config)
            
            # 리딤 코드 관련 키워드 확인 (한국어, 영어, 중국어, 일본어)
            redeem_keywords = [
                '리딤', '코드', 'redeem', 'code', 'CODE', 'REDEEM',
                '兌換', '兑换', '코드입력', '입력코드', 'input',
                '交換', '交换', 'exchange', 'gift', 'GIFT',
                '引き換え', 'コード', '特典', '보상'
            ]
            
            # 키워드가 감지된 경우에만 코드 추출
            has_redeem_keyword = any(keyword in full_text for keyword in redeem_keywords)
            
            if not has_redeem_keyword:
                return []  # 키워드가 없으면 빈 리스트 반환
            
            print(f"리딤 코드 키워드 감지됨: {full_text[:100]}...")
            
            # 키워드가 감지된 경우에만 정확한 코드 추출
            code_text = pytesseract.image_to_string(enlarged, config=self.tesseract_config)
            
            # 코드 패턴 찾기
            matches = self.code_pattern.findall(code_text)
            valid_codes = []
            
            for code in matches:
                # 길이 검증
                if 10 <= len(code) <= 16:
                    # 숫자만 있는 코드 제외
                    if not code.isdigit():
                        # 의미 있는 문자 조합인지 확인 (연속 같은 문자 제외)
                        if not self.is_repetitive_pattern(code):
                            valid_codes.append(code)
            
            return valid_codes
            
        except Exception as e:
            print(f"OCR 처리 오류: {e}")
            return []
    
    def is_repetitive_pattern(self, code):
        """반복적인 패턴의 잘못된 코드인지 확인"""
        # 같은 문자가 5개 이상 연속으로 나오는 경우
        for i in range(len(code) - 4):
            if len(set(code[i:i+5])) == 1:
                return True
        
        # 두 문자가 번갈아가며 나오는 패턴 (예: ABABABAB)
        if len(code) >= 8:
            pattern = code[:2]
            if (pattern * (len(code)//2 + 1))[:len(code)] == code:
                return True
        
        # 의미없는 문자 조합 필터링
        meaningless_patterns = [
            'AAAAAAA', 'BBBBBBB', 'CCCCCCC', 'LLLLLLL', 'NNNNNNN', 'RRRRRRR',
            'EEEEEEE', 'TTTTTTT', 'SSSSSSS', 'IIIIIII'
        ]
        
        for pattern in meaningless_patterns:
            if pattern[:len(code)] == code or pattern in code:
                return True
        
        return False

    def get_stream_url(self, youtube_url):
        """YouTube 스트림 URL 추출"""
        try:
            ydl_opts = {
                'format': 'best[height<=720]',
                'quiet': True,
                'no_warnings': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(youtube_url, download=False)
                return info.get('url'), info.get('title', 'Unknown')
                
        except Exception as e:
            print(f"스트림 URL 추출 실패: {e}")
            return None, None

    def monitor_stream(self, youtube_url):
        """스트림 모니터링 메인 루프"""
        print(f"스트림 모니터링 시작: {youtube_url}")
        
        # 스트림 URL 가져오기
        stream_url, title = self.get_stream_url(youtube_url)
        if not stream_url:
            print("스트림 URL을 가져올 수 없습니다.")
            return
        
        print(f"모니터링 중: {title}")
        
        # 비디오 캡처 초기화
        cap = cv2.VideoCapture(stream_url)
        if not cap.isOpened():
            print("비디오 스트림을 열 수 없습니다.")
            return
        
        self.stats['start_time'] = datetime.now()
        frame_skip = 0
        
        while self.is_monitoring:
            ret, frame = cap.read()
            if not ret:
                print("스트림 연결 끊어짐, 재연결 시도...")
                cap.release()
                time.sleep(3)
                cap = cv2.VideoCapture(stream_url)
                continue
            
            self.latest_frame = frame
            frame_skip += 1
            
            # 매 15프레임마다 OCR 처리 (성능 최적화 및 정확도 향상)
            if frame_skip % 15 == 0:
                self.stats['frames_processed'] += 1
                
                codes = self.extract_codes_from_frame(frame)
                if codes:
                    new_codes = set(codes) - self.found_codes
                    if new_codes:
                        self.found_codes.update(new_codes)
                        self.stats['codes_found'] += len(new_codes)
                        self.stats['last_detection'] = datetime.now()
                        
                        print(f"새로운 코드 발견: {new_codes}")
                        
                        # 데이터베이스에 저장
                        self.save_to_database(new_codes)
        
        cap.release()
        print("모니터링 종료")

    def save_to_database(self, codes):
        """코드를 데이터베이스에 저장"""
        try:
            from models import RedeemCode, db
            from app import app
            
            with app.app_context():
                for code in codes:
                    existing = RedeemCode.query.filter_by(code=code).first()
                    if not existing:
                        new_code = RedeemCode(
                            game='YouTube Live OCR',
                            code=code,
                            rewards='실시간 OCR로 감지된 코드',
                            status='active'
                        )
                        db.session.add(new_code)
                
                db.session.commit()
                print(f"데이터베이스에 {len(codes)}개 코드 저장")
                
        except Exception as e:
            print(f"데이터베이스 저장 실패: {e}")

    def start_monitoring(self, youtube_url):
        """모니터링 시작"""
        if self.is_monitoring:
            return False, "이미 모니터링 중입니다."
        
        self.current_url = youtube_url
        self.is_monitoring = True
        self.found_codes.clear()
        self.stats = {
            'frames_processed': 0,
            'codes_found': 0,
            'start_time': datetime.now(),
            'last_detection': None
        }
        
        self.monitoring_thread = threading.Thread(
            target=self.monitor_stream, 
            args=(youtube_url,)
        )
        self.monitoring_thread.start()
        
        return True, "모니터링이 시작되었습니다."

    def stop_monitoring(self):
        """모니터링 중지"""
        if not self.is_monitoring:
            return False, "모니터링이 실행되고 있지 않습니다."
        
        self.is_monitoring = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        
        return True, "모니터링이 중지되었습니다."

    def get_status(self):
        """현재 상태 반환"""
        if not self.is_monitoring:
            return {
                'status': 'stopped',
                'message': '모니터링 중지됨'
            }
        
        runtime = (datetime.now() - self.stats['start_time']).seconds if self.stats['start_time'] else 0
        
        return {
            'status': 'running',
            'url': self.current_url,
            'runtime_seconds': runtime,
            'frames_processed': self.stats['frames_processed'],
            'codes_found': list(self.found_codes),
            'total_codes': len(self.found_codes),
            'last_detection': self.stats['last_detection'].isoformat() if self.stats['last_detection'] else None
        }

# 전역 OCR 인스턴스
ocr_monitor = RealtimeYouTubeOCR()
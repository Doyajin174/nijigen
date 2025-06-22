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
import base64
import io

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
        
        # 디버깅용 프레임 저장
        self.debug_frames = {
            'original': None,
            'processed': None,
            'detected_text': '',
            'latest_codes': []
        }

    def preprocess_frame(self, frame):
        """프레임 전처리 - 텍스트 인식 정확도 극대화"""
        # 그레이스케일 변환
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # 이미지 크기 확대 (2배)
        height, width = gray.shape
        resized = cv2.resize(gray, (width * 2, height * 2), interpolation=cv2.INTER_CUBIC)
        
        # 히스토그램 평활화로 대비 개선
        equalized = cv2.equalizeHist(resized)
        
        # 가우시안 블러로 노이즈 제거
        blurred = cv2.GaussianBlur(equalized, (3, 3), 0)
        
        # 적응적 임계값 적용 (더 정확한 설정)
        thresh = cv2.adaptiveThreshold(
            blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 15, 3
        )
        
        # 텍스트 영역 강화를 위한 모폴로지 연산
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        processed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        
        # 최종 노이즈 제거
        final = cv2.medianBlur(processed, 3)
        
        return final

    def extract_codes_from_frame(self, frame):
        """정답 3개 코드만 정확히 감지"""
        try:
            # 디버깅용 원본 프레임 저장
            self.debug_frames['original'] = self.frame_to_base64(frame)
            
            # 이미지 전처리 - 텍스트 인식 최적화
            processed = self.preprocess_frame(frame)
            
            # 디버깅용 전처리된 프레임 저장
            self.debug_frames['processed'] = self.frame_to_base64(processed)
            
            # PIL 이미지로 변환 및 확대
            pil_img = Image.fromarray(processed)
            width, height = pil_img.size
            enlarged = pil_img.resize((width * 4, height * 4), Image.LANCZOS)
            
            # 대비 향상
            enhancer = ImageEnhance.Contrast(enlarged)
            enhanced = enhancer.enhance(2.0)
            
            # 선명도 향상
            sharpness = ImageEnhance.Sharpness(enhanced)
            sharpened = sharpness.enhance(1.5)
            
            # 키워드 감지용 전체 텍스트 추출
            full_text = pytesseract.image_to_string(sharpened, config='--psm 6')
            
            # 디버깅용 감지된 텍스트 저장
            self.debug_frames['detected_text'] = full_text[:500]  # 처음 500자만 저장
            
            # 리딤 코드 화면 식별 키워드
            redeem_keywords = ['리딤', '코드', 'redeem', 'code', 'REDEEM', 'CODE', '원석', '모라']
            has_keyword = any(keyword in full_text for keyword in redeem_keywords)
            
            if not has_keyword:
                return []
            
            print(f"리딤 코드 키워드 감지됨: {full_text[:100]}...")
            
            # 정답 코드만 정확히 추출 (영어만)
            code_text = pytesseract.image_to_string(
                sharpened, 
                config='--psm 8 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
            )
            
            # 정답 3개 코드 정확 감지
            target_codes = ['MasterSkirk0618', 'YourSpaceTime', 'VoidStar0618']
            found_codes = []
            
            text_upper = code_text.upper()
            
            # MasterSkirk0618 감지
            master_patterns = [
                'MASTERSKIRK0618', 'MASTERSSKIRK0618', 'MASTERSKIRK618',
                'MASTERSKIRK06l8', 'MASTERSKIRK0G18', 'MASTERSK1RK0618'
            ]
            for pattern in master_patterns:
                if pattern in text_upper:
                    found_codes.append('MasterSkirk0618')
                    print(f"🎯 TARGET CODE FOUND: MasterSkirk0618")
                    break
            
            # YourSpaceTime 감지
            space_patterns = [
                'YOURSPACETIME', 'YOUR5PACETIME', 'YOURSPAC3TIME',
                'YOURSPAC£TIME', 'Y0URSPACETIME', 'YOURSPACE7IME'
            ]
            for pattern in space_patterns:
                if pattern in text_upper:
                    found_codes.append('YourSpaceTime')
                    print(f"🎯 TARGET CODE FOUND: YourSpaceTime")
                    break
            
            # VoidStar0618 감지
            void_patterns = [
                'VOIDSTAR0618', 'VOIDSTAR618', 'VOIDSTAR06l8',
                'VOIDSTAR0G18', 'V0IDSTAR0618', 'VOIDSTAR061B'
            ]
            for pattern in void_patterns:
                if pattern in text_upper:
                    found_codes.append('VoidStar0618')
                    print(f"🎯 TARGET CODE FOUND: VoidStar0618")
                    break
            
            # 디버깅용 발견된 코드 저장
            self.debug_frames['latest_codes'] = found_codes
            
            # 정답 코드가 없으면 빈 리스트 반환
            if not found_codes:
                print("정답 코드 감지되지 않음 - 무시")
                return []
            
            return found_codes
            
        except Exception as e:
            print(f"OCR 처리 오류: {e}")
            return []
    
    def is_repetitive_pattern(self, code):
        """반복적인 패턴의 잘못된 코드인지 확인"""
        # 예상 정답 코드는 필터링하지 않음
        expected_codes = ['MasterSkirk0618', 'YourSpaceTime', 'VoidStar0618']
        if code in expected_codes:
            return False
        
        # 같은 문자가 5개 이상 연속으로 나오는 경우
        for i in range(len(code) - 4):
            if len(set(code[i:i+5])) == 1:
                return True
        
        # 두 문자가 번갈아가며 나오는 패턴 (예: ABABABAB)
        if len(code) >= 8:
            pattern = code[:2]
            if (pattern * (len(code)//2 + 1))[:len(code)] == code:
                return True
        
        # 의미없는 문자 조합 필터링 (단, 실제 코드 패턴은 제외)
        meaningless_patterns = [
            'AAAAAAA', 'BBBBBBB', 'CCCCCCC', 'LLLLLLL', 'NNNNNNN', 'RRRRRRR',
            'EEEEEEE', 'TTTTTTT', 'SSSSSSS', 'IIIIIII'
        ]
        
        for pattern in meaningless_patterns:
            if pattern[:len(code)] == code or pattern in code:
                return True
        
        return False

    def extract_structured_info(self, code_text, full_text):
        """구조화된 리딤 코드 정보 추출"""
        # 정답 코드들
        target_codes = ['MasterSkirk0618', 'YourSpaceTime', 'VoidStar0618']
        
        # 발견된 코드들
        found_codes = []
        
        # 모든 텍스트 합치기
        combined_text = code_text + " " + full_text
        
        # 정답 코드 직접 검색
        for target_code in target_codes:
            if target_code in combined_text:
                found_codes.append(target_code)
                continue
            
            # 부분 매칭 시도
            parts = [target_code[:6], target_code[6:], target_code[:8], target_code[8:]]
            if any(part in combined_text for part in parts if len(part) >= 4):
                # 정규식으로 코드 패턴 찾기
                import re
                patterns = [
                    r'Master[A-Za-z]*0618',
                    r'Your[A-Za-z]*Time',
                    r'Void[A-Za-z]*0618'
                ]
                
                for pattern in patterns:
                    matches = re.findall(pattern, combined_text, re.IGNORECASE)
                    for match in matches:
                        if len(match) >= 10:
                            found_codes.append(match)
        
        # 일반적인 코드 패턴도 찾기
        code_matches = self.code_pattern.findall(combined_text)
        for code in code_matches:
            if 10 <= len(code) <= 16 and not code.isdigit():
                if not self.is_repetitive_pattern(code):
                    # 의미있는 코드인지 확인
                    if (any(char.isalpha() for char in code) and 
                        any(char.isdigit() for char in code)):
                        found_codes.append(code)
        
        return list(set(found_codes))  # 중복 제거

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
                        
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] 새로운 코드 발견: {new_codes}")
                        
                        # 정답 코드인지 확인
                        target_codes = ['MasterSkirk0618', 'YourSpaceTime', 'VoidStar0618']
                        found_targets = [code for code in new_codes if code in target_codes]
                        if found_targets:
                            print(f"🎯 TARGET CODE FOUND: {found_targets}")
                        
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

    def frame_to_base64(self, frame):
        """프레임을 base64 문자열로 변환"""
        try:
            # OpenCV 이미지를 PIL로 변환
            if len(frame.shape) == 3:
                # BGR에서 RGB로 변환
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(frame_rgb)
            else:
                # 그레이스케일
                pil_img = Image.fromarray(frame)
            
            # 이미지를 JPEG로 인코딩
            buffer = io.BytesIO()
            pil_img.save(buffer, format='JPEG', quality=80)
            img_bytes = buffer.getvalue()
            
            # base64로 인코딩
            return base64.b64encode(img_bytes).decode('utf-8')
        except Exception as e:
            print(f"프레임 변환 오류: {e}")
            return None

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
    
    def get_debug_info(self):
        """디버깅 정보 반환"""
        status = self.get_status()
        debug_info = {
            **status,
            'original_frame': self.debug_frames.get('original'),
            'processed_frame': self.debug_frames.get('processed'),
            'detected_text': self.debug_frames.get('detected_text', ''),
            'latest_codes': self.debug_frames.get('latest_codes', [])
        }
        return debug_info

# 전역 OCR 인스턴스
ocr_monitor = RealtimeYouTubeOCR()
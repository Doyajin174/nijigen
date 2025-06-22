#!/usr/bin/env python3
"""
실시간 라이브 스트림 OCR 모니터링
명조 라이브 방송에서 리딤코드를 실시간으로 감지하고 추출합니다.
"""

import cv2
import numpy as np
import pytesseract
import time
import re
from datetime import datetime
from PIL import Image
import threading
from app import app, db
from models import RedeemCode

class LiveOCRMonitor:
    def __init__(self, roi_coords=None):
        """
        roi_coords: (x, y, width, height) - 관심 영역 좌표
        예: 화면 하단 코드 영역 (0, 600, 1920, 200)
        """
        self.roi_coords = roi_coords or (0, 600, 1920, 200)  # 기본값: 화면 하단
        self.running = False
        self.detected_codes = set()
        self.monitor_thread = None
        
        # OCR 설정
        self.ocr_config = '--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
        
        # 코드 패턴 (명조 리딤코드 형태)
        self.code_patterns = [
            r'\b[A-Z]{2,4}[0-9A-Z]{8,15}\b',  # DTJ7CVACLBGF 형태
            r'\b[A-Z0-9]{10,16}\b',           # 일반적인 코드
            r'WUTHERING[A-Z0-9]+',            # WUTHERING으로 시작
            r'WW[A-Z0-9]{6,}',                # WW로 시작
        ]
        
        # 유효기간 패턴
        self.date_patterns = [
            r'(\d{4})/(\d{1,2})/(\d{1,2})\s*(\d{1,2}):(\d{2})',
            r'(\d{4})\.(\d{1,2})\.(\d{1,2})\s*(\d{1,2}):(\d{2})',
            r'(\d{1,2})/(\d{1,2})\s*(\d{1,2}):(\d{2})',
        ]
    
    def preprocess_image(self, image):
        """이미지 전처리로 OCR 정확도 향상"""
        # 그레이스케일 변환
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # 대비 향상
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        enhanced = clahe.apply(gray)
        
        # 노이즈 제거
        denoised = cv2.bilateralFilter(enhanced, 9, 75, 75)
        
        # 이진화
        _, thresh = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # 모폴로지 연산으로 텍스트 개선
        kernel = np.ones((2,2), np.uint8)
        processed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        
        return processed
    
    def extract_text_from_image(self, image):
        """이미지에서 텍스트 추출"""
        try:
            # 이미지 전처리
            processed = self.preprocess_image(image)
            
            # OCR 실행
            text = pytesseract.image_to_string(processed, config=self.ocr_config)
            return text.strip()
        except Exception as e:
            print(f"OCR 오류: {e}")
            return ""
    
    def find_codes_in_text(self, text):
        """텍스트에서 리딤코드 추출"""
        found_codes = []
        
        for pattern in self.code_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                if len(match) >= 8 and match not in ['YOUTUBE', 'STREAM', 'CHANNEL']:
                    found_codes.append(match.upper())
        
        return list(set(found_codes))  # 중복 제거
    
    def find_expiry_in_text(self, text):
        """텍스트에서 유효기간 추출"""
        for pattern in self.date_patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    groups = match.groups()
                    if len(groups) == 5:  # 년/월/일 시:분
                        year, month, day, hour, minute = groups
                        return datetime(int(year), int(month), int(day), int(hour), int(minute))
                    elif len(groups) == 3:  # 월/일 시:분 (현재 년도)
                        month, day, hour, minute = groups[0], groups[1], groups[2], groups[3]
                        current_year = datetime.now().year
                        return datetime(current_year, int(month), int(day), int(hour), int(minute))
                except ValueError:
                    continue
        return None
    
    def capture_screen_region(self):
        """화면의 특정 영역 캡처"""
        try:
            import mss
            with mss.mss() as sct:
                monitor = {
                    "top": self.roi_coords[1],
                    "left": self.roi_coords[0], 
                    "width": self.roi_coords[2],
                    "height": self.roi_coords[3]
                }
                screenshot = sct.grab(monitor)
                image = np.array(screenshot)
                return cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
        except Exception as e:
            print(f"화면 캡처 오류: {e}")
            return None
    
    def save_code_to_database(self, code, expiry_date=None):
        """데이터베이스에 코드 저장"""
        try:
            with app.app_context():
                # 중복 확인
                existing = RedeemCode.query.filter_by(code=code).first()
                if existing:
                    return False
                
                # 새 코드 저장
                new_code = RedeemCode(
                    game='wuthering-waves',
                    code=code,
                    rewards='',  # 보상 정보는 별도로 추출 필요
                    expires_at=expiry_date,
                    status='new'
                )
                db.session.add(new_code)
                db.session.commit()
                return True
        except Exception as e:
            print(f"데이터베이스 저장 오류: {e}")
            return False
    
    def monitor_live_stream(self):
        """실시간 모니터링 메인 루프"""
        print("라이브 스트림 OCR 모니터링 시작...")
        
        while self.running:
            try:
                # 화면 캡처
                screenshot = self.capture_screen_region()
                if screenshot is None:
                    time.sleep(1)
                    continue
                
                # OCR로 텍스트 추출
                text = self.extract_text_from_image(screenshot)
                
                if text:
                    # 리딤코드 검색
                    codes = self.find_codes_in_text(text)
                    expiry = self.find_expiry_in_text(text)
                    
                    for code in codes:
                        if code not in self.detected_codes:
                            self.detected_codes.add(code)
                            
                            # 데이터베이스에 저장
                            saved = self.save_code_to_database(code, expiry)
                            
                            if saved:
                                current_time = datetime.now().strftime("%H:%M:%S")
                                print(f"[{current_time}] 새 리딤코드 발견: {code}")
                                if expiry:
                                    print(f"  유효기간: {expiry}")
                                
                                # 디버그용 이미지 저장
                                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                                cv2.imwrite(f"detected_code_{code}_{timestamp}.png", screenshot)
                
                # 2초마다 확인
                time.sleep(2)
                
            except Exception as e:
                print(f"모니터링 오류: {e}")
                time.sleep(5)
    
    def start_monitoring(self):
        """모니터링 시작"""
        if self.running:
            print("이미 모니터링이 실행 중입니다.")
            return
        
        self.running = True
        self.monitor_thread = threading.Thread(target=self.monitor_live_stream, daemon=True)
        self.monitor_thread.start()
        print("실시간 OCR 모니터링이 시작되었습니다.")
    
    def stop_monitoring(self):
        """모니터링 중지"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join()
        print("모니터링이 중지되었습니다.")
    
    def test_ocr_on_sample(self, image_path):
        """샘플 이미지로 OCR 테스트"""
        try:
            image = cv2.imread(image_path)
            if image is None:
                print(f"이미지를 불러올 수 없습니다: {image_path}")
                return
            
            # ROI 영역 추출 (필요시)
            if len(image.shape) == 3:
                roi = image[self.roi_coords[1]:self.roi_coords[1]+self.roi_coords[3], 
                           self.roi_coords[0]:self.roi_coords[0]+self.roi_coords[2]]
            else:
                roi = image
            
            # OCR 실행
            text = self.extract_text_from_image(roi)
            print(f"추출된 텍스트:\n{text}")
            
            # 코드 검색
            codes = self.find_codes_in_text(text)
            expiry = self.find_expiry_in_text(text)
            
            print(f"발견된 코드: {codes}")
            if expiry:
                print(f"유효기간: {expiry}")
            
        except Exception as e:
            print(f"테스트 오류: {e}")

# 글로벌 모니터 인스턴스
monitor = LiveOCRMonitor()

def start_live_monitoring():
    """라이브 모니터링 시작"""
    monitor.start_monitoring()

def stop_live_monitoring():
    """라이브 모니터링 중지"""
    monitor.stop_monitoring()

if __name__ == '__main__':
    # 테스트 실행
    print("실시간 OCR 모니터 테스트...")
    monitor = LiveOCRMonitor()
    
    # 샘플 이미지가 있다면 테스트
    # monitor.test_ocr_on_sample("sample_code.png")
    
    # 실시간 모니터링 시작
    monitor.start_monitoring()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n사용자에 의해 중단됨")
        monitor.stop_monitoring()
#!/usr/bin/env python3
"""
실시간 유튜브 리딤 코드 OCR 스크래퍼
YouTube 라이브 스트림에서 실시간으로 리딤 코드를 감지하고 추출하는 스크립트
"""

import cv2
import pytesseract
import re
import time
import threading
import subprocess
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
import yt_dlp
import requests
from datetime import datetime
import os
import json

class YouTubeOCRScraper:
    def __init__(self):
        # OCR 설정
        self.tesseract_config = '--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
        
        # 리딤 코드 패턴 (10-16자리 영문 대문자 + 숫자)
        self.redeem_code_pattern = re.compile(r'\b[A-Z0-9]{10,16}\b')
        
        # 발견된 코드 저장
        self.found_codes = set()
        self.running = False
        
        # ROI 설정 (화면 비율 기준)
        self.roi_regions = [
            (0.2, 0.3, 0.8, 0.7),  # 중앙 영역
            (0.1, 0.7, 0.9, 0.9),  # 하단 영역
            (0.3, 0.4, 0.7, 0.6),  # 중앙 집중 영역
        ]

    def preprocess_image(self, image):
        """이미지 전처리로 OCR 정확도 향상"""
        # 그레이스케일 변환
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        # 가우시안 블러로 노이즈 제거
        denoised = cv2.GaussianBlur(gray, (3, 3), 0)
        
        # 적응적 임계값으로 이진화
        binary = cv2.adaptiveThreshold(
            denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 11, 2
        )
        
        # 모폴로지 연산으로 텍스트 개선
        kernel = np.ones((2, 2), np.uint8)
        processed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        
        # 대비 향상
        processed = cv2.convertScaleAbs(processed, alpha=1.2, beta=10)
        
        return processed

    def extract_text_from_image(self, image):
        """이미지에서 텍스트 추출"""
        try:
            # 이미지 전처리
            processed = self.preprocess_image(image)
            
            # PIL 이미지로 변환
            pil_image = Image.fromarray(processed)
            
            # 이미지 크기 확대 (OCR 정확도 향상)
            width, height = pil_image.size
            pil_image = pil_image.resize((width * 2, height * 2), Image.LANCZOS)
            
            # 추가 이미지 향상
            enhancer = ImageEnhance.Contrast(pil_image)
            pil_image = enhancer.enhance(1.5)
            
            enhancer = ImageEnhance.Sharpness(pil_image)
            pil_image = enhancer.enhance(1.3)
            
            # OCR 실행
            text = pytesseract.image_to_string(pil_image, config=self.tesseract_config)
            return text.strip()
            
        except Exception as e:
            print(f"OCR 처리 중 오류: {e}")
            return ""

    def find_redeem_codes(self, text):
        """텍스트에서 리딤 코드 패턴 찾기"""
        if not text:
            return []
        
        # 정규식으로 리딤 코드 패턴 추출
        matches = self.redeem_code_pattern.findall(text)
        
        # 중복 제거 및 필터링
        codes = []
        for match in matches:
            # 길이 검증 (10-16자)
            if 10 <= len(match) <= 16:
                # 숫자만 있는 코드 제외 (리딤 코드는 보통 문자+숫자 조합)
                if not match.isdigit():
                    codes.append(match)
        
        return list(set(codes))

    def get_video_stream_url(self, youtube_url):
        """YouTube URL에서 스트림 URL 추출"""
        try:
            ydl_opts = {
                'format': 'best[height<=720]',  # 720p 이하로 제한 (처리 속도 향상)
                'quiet': True,
                'no_warnings': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(youtube_url, download=False)
                return info['url']
                
        except Exception as e:
            print(f"스트림 URL 추출 실패: {e}")
            return None

    def process_video_frame(self, frame):
        """비디오 프레임 처리"""
        height, width = frame.shape[:2]
        new_codes = set()
        
        # 전체 화면에서 OCR
        full_text = self.extract_text_from_image(frame)
        full_codes = self.find_redeem_codes(full_text)
        new_codes.update(full_codes)
        
        # ROI 영역별 OCR
        for roi in self.roi_regions:
            x1 = int(roi[0] * width)
            y1 = int(roi[1] * height)
            x2 = int(roi[2] * width)
            y2 = int(roi[3] * height)
            
            roi_frame = frame[y1:y2, x1:x2]
            if roi_frame.size > 0:
                roi_text = self.extract_text_from_image(roi_frame)
                roi_codes = self.find_redeem_codes(roi_text)
                new_codes.update(roi_codes)
        
        return new_codes

    def test_accuracy(self, test_url, expected_codes):
        """정확도 테스트 (최적화된 버전)"""
        print(f"정확도 테스트 시작: {test_url}")
        print(f"예상 코드: {expected_codes}")
        
        # 스트림 URL 가져오기
        stream_url = self.get_video_stream_url(test_url)
        if not stream_url:
            print("스트림 URL을 가져올 수 없습니다.")
            return False
        
        # OpenCV로 비디오 캡처
        cap = cv2.VideoCapture(stream_url)
        if not cap.isOpened():
            print("비디오를 열 수 없습니다.")
            return False
        
        found_codes = set()
        frame_count = 0
        max_frames = 1800  # 약 60초 분량으로 단축
        skip_frames = 15   # 15프레임마다 처리 (더 빠른 처리)
        
        print("프레임 분석 중...")
        
        # 더 빠른 처리를 위해 특정 시간대로 점프
        time_points = [30, 60, 120, 180, 240, 300]  # 초 단위
        
        for time_point in time_points:
            if len(found_codes) >= len(expected_codes):
                break
                
            # 특정 시간으로 점프
            cap.set(cv2.CAP_PROP_POS_MSEC, time_point * 1000)
            
            # 해당 시간대에서 30프레임 정도 분석
            for i in range(30):
                ret, frame = cap.read()
                if not ret:
                    break
                
                frame_count += 1
                
                if frame_count % 3 == 0:  # 3프레임마다 처리
                    codes = self.process_video_frame(frame)
                    if codes:
                        new_codes = codes - found_codes
                        if new_codes:
                            found_codes.update(new_codes)
                            print(f"시간 {time_point}초: 새로운 코드 발견 - {new_codes}")
                            
                            # 모든 예상 코드를 찾았는지 확인
                            if all(code in found_codes for code in expected_codes):
                                print("모든 예상 코드를 찾았습니다!")
                                break
        
        cap.release()
        
        # 결과 출력
        print(f"\n=== 테스트 결과 ===")
        print(f"처리된 프레임: {frame_count}")
        print(f"발견된 코드: {found_codes}")
        print(f"예상 코드: {set(expected_codes)}")
        
        missing_codes = set(expected_codes) - found_codes
        extra_codes = found_codes - set(expected_codes)
        
        if missing_codes:
            print(f"누락된 코드: {missing_codes}")
        if extra_codes:
            print(f"추가로 발견된 코드: {extra_codes}")
        
        # 성공 여부 판단
        success = len(missing_codes) == 0
        print(f"테스트 {'성공' if success else '실패'}")
        
        return success

    def monitor_live_stream(self, youtube_url, duration_minutes=30):
        """실시간 스트림 모니터링"""
        print(f"실시간 스트림 모니터링 시작: {youtube_url}")
        print(f"모니터링 시간: {duration_minutes}분")
        
        stream_url = self.get_video_stream_url(youtube_url)
        if not stream_url:
            print("스트림 URL을 가져올 수 없습니다.")
            return
        
        cap = cv2.VideoCapture(stream_url)
        if not cap.isOpened():
            print("비디오를 열 수 없습니다.")
            return
        
        self.running = True
        start_time = time.time()
        frame_count = 0
        
        print("실시간 모니터링 중... (Ctrl+C로 중단)")
        
        try:
            while self.running:
                # 시간 제한 확인
                if time.time() - start_time > duration_minutes * 60:
                    print(f"{duration_minutes}분 모니터링 완료")
                    break
                
                ret, frame = cap.read()
                if not ret:
                    print("스트림 연결이 끊어졌습니다. 재연결 시도...")
                    cap.release()
                    time.sleep(5)
                    cap = cv2.VideoCapture(stream_url)
                    continue
                
                frame_count += 1
                
                # 5프레임마다 처리 (실시간 성능 최적화)
                if frame_count % 5 == 0:
                    codes = self.process_video_frame(frame)
                    new_codes = codes - self.found_codes
                    
                    if new_codes:
                        self.found_codes.update(new_codes)
                        timestamp = datetime.now().strftime("%H:%M:%S")
                        print(f"[{timestamp}] 새로운 리딤 코드 발견: {new_codes}")
                        
                        # 데이터베이스에 저장
                        self.save_codes_to_db(new_codes)
        
        except KeyboardInterrupt:
            print("\n모니터링이 중단되었습니다.")
        
        finally:
            cap.release()
            self.running = False
            print(f"\n=== 모니터링 완료 ===")
            print(f"총 발견된 코드: {self.found_codes}")

    def save_codes_to_db(self, codes):
        """발견된 코드를 데이터베이스에 저장"""
        try:
            from models import RedeemCode, db
            from app import app
            
            with app.app_context():
                for code in codes:
                    # 중복 확인
                    existing = RedeemCode.query.filter_by(code=code).first()
                    if not existing:
                        new_code = RedeemCode(
                            game='원신',  # 기본값
                            code=code,
                            rewards='OCR로 자동 감지된 코드',
                            status='active'
                        )
                        db.session.add(new_code)
                
                db.session.commit()
                print(f"데이터베이스에 {len(codes)}개 코드 저장 완료")
                
        except Exception as e:
            print(f"데이터베이스 저장 실패: {e}")

def main():
    """메인 실행 함수"""
    scraper = YouTubeOCRScraper()
    
    # 테스트 케이스
    test_url = "https://www.youtube.com/watch?v=oNnLByYSzHw"
    expected_codes = ["MasterSkirk0618", "YourSpaceTime", "VoidStar0618"]
    
    print("=== YouTube OCR 스크래퍼 시작 ===")
    
    # 정확도 테스트 실행
    print("\n1. 정확도 테스트 실행")
    success = scraper.test_accuracy(test_url, expected_codes)
    
    if success:
        print("\n✓ 정확도 테스트 통과! 실시간 모니터링 기능을 사용할 수 있습니다.")
        
        # 실시간 모니터링 옵션 제공
        choice = input("\n실시간 스트림 모니터링을 시작하시겠습니까? (y/n): ").lower()
        if choice == 'y':
            live_url = input("모니터링할 YouTube URL을 입력하세요: ").strip()
            if live_url:
                scraper.monitor_live_stream(live_url)
    else:
        print("\n✗ 정확도 테스트 실패. 코드를 개선해야 합니다.")
    
    print("\n=== 스크래퍼 종료 ===")

if __name__ == "__main__":
    main()
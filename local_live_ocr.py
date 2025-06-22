#!/usr/bin/env python3
"""
로컬 컴퓨터용 실시간 라이브 OCR 모니터
독립 실행 가능한 버전으로 Flask 서버 없이 동작합니다.
"""

import cv2
import numpy as np
import pytesseract
import time
import re
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from datetime import datetime
from PIL import Image, ImageGrab
import json
import os

class LocalLiveOCR:
    def __init__(self):
        self.is_monitoring = False
        self.detected_codes = set()
        self.monitor_thread = None
        self.codes_file = "detected_codes.json"
        
        # GUI 초기화
        self.setup_gui()
        self.load_saved_codes()
        
    def setup_gui(self):
        """GUI 설정"""
        self.root = tk.Tk()
        self.root.title("실시간 라이브 OCR 모니터 (로컬용)")
        self.root.geometry("800x600")
        self.root.configure(bg='#2d2d44')
        
        # 스타일 설정
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TFrame', background='#2d2d44')
        style.configure('TLabel', background='#2d2d44', foreground='#e2e8f0', font=('Arial', 10))
        style.configure('TButton', font=('Arial', 10, 'bold'))
        
        # 메인 프레임
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # 제목
        title_label = ttk.Label(main_frame, text="실시간 라이브 OCR 모니터", font=('Arial', 16, 'bold'))
        title_label.pack(pady=(0, 20))
        
        # 설명
        info_text = """사용 방법:
1. 유튜브 라이브 스트림을 전체화면으로 시청하세요
2. "모니터링 시작" 버튼을 클릭하세요
3. 코드가 화면 하단에 나타나면 자동으로 감지됩니다
4. 감지된 코드는 자동으로 파일에 저장됩니다"""
        
        info_label = ttk.Label(main_frame, text=info_text, justify=tk.LEFT)
        info_label.pack(pady=(0, 20))
        
        # 버튼 프레임
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=(0, 20))
        
        self.start_btn = ttk.Button(button_frame, text="모니터링 시작", command=self.start_monitoring)
        self.start_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.stop_btn = ttk.Button(button_frame, text="모니터링 중지", command=self.stop_monitoring, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.test_btn = ttk.Button(button_frame, text="현재 화면 테스트", command=self.test_current_screen)
        self.test_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.clear_btn = ttk.Button(button_frame, text="로그 지우기", command=self.clear_log)
        self.clear_btn.pack(side=tk.LEFT)
        
        # 상태 표시
        self.status_var = tk.StringVar(value="대기 중")
        status_label = ttk.Label(main_frame, textvariable=self.status_var, font=('Arial', 12, 'bold'))
        status_label.pack(pady=(0, 10))
        
        # 로그 영역
        log_label = ttk.Label(main_frame, text="로그:")
        log_label.pack(anchor=tk.W)
        
        self.log_text = scrolledtext.ScrolledText(main_frame, height=15, bg='#1e1e2e', fg='#e2e8f0', 
                                                 font=('Consolas', 10), wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True, pady=(5, 0))
        
        # 발견된 코드 표시
        codes_label = ttk.Label(main_frame, text="발견된 코드:")
        codes_label.pack(anchor=tk.W, pady=(10, 0))
        
        self.codes_text = scrolledtext.ScrolledText(main_frame, height=6, bg='#1e1e2e', fg='#10b981', 
                                                   font=('Consolas', 12, 'bold'), wrap=tk.WORD)
        self.codes_text.pack(fill=tk.X, pady=(5, 0))
        
        # 초기 로그 메시지
        self.add_log("OCR 모니터링 시스템 준비 완료")
        self.add_log("Tesseract OCR이 설치되어 있는지 확인하세요")
        
    def add_log(self, message):
        """로그 추가"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"
        self.log_text.insert(tk.END, log_message)
        self.log_text.see(tk.END)
        print(f"[{timestamp}] {message}")  # 콘솔에도 출력
        
    def clear_log(self):
        """로그 지우기"""
        self.log_text.delete(1.0, tk.END)
        
    def capture_screen_area(self, x=0, y=None, width=None, height=200):
        """화면의 특정 영역 캡처"""
        try:
            # 화면 크기 자동 감지
            screen = ImageGrab.grab()
            screen_width, screen_height = screen.size
            
            if width is None:
                width = screen_width
            if y is None:
                y = screen_height - height  # 화면 하단
                
            # 지정된 영역 캡처
            screenshot = ImageGrab.grab(bbox=(x, y, x + width, y + height))
            return cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        except Exception as e:
            self.add_log(f"화면 캡처 오류: {e}")
            return None
    
    def preprocess_image(self, image):
        """OCR을 위한 이미지 전처리"""
        # 그레이스케일 변환
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # 이미지 크기 확대
        height, width = gray.shape
        scale_factor = 3
        resized = cv2.resize(gray, (width * scale_factor, height * scale_factor), 
                           interpolation=cv2.INTER_CUBIC)
        
        # 대비 향상
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(resized)
        
        # 이진화
        _, thresh1 = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        _, thresh2 = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        
        return [thresh1, thresh2]
    
    def extract_codes_from_image(self, image):
        """이미지에서 코드 추출"""
        processed_images = self.preprocess_image(image)
        all_text = []
        
        for processed in processed_images:
            try:
                # OCR 설정
                config = '--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
                text = pytesseract.image_to_string(processed, config=config)
                all_text.append(text)
            except Exception as e:
                self.add_log(f"OCR 처리 오류: {e}")
        
        # 텍스트 결합 및 정리
        combined_text = " ".join(all_text).upper()
        combined_text = re.sub(r'[^A-Z0-9\s]', '', combined_text)
        
        # 코드 패턴 검색
        patterns = [
            r'\b[A-Z]{2,4}[0-9A-Z]{8,12}\b',   # 일반 패턴
            r'\b[A-Z0-9]{10,16}\b',            # 긴 코드
            r'\b[A-Z]{3}[0-9][A-Z0-9]{8}\b',  # 특정 패턴
        ]
        
        found_codes = set()
        for pattern in patterns:
            matches = re.findall(pattern, combined_text)
            for match in matches:
                # 제외할 단어들
                excluded = ['YOUTUBE', 'STREAM', 'CHANNEL', 'SUBSCRIBE', 'HONKAI', 'WUTHERING', 'STARRAIL']
                if not any(exc in match for exc in excluded) and len(match) >= 8:
                    found_codes.add(match)
        
        return list(found_codes)
    
    def save_code(self, code):
        """코드를 파일에 저장"""
        try:
            codes_data = []
            if os.path.exists(self.codes_file):
                with open(self.codes_file, 'r', encoding='utf-8') as f:
                    codes_data = json.load(f)
            
            # 중복 체크
            existing_codes = [item['code'] for item in codes_data]
            if code not in existing_codes:
                new_entry = {
                    'code': code,
                    'detected_at': datetime.now().isoformat(),
                    'game': 'unknown'  # 게임 종류는 수동으로 설정 가능
                }
                codes_data.append(new_entry)
                
                with open(self.codes_file, 'w', encoding='utf-8') as f:
                    json.dump(codes_data, f, ensure_ascii=False, indent=2)
                
                return True
            return False
        except Exception as e:
            self.add_log(f"파일 저장 오류: {e}")
            return False
    
    def load_saved_codes(self):
        """저장된 코드 불러오기"""
        try:
            if os.path.exists(self.codes_file):
                with open(self.codes_file, 'r', encoding='utf-8') as f:
                    codes_data = json.load(f)
                
                self.codes_text.delete(1.0, tk.END)
                for item in codes_data:
                    code = item['code']
                    timestamp = item['detected_at']
                    self.codes_text.insert(tk.END, f"{code} ({timestamp})\n")
                    self.detected_codes.add(code)
                
                if codes_data:
                    self.add_log(f"저장된 {len(codes_data)}개 코드를 불러왔습니다")
        except Exception as e:
            self.add_log(f"코드 불러오기 오류: {e}")
    
    def monitor_loop(self):
        """모니터링 메인 루프"""
        self.add_log("실시간 모니터링 시작 (3초 간격)")
        
        while self.is_monitoring:
            try:
                # 화면 하단 영역 캡처
                screenshot = self.capture_screen_area()
                if screenshot is None:
                    time.sleep(3)
                    continue
                
                # 코드 추출
                codes = self.extract_codes_from_image(screenshot)
                
                if codes:
                    for code in codes:
                        if code not in self.detected_codes:
                            self.detected_codes.add(code)
                            current_time = datetime.now().strftime("%H:%M:%S")
                            
                            self.add_log(f"🎉 새 코드 발견: {code}")
                            
                            # 코드 목록에 추가
                            self.codes_text.insert(tk.END, f"{code} ({current_time})\n")
                            self.codes_text.see(tk.END)
                            
                            # 파일에 저장
                            if self.save_code(code):
                                self.add_log(f"✅ 파일에 저장됨: {code}")
                            
                            # 화면 캡처 저장 (디버그용)
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            cv2.imwrite(f"detected_{code}_{timestamp}.png", screenshot)
                            
                            # 시스템 알림 (Windows)
                            try:
                                import winsound
                                winsound.MessageBeep()
                            except:
                                pass
                
                time.sleep(3)  # 3초 대기
                
            except Exception as e:
                self.add_log(f"모니터링 오류: {e}")
                time.sleep(5)
        
        self.add_log("모니터링 중지됨")
    
    def start_monitoring(self):
        """모니터링 시작"""
        if not self.is_monitoring:
            self.is_monitoring = True
            self.status_var.set("모니터링 중...")
            self.start_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.NORMAL)
            
            # 별도 스레드에서 모니터링 시작
            self.monitor_thread = threading.Thread(target=self.monitor_loop, daemon=True)
            self.monitor_thread.start()
    
    def stop_monitoring(self):
        """모니터링 중지"""
        if self.is_monitoring:
            self.is_monitoring = False
            self.status_var.set("대기 중")
            self.start_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)
    
    def test_current_screen(self):
        """현재 화면에서 테스트"""
        self.add_log("현재 화면 테스트 중...")
        
        # 전체 화면 캡처
        full_screenshot = self.capture_screen_area(0, 0, None, None)
        # 하단 영역 캡처
        bottom_screenshot = self.capture_screen_area()
        
        if full_screenshot is not None and bottom_screenshot is not None:
            # 전체 화면에서 코드 검색
            full_codes = self.extract_codes_from_image(full_screenshot)
            # 하단 영역에서 코드 검색
            bottom_codes = self.extract_codes_from_image(bottom_screenshot)
            
            self.add_log(f"전체 화면 결과: {full_codes if full_codes else '코드 없음'}")
            self.add_log(f"하단 영역 결과: {bottom_codes if bottom_codes else '코드 없음'}")
            
            # 테스트 이미지 저장
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            cv2.imwrite(f"test_full_{timestamp}.png", full_screenshot)
            cv2.imwrite(f"test_bottom_{timestamp}.png", bottom_screenshot)
            self.add_log(f"테스트 이미지 저장됨")
        else:
            self.add_log("화면 캡처 실패")
    
    def run(self):
        """GUI 실행"""
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()
    
    def on_closing(self):
        """프로그램 종료시"""
        if self.is_monitoring:
            self.stop_monitoring()
        self.root.destroy()

if __name__ == '__main__':
    # Tesseract 설치 확인
    try:
        pytesseract.get_tesseract_version()
        print("Tesseract OCR이 설치되어 있습니다.")
    except:
        print("경고: Tesseract OCR이 설치되지 않았습니다.")
        print("설치 방법:")
        print("Windows: https://github.com/UB-Mannheim/tesseract/wiki")
        print("Mac: brew install tesseract")
        print("Linux: sudo apt-get install tesseract-ocr")
    
    # 애플리케이션 실행
    app = LocalLiveOCR()
    app.run()
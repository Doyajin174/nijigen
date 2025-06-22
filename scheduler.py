#!/usr/bin/env python3
"""
명조 유튜브 스크래퍼 자동 스케줄링
매시간마다 스크래핑을 실행하여 새로운 리딤코드를 수집합니다.
"""

import threading
import time
from datetime import datetime
from app import app
from scrapers.myungjo_youtube_scraper import scrape_youtube_official

class YoutubeScraperScheduler:
    def __init__(self, interval_hours=1):
        self.interval_hours = interval_hours
        self.interval_seconds = interval_hours * 3600
        self.running = False
        self.thread = None
        
    def start(self):
        """스케줄러 시작"""
        if self.running:
            print("스케줄러가 이미 실행 중입니다.")
            return
            
        self.running = True
        self.thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.thread.start()
        print(f"명조 유튜브 스크래퍼 스케줄러 시작 - {self.interval_hours}시간마다 실행")
        
    def stop(self):
        """스케줄러 중지"""
        self.running = False
        if self.thread:
            self.thread.join()
        print("스케줄러가 중지되었습니다.")
        
    def _run_scheduler(self):
        """스케줄러 메인 루프"""
        while self.running:
            try:
                self._execute_scraping()
                time.sleep(self.interval_seconds)
            except Exception as e:
                print(f"스케줄러 실행 중 오류 발생: {e}")
                time.sleep(60)  # 오류 발생시 1분 후 재시도
                
    def _execute_scraping(self):
        """스크래핑 실행"""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n[{current_time}] 명조 유튜브 스크래핑 시작...")
        
        try:
            with app.app_context():
                result = scrape_youtube_official()
                
                if result['total'] > 0:
                    print(f"총 {result['total']}개 코드 발견, {result['newCodes']}개 새로운 코드 저장됨")
                    if result['codes']:
                        print(f"새로운 코드: {', '.join(result['codes'])}")
                else:
                    print("새로운 코드가 발견되지 않았습니다.")
                    
        except Exception as e:
            print(f"스크래핑 실행 중 오류: {e}")
            
        print(f"[{current_time}] 스크래핑 완료. 다음 실행: {self.interval_hours}시간 후")

# 글로벌 스케줄러 인스턴스
scheduler = YoutubeScraperScheduler(interval_hours=1)

def start_scheduler():
    """스케줄러 시작 함수"""
    scheduler.start()
    
def stop_scheduler():
    """스케줄러 중지 함수"""
    scheduler.stop()

if __name__ == '__main__':
    # 스케줄러 테스트
    print("스케줄러 테스트 시작...")
    scheduler = YoutubeScraperScheduler(interval_hours=1)
    scheduler.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n사용자에 의해 중단됨")
        scheduler.stop()
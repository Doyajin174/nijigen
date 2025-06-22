# 로컬 컴퓨터에서 실시간 라이브 OCR 모니터링 설정 가이드

## 1. 필수 소프트웨어 설치

### Python 3.8+ 설치
- [Python 공식 웹사이트](https://www.python.org/downloads/)에서 다운로드
- 설치시 "Add Python to PATH" 옵션 체크

### Tesseract OCR 설치

#### Windows:
1. [Tesseract 설치 파일](https://github.com/UB-Mannheim/tesseract/wiki) 다운로드
2. 설치 후 환경변수 PATH에 추가 (보통 `C:\Program Files\Tesseract-OCR`)
3. 또는 Python에서 경로 지정:
   ```python
   pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
   ```

#### Mac:
```bash
brew install tesseract
```

#### Linux (Ubuntu/Debian):
```bash
sudo apt-get install tesseract-ocr
sudo apt-get install libtesseract-dev
```

## 2. Python 라이브러리 설치

프로젝트 폴더에서 다음 명령어 실행:

```bash
pip install -r requirements_local.txt
```

또는 개별 설치:
```bash
pip install opencv-python pytesseract Pillow numpy
```

## 3. 프로그램 실행

```bash
python local_live_ocr.py
```

## 4. 사용 방법

### 기본 사용법:
1. 프로그램 실행
2. 유튜브 라이브 스트림을 **전체화면**으로 시청
3. "모니터링 시작" 버튼 클릭
4. 코드가 화면 하단에 나타나면 자동으로 감지

### 테스트 방법:
1. "현재 화면 테스트" 버튼으로 OCR 작동 확인
2. 테스트 이미지가 저장되어 OCR 결과 확인 가능

### 감지된 코드:
- 프로그램 내에서 실시간 확인
- `detected_codes.json` 파일에 자동 저장
- 각 코드마다 스크린샷 자동 저장

## 5. 주요 기능

### 자동 감지:
- 3초마다 화면 하단 영역 스캔
- 다양한 코드 패턴 인식 (명조, 스타레일 등)
- 중복 코드 자동 필터링

### 저장 기능:
- JSON 파일로 코드 목록 저장
- 감지 시점의 스크린샷 저장
- 프로그램 재실행시 이전 코드 자동 로드

### GUI 기능:
- 실시간 로그 확인
- 감지된 코드 목록 표시
- 모니터링 시작/중지 제어
- 현재 화면 테스트 기능

## 6. 문제 해결

### Tesseract 오류:
```
TesseractNotFoundError: tesseract is not installed or it's not in your PATH
```
**해결방법:** Tesseract 설치 후 PATH 환경변수 설정

### 화면 캡처 오류:
```
화면 캡처 오류: ...
```
**해결방법:** 
- 관리자 권한으로 실행
- 보안 소프트웨어 화면 캡처 차단 해제

### 코드 감지 안됨:
- 유튜브를 전체화면으로 시청
- 코드가 화면 하단에 명확히 표시되는지 확인
- "현재 화면 테스트"로 OCR 작동 확인

## 7. 고급 설정

### 모니터링 영역 조정:
`local_live_ocr.py` 파일에서 `capture_screen_area()` 함수의 매개변수 수정:
```python
screenshot = self.capture_screen_area(x=0, y=600, width=1920, height=200)
```

### OCR 정확도 개선:
- 모니터 해상도를 1920x1080 이상 사용
- 라이브 스트림 화질을 최고로 설정
- 코드가 나타나는 영역의 배경 대비 확인

## 8. 파일 구조

```
local_live_ocr.py           # 메인 프로그램
requirements_local.txt      # 필요한 라이브러리
detected_codes.json         # 감지된 코드 저장
test_*.png                  # 테스트 스크린샷
detected_*.png              # 코드 감지시 스크린샷
```

## 9. 성능 최적화

### 시스템 요구사항:
- RAM: 4GB 이상 권장
- CPU: 듀얼코어 이상
- 디스크: 1GB 여유공간 (스크린샷 저장용)

### 성능 개선:
- 불필요한 프로그램 종료
- 가상 메모리 설정 확인
- 안티바이러스 실시간 검사 제외 폴더 설정

이제 로컬 컴퓨터에서 완전히 독립적으로 실시간 라이브 OCR 모니터링을 사용할 수 있습니다!
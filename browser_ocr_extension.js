// 브라우저 확장용 OCR 모니터링 스크립트
// 유튜브 라이브 스트림에서 리딤코드를 실시간 감지

class LiveStreamOCR {
    constructor() {
        this.isMonitoring = false;
        this.detectedCodes = new Set();
        this.canvas = document.createElement('canvas');
        this.ctx = this.canvas.getContext('2d');
        this.serverUrl = 'http://localhost:5000'; // Replit URL로 변경 필요
    }

    startMonitoring() {
        if (this.isMonitoring) return;
        
        this.isMonitoring = true;
        console.log('라이브 스트림 OCR 모니터링 시작');
        
        // 5초마다 화면 캡처 및 분석
        this.monitorInterval = setInterval(() => {
            this.captureAndAnalyze();
        }, 5000);
    }

    stopMonitoring() {
        this.isMonitoring = false;
        if (this.monitorInterval) {
            clearInterval(this.monitorInterval);
        }
        console.log('라이브 스트림 OCR 모니터링 중지');
    }

    captureAndAnalyze() {
        const video = document.querySelector('video');
        if (!video) return;

        // 비디오 프레임을 캔버스에 캡처
        this.canvas.width = video.videoWidth;
        this.canvas.height = video.videoHeight;
        this.ctx.drawImage(video, 0, 0);

        // 하단 영역만 추출 (코드가 주로 하단에 표시됨)
        const bottomRegion = this.ctx.getImageData(
            0, 
            this.canvas.height * 0.7, 
            this.canvas.width, 
            this.canvas.height * 0.3
        );

        // OCR 처리를 위해 서버로 전송
        this.sendForOCR(bottomRegion);
    }

    async sendForOCR(imageData) {
        try {
            // 이미지 데이터를 base64로 변환
            const canvas = document.createElement('canvas');
            canvas.width = imageData.width;
            canvas.height = imageData.height;
            const ctx = canvas.getContext('2d');
            ctx.putImageData(imageData, 0, 0);
            
            const base64 = canvas.toDataURL('image/png');
            
            // 서버로 OCR 요청
            const response = await fetch(`${this.serverUrl}/api/process-ocr`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    image: base64,
                    timestamp: new Date().toISOString()
                })
            });

            const result = await response.json();
            
            if (result.codes && result.codes.length > 0) {
                result.codes.forEach(code => {
                    if (!this.detectedCodes.has(code)) {
                        this.detectedCodes.add(code);
                        this.notifyCodeDetected(code, result.expiry);
                    }
                });
            }
        } catch (error) {
            console.error('OCR 처리 오류:', error);
        }
    }

    notifyCodeDetected(code, expiry) {
        console.log(`새 리딤코드 발견: ${code}`);
        if (expiry) {
            console.log(`유효기간: ${expiry}`);
        }
        
        // 브라우저 알림
        if (Notification.permission === 'granted') {
            new Notification('새 리딤코드 발견!', {
                body: `코드: ${code}${expiry ? `\n유효기간: ${expiry}` : ''}`,
                icon: '/favicon.ico'
            });
        }
        
        // 페이지에 오버레이 표시
        this.showCodeOverlay(code, expiry);
    }

    showCodeOverlay(code, expiry) {
        // 오버레이 요소 생성
        const overlay = document.createElement('div');
        overlay.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: rgba(0, 0, 0, 0.9);
            color: #00ff00;
            padding: 15px;
            border-radius: 8px;
            z-index: 9999;
            font-family: monospace;
            font-size: 16px;
            border: 2px solid #00ff00;
        `;
        
        overlay.innerHTML = `
            <div>🎁 새 리딤코드 발견!</div>
            <div style="font-size: 20px; font-weight: bold; margin: 10px 0;">${code}</div>
            ${expiry ? `<div>⏰ 유효기간: ${expiry}</div>` : ''}
            <button onclick="this.parentElement.remove()" style="
                background: #00ff00;
                color: black;
                border: none;
                padding: 5px 10px;
                border-radius: 4px;
                margin-top: 10px;
                cursor: pointer;
            ">확인</button>
        `;
        
        document.body.appendChild(overlay);
        
        // 10초 후 자동 제거
        setTimeout(() => {
            if (overlay.parentElement) {
                overlay.remove();
            }
        }, 10000);
    }
}

// 북마클릿 또는 확장 프로그램에서 사용
const liveOCR = new LiveStreamOCR();

// 키보드 단축키로 모니터링 시작/중지
document.addEventListener('keydown', (e) => {
    if (e.ctrlKey && e.shiftKey && e.key === 'O') {
        if (liveOCR.isMonitoring) {
            liveOCR.stopMonitoring();
        } else {
            liveOCR.startMonitoring();
        }
    }
});

console.log('라이브 스트림 OCR 모니터 로드됨. Ctrl+Shift+O로 시작/중지');
# ASMR 자동 자막 생성기

> ASMR 속삭임 음성에 최적화된 자동 자막(SRT) 추출 도구  
> **faster-whisper** 기반, NVIDIA GPU 자동 가속 지원

---

## 스크린샷

| 파일 추가 & 설정 | 배치 처리 중 |
|---|---|
| *(main.py 실행 화면)* | *(자막 생성 진행)* |

---

## 주요 기능

- **ASMR 최적화** — 속삭임 전용 프롬프트, VAD 필터 적용
- **GPU 자동 가속** — NVIDIA CUDA 감지 시 자동 전환 (RTX 시리즈 권장)
- **배치 처리** — 여러 파일 한 번에 처리
- **노이즈 제거** — 배경 잡음 감소 옵션 내장
- **다국어 지원** — 일본어·한국어·영어·중국어·자동 감지
- **SRT 출력** — 오디오 파일과 동일 위치에 `.srt` 저장

---

## 파일 구성

```
ASMR_translation/
├── main.py              # GUI 엔트리포인트
├── transcriber.py       # Whisper STT 핵심 로직
├── audio_processor.py   # 오디오 전처리 (노이즈 제거, 정규화)
├── requirements.txt     # 의존성 목록
├── setup.bat            # 기본 설치 스크립트 (CPU)
└── setup_gpu.bat        # GPU(CUDA) 설치 스크립트
```

---

## 설치

### 사전 요구사항

- **Python 3.9 이상** ([python.org](https://www.python.org))
- **FFmpeg** — MP3·M4A 포맷 지원 시 필요 ([ffmpeg.org](https://ffmpeg.org/download.html))
  - 설치 후 시스템 PATH에 추가

### CPU 환경

```bat
setup.bat
```

### GPU 환경 (NVIDIA CUDA)

```bat
:: 1단계: 기본 의존성 설치
setup.bat

:: 2단계: CUDA 가속 설치 (PyTorch CUDA 12.4)
setup_gpu.bat
```

> **드라이버 요구사항**: CUDA 12.x 호환 드라이버 (≥ 드라이버 525)  
> RTX 20xx 이상 권장

### 수동 설치

```bash
pip install faster-whisper soundfile noisereduce numpy librosa
```

---

## 실행

```bash
python main.py
```

또는 파일을 직접 인자로 전달:

```bash
python main.py audio1.wav audio2.flac
```

---

## 사용 방법

1. **`python main.py`** 실행
2. **`＋ 파일 추가`** 또는 **`＋ 폴더 추가`** 로 오디오 파일 등록
3. **모델 크기** 선택
   | 모델 | 속도 | 정확도 | 권장 상황 |
   |---|---|---|---|
   | `tiny` / `base` | ★★★★★ | ★★☆ | 빠른 테스트 |
   | `small` / `medium` | ★★★☆ | ★★★★ | 일반 사용 |
   | `large-v3-turbo` | ★★★☆ | ★★★★★ | **ASMR 권장** |
   | `large-v3` | ★★☆ | ★★★★★ | 최고 정확도 |
4. **언어** 선택 (일본어 ASMR이면 `日本語`)
5. **노이즈 제거** 옵션 체크 (배경 잡음이 많을 때)
6. **`▶ 자막 생성 시작`** 클릭
7. 완료 후 오디오 파일과 같은 폴더에 `.srt` 파일 생성됨

---

## 출력 예시

```
📁 오디오 폴더/
├── track01.wav
├── track01.srt          ← 생성됨 (원본 언어)
├── track02.wav
└── track02.srt          ← 생성됨
```

---

## 지원 오디오 포맷

| 포맷 | 비고 |
|---|---|
| `.wav` | 기본 지원 |
| `.flac` | 무손실, 기본 지원 |
| `.mp3` | FFmpeg 필요 |
| `.m4a` | FFmpeg 필요 |
| `.ogg` | 기본 지원 |
| `.aac` | FFmpeg 필요 |
| `.opus` | FFmpeg 필요 |

---

## 번역 플러그인 연동

생성된 `.srt` 파일을 다국어로 번역하려면 `plugin/translate` 폴더의 번역기를 사용하세요.  
Gemini 웹 자동화 기반으로 **API 키 없이** 번역 가능합니다.

```bash
cd plugin/translate
setup.bat     # 최초 1회
python translate_app.py
```

번역 결과: `파일명_ko.srt`, `파일명_en.srt` 등으로 저장됩니다.

---

## 의존성

| 패키지 | 버전 | 용도 |
|---|---|---|
| `faster-whisper` | ≥ 1.0.0 | 음성 인식 (STT) |
| `soundfile` | ≥ 0.12.1 | 오디오 파일 읽기 |
| `noisereduce` | ≥ 3.0.2 | 노이즈 제거 |
| `numpy` | ≥ 1.24.0 | 오디오 배열 처리 |
| `librosa` | ≥ 0.10.0 | MP3·M4A 포맷 지원 (선택) |
| `torch` (CUDA) | — | GPU 가속 (선택) |

---

## 라이선스

MIT

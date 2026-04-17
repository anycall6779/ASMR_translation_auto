# ASMR 영상 합성기

> 오디오 + 정지 이미지 + SRT 자막 → **무손실 MKV 영상** 생성 도구  
> NVIDIA GPU 가속, 하드 번인 자막, 다국어 SRT 자동 탐지 지원

---

## 주요 기능

- **무손실 인코딩** — NVIDIA h264_nvenc lossless (GPU) / libx264 -crf 0 (CPU)
- **무손실 오디오** — FLAC 코덱으로 원본 음질 보존
- **자막 하드 번인** — FFmpeg `subtitles` 필터로 영상에 직접 삽입
- **문장 자동 분리** — 한 블록에 여러 문장이 있으면 자동으로 나눔 + 시간 비례 배분
- **CJK 줄바꿈** — 일본어·한국어·한자 22자 단위 자동 줄바꿈
- **다국어 SRT 자동 탐지** — 번역 플러그인 출력(`_ko.srt`, `_en.srt` 등) 우선 연결
- **배치 처리** — 여러 파일 쌍을 한 번에 변환

---

## 파일 구성

```
video_combine/
├── video_app.py         # GUI 엔트리포인트
├── video_maker.py       # FFmpeg 영상 합성 핵심 로직
└── (출력) video_make/   # 생성된 MKV 파일 저장 위치
```

---

## 설치

### 사전 요구사항

- **Python 3.9 이상** ([python.org](https://www.python.org))
- **FFmpeg** — 필수 ([ffmpeg.org](https://ffmpeg.org/download.html))
  - 다운로드 후 시스템 PATH에 추가, 또는 아래 명령으로 자동 설치:
    ```bash
    pip install imageio-ffmpeg
    ```
- **NVIDIA 드라이버** — GPU 가속 사용 시 필요 (선택)

### Python 의존성

```bash
pip install imageio-ffmpeg   # FFmpeg PATH에 없을 때
```

> `tkinter`는 Python 내장이므로 별도 설치 불필요

---

## 실행

```bash
python video_app.py
```

---

## 사용 방법

### 기본 흐름

1. **`python video_app.py`** 실행
2. **`＋ 오디오 추가`** 또는 **`＋ 폴더 추가`** 로 오디오 파일 등록  
   → SRT 파일을 자동으로 연결 (아래 [SRT 자동 탐지](#srt-자동-탐지) 참고)
3. **배경 이미지** 선택 (`.jpg` / `.png` / `.webp` 등)
4. **자막 설정** 조정
   - 자막 크기: 14 ~ 48pt (기본 22)
   - 자막 색상: 흰색 / 노란색 / 하늘색
   - 자막 언어 우선순위: 한국어 / English / 日本語 / 中文 / 원본
5. **`▶ 영상 생성 시작`** 클릭
6. 완료 후 `video_make/` 폴더에 `.mkv` 파일 생성됨

---

### SRT 자동 탐지

오디오 파일을 추가하면 다음 순서로 SRT 파일을 자동으로 찾습니다:

| 우선순위 | 탐색 파일 | 예시 |
|---|---|---|
| 1순위 | 선호 언어 번역본 | `track01_ko.srt` |
| 2순위 | 다른 번역 언어본 | `track01_en.srt`, `track01_ja.srt` |
| 3순위 | 원본 SRT | `track01.srt` |

> 번역 플러그인(`plugin/translate`)으로 생성한 다국어 SRT를 자동으로 인식합니다.  
> **`SRT 자동 연결`** 버튼으로 언제든 재탐색할 수 있습니다.

---

### 출력 결과

```
📁 ASMR/
└── video_make/
    ├── track01.mkv      ← 생성됨
    ├── track02.mkv      ← 생성됨
    └── ...
```

| 항목 | 내용 |
|---|---|
| 컨테이너 | MKV |
| 영상 코덱 | h264_nvenc lossless (GPU) / libx264 -crf 0 (CPU) |
| 오디오 코덱 | FLAC (무손실) |
| 자막 | 하드 번인 (영상에 직접 삽입) |

---

## 자막 처리 상세

### 문장 자동 분리

SRT 블록 안에 `。！？!?` 로 끝나는 문장이 여러 개 있으면 자동으로 분리합니다.

```
[원본 블록]
1
00:00:05,000 --> 00:00:10,000
お疲れ様です。今日もよろしくお願いします。

        ↓ 자동 분리

1
00:00:05,000 --> 00:00:07,500
お疲れ様です。

2
00:00:07,500 --> 00:00:10,000
今日もよろしくお願いします。
```

### CJK 자동 줄바꿈

- 일본어·한국어·한자: **22자** 단위 강제 줄바꿈
- 영어: 단어 단위 줄바꿈 (최대 40자)

---

## 번역 플러그인 연동

`plugin/translate` 폴더의 번역기와 함께 사용하면 다국어 자막 영상을 만들 수 있습니다.

```
[작업 흐름]

1. 자막 추출기(main.py) → track01.srt 생성
2. 번역기(translate_app.py) → track01_ko.srt 생성
3. 영상 합성기(video_app.py) → 자막 언어 "한국어" 선택
   → track01_ko.srt 자동 인식 후 MKV 생성
```

---

## 지원 오디오 포맷

`.wav` · `.mp3` · `.flac` · `.m4a` · `.ogg` · `.aac` · `.opus`

---

## 지원 이미지 포맷

`.jpg` · `.jpeg` · `.png` · `.webp` · `.bmp`

---

## 트러블슈팅

| 증상 | 해결 방법 |
|---|---|
| `FFmpeg를 찾을 수 없습니다` | FFmpeg PATH 추가 또는 `pip install imageio-ffmpeg` |
| GPU 인식 안 됨 | NVIDIA 드라이버 최신화, CUDA 버전 확인 |
| 자막이 표시 안 됨 | SRT 파일 경로에 한글/일본어 포함 여부 확인 (자동 처리됨) |
| 영상이 너무 큼 | GPU 없는 경우 libx264 -crf 0은 파일이 큼 — 정상 |

---

## 라이선스

MIT

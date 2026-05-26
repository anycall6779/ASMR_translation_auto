#!/data/data/com.termux/files/usr/bin/bash
# ASMR Studio — Termux 설치 스크립트 (컴파일 완전 차단)

set -e
echo "========================================"
echo "  ASMR Studio — Termux 환경 설치"
echo "========================================"
echo ""

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# ── 1단계: pkg 사전 컴파일 바이너리 ─────────────────────────
echo "[1/4] 시스템 패키지 설치 (사전 컴파일 — 컴파일 없음)..."
pkg update -y
pkg install -y \
    python \
    ffmpeg \
    libsndfile \
    git \
    python-numpy \
    python-scipy \
    python-cffi

# ── 2단계: pip — 바이너리 전용 설치 ─────────────────────────
# --only-binary=:all: → 소스 컴파일/빌드 의존성 설치 완전 차단
echo ""
echo "[2/4] pip 패키지 설치 (바이너리 전용 — 컴파일 없음)..."

pip install --only-binary=:all: flask
pip install --only-binary=:all: deep-translator
pip install --only-binary=:all: soundfile
pip install --only-binary=:all: noisereduce

# ── 3단계: Whisper ────────────────────────────────────────────
echo ""
echo "[3/4] Whisper STT 설치..."

# faster-whisper: 바이너리 없으면 openai-whisper 시도
pip install --only-binary=:all: faster-whisper 2>/dev/null && {
    echo "  ✓ faster-whisper 설치됨"
} || {
    echo "  faster-whisper 바이너리 없음 → openai-whisper 시도..."
    pip install --only-binary=:all: openai-whisper 2>/dev/null || {
        echo "  ⚠ 둘 다 바이너리 없음. 수동 설치 필요:"
        echo "    pip install faster-whisper"
        echo "  (이 경우 빌드 시간 소요됨)"
    }
}

# ── 4단계: ASMRT 단축 명령 ────────────────────────────────────
echo ""
echo "[4/4] ASMRT 단축 명령 등록..."

BASHRC="$HOME/.bashrc"
ALIAS_LINE="alias ASMRT='cd \"$SCRIPT_DIR\" && bash run.sh'"

if grep -q "alias ASMRT=" "$BASHRC" 2>/dev/null; then
    sed -i "/alias ASMRT=/c\\$ALIAS_LINE" "$BASHRC"
    echo "  ASMRT 단축 명령 업데이트됨"
else
    echo "" >> "$BASHRC"
    echo "# ASMR Studio 단축 명령" >> "$BASHRC"
    echo "$ALIAS_LINE" >> "$BASHRC"
    echo "  ASMRT 단축 명령 등록됨"
fi

echo ""
echo "========================================"
echo "  설치 완료!"
echo ""
echo "  지금 바로 실행:  bash run.sh"
echo "  단축 명령 적용:  source ~/.bashrc"
echo "  다음부터 실행:   ASMRT"
echo "========================================"

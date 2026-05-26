#!/data/data/com.termux/files/usr/bin/bash
# ASMR Studio — Termux 설치 스크립트 (빌드 완전 차단)

set -e
echo "========================================"
echo "  ASMR Studio — Termux 환경 설치"
echo "========================================"
echo ""

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# ── 1단계: pkg 바이너리 ────────────────────────────────────────
echo "[1/4] 시스템 패키지 설치..."
pkg update -y
pkg install -y python ffmpeg libsndfile git

# ── 2단계: pip 핵심 패키지 (빌드 없음) ────────────────────────
echo ""
echo "[2/4] pip 패키지 설치 (빌드 없음)..."

pip install flask
pip install deep-translator

# soundfile: 바이너리 전용 시도 → 안되면 --no-deps (cffi는 이미 설치됨)
pip install --only-binary=:all: soundfile 2>/dev/null || \
pip install soundfile --no-deps 2>/dev/null || \
echo "  ⚠ soundfile 스킵 (MP3/M4A 제외 WAV/FLAC만 사용 가능)"

# scipy + noisereduce: 바이너리 전용, 빌드 시도 절대 안 함
echo ""
echo "  [노이즈감소] scipy 바이너리 확인 중..."
pip install --only-binary=:all: scipy 2>/dev/null && {
    pip install noisereduce --no-deps 2>/dev/null && \
    echo "  ✓ 노이즈 감소 기능 활성화됨" || true
} || {
    echo "  ⚠ scipy 바이너리 없음 — 노이즈 감소 기능 비활성화"
    echo "    STT / 번역 / 영상 기능은 정상 작동"
}

# ── 3단계: Whisper ────────────────────────────────────────────
echo ""
echo "[3/4] Whisper STT 설치..."
pip install --only-binary=:all: faster-whisper 2>/dev/null && {
    echo "  ✓ faster-whisper 설치됨"
} || {
    echo "  ⚠ faster-whisper 바이너리 없음"
    echo "    STT 사용 전 수동 설치: pip install faster-whisper"
}

# ── 4단계: ASMRT 단축 명령 ────────────────────────────────────
echo ""
echo "[4/4] ASMRT 단축 명령 등록..."

BASHRC="$HOME/.bashrc"
ALIAS_LINE="alias ASMRT='cd \"$SCRIPT_DIR\" && bash run.sh'"

if grep -q "alias ASMRT=" "$BASHRC" 2>/dev/null; then
    sed -i "/alias ASMRT=/c\\$ALIAS_LINE" "$BASHRC"
    echo "  업데이트됨"
else
    { echo ""; echo "# ASMR Studio"; echo "$ALIAS_LINE"; } >> "$BASHRC"
    echo "  등록됨"
fi

echo ""
echo "========================================"
echo "  설치 완료!"
echo "  지금 실행:       bash run.sh"
echo "  단축 명령 적용:  source ~/.bashrc"
echo "  다음부터:        ASMRT"
echo "========================================"

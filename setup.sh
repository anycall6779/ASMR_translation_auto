#!/data/data/com.termux/files/usr/bin/bash
# ASMR Studio — Termux 설치 (컴파일/빌드 완전 없음)

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

# ── 2단계: pip 순수 Python 패키지만 ───────────────────────────
echo ""
echo "[2/4] pip 패키지 설치..."

pip install flask
pip install deep-translator

# soundfile: 바이너리 전용, 실패하면 스킵
pip install --only-binary=:all: soundfile 2>/dev/null \
    && echo "  ✓ soundfile" \
    || echo "  ⚠ soundfile 스킵 (WAV만 지원)"

# noisereduce / scipy → ARM64 바이너리 없음 → 완전 제거
# audio_processor.py가 미설치 시 자동 스킵 처리함
echo "  [노이즈감소] scipy ARM 바이너리 없음 — 기능 비활성화 (앱 정상 동작)"

# ── 3단계: Whisper ────────────────────────────────────────────
echo ""
echo "[3/4] Whisper STT 설치..."
pip install --only-binary=:all: faster-whisper 2>/dev/null \
    && echo "  ✓ faster-whisper" \
    || echo "  ⚠ faster-whisper 바이너리 없음 — 사용 전 수동 설치 필요"

# ── 4단계: ASMRT 단축 명령 ────────────────────────────────────
echo ""
echo "[4/4] ASMRT 단축 명령 등록..."
BASHRC="$HOME/.bashrc"
ALIAS_LINE="alias ASMRT='cd \"$SCRIPT_DIR\" && bash run.sh'"
if grep -q "alias ASMRT=" "$BASHRC" 2>/dev/null; then
    sed -i "/alias ASMRT=/c\\$ALIAS_LINE" "$BASHRC"
else
    { echo ""; echo "# ASMR Studio"; echo "$ALIAS_LINE"; } >> "$BASHRC"
fi
echo "  ✓ ASMRT 등록됨"

echo ""
echo "========================================"
echo "  설치 완료!"
echo "  지금 실행:       bash run.sh"
echo "  단축 명령 적용:  source ~/.bashrc"
echo "  다음부터:        ASMRT"
echo "========================================"

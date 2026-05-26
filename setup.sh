#!/data/data/com.termux/files/usr/bin/bash
# ASMR Studio — Termux 설치 스크립트 (빌드 완전 차단)

set -e
echo "========================================"
echo "  ASMR Studio — Termux 환경 설치"
echo "========================================"
echo ""

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# ── 1단계: pkg 바이너리 (컴파일 없음) ─────────────────────────
echo "[1/4] 시스템 패키지 설치..."
pkg update -y
pkg install -y python ffmpeg libsndfile git python-numpy python-scipy

# cffi: pkg에 있으면 설치 (soundfile 런타임 의존), 없어도 계속
pkg install -y python-cffi 2>/dev/null || true

# ── 2단계: 순수 Python 패키지만 pip 설치 ─────────────────────
# --no-deps : pip이 C 의존성(scipy/cffi 등)을 추가로 당겨오는 것 차단
# 런타임 의존성(numpy/scipy/cffi)은 위에서 pkg로 이미 설치됨
echo ""
echo "[2/4] pip 패키지 설치 (빌드 없음)..."

pip install flask
pip install deep-translator

# soundfile: 휠 자체는 순수 Python, cffi/libsndfile은 pkg에서 제공
pip install soundfile --no-deps

# noisereduce: 휠은 순수 Python, scipy/numpy는 pkg에서 제공
pip install noisereduce --no-deps

# ── 3단계: Whisper ────────────────────────────────────────────
echo ""
echo "[3/4] Whisper STT 설치..."

# 바이너리 전용 시도 → 없으면 스킵 (사용자가 나중에 따로 설치 가능)
pip install --only-binary=:all: faster-whisper 2>/dev/null && {
    echo "  ✓ faster-whisper 설치됨"
} || {
    echo "  ⚠ faster-whisper 바이너리 없음 — 앱은 실행 가능"
    echo "    STT 사용 전 수동 설치:  pip install faster-whisper"
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
echo "  지금 바로 실행:  bash run.sh"
echo "  단축 명령 적용:  source ~/.bashrc"
echo "  다음부터 실행:   ASMRT"
echo "========================================"

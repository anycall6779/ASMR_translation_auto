#!/data/data/com.termux/files/usr/bin/bash
# ASMR Studio — Termux 설치 스크립트 (빠른 설치 최적화)

set -e
echo "========================================"
echo "  ASMR Studio — Termux 환경 설치"
echo "========================================"
echo ""

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "[1/4] 시스템 패키지 설치 (사전 컴파일 바이너리)..."
pkg update -y
# numpy, scipy를 pkg로 설치 → pip 컴파일 불필요 (핵심 속도 개선)
pkg install -y python ffmpeg libsndfile git python-numpy python-scipy

echo ""
echo "[2/4] 경량 pip 패키지 설치..."
# --prefer-binary: 소스 컴파일 대신 바이너리 휠 우선 사용
pip install --prefer-binary flask
pip install --prefer-binary deep-translator
pip install --prefer-binary soundfile
pip install --prefer-binary noisereduce   # scipy는 이미 pkg로 설치됨

echo ""
echo "[3/4] Whisper STT 설치..."
pip install --prefer-binary faster-whisper || {
    echo "faster-whisper 실패 → openai-whisper 시도..."
    pip install --prefer-binary openai-whisper
}

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

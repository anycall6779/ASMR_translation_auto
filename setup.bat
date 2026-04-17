@echo off
chcp 65001 > nul
title ASMR 자동 자막 생성기 - 의존성 설치

echo ============================================
echo   ASMR 자막 생성기 - 의존성 설치
echo ============================================
echo.

:: Python 확인
python --version > nul 2>&1
if errorlevel 1 (
    echo [오류] Python이 설치되지 않았거나 PATH에 없습니다.
    echo https://www.python.org 에서 설치 후 재시도하세요.
    pause
    exit /b 1
)

echo [1/4] pip 업그레이드...
python -m pip install --upgrade pip

echo.
echo [2/4] faster-whisper 설치 (CUDA GPU 있으면 자동 가속)...
pip install faster-whisper

echo.
echo [3/4] 오디오 처리 라이브러리 설치...
pip install soundfile noisereduce numpy

echo.
echo [4/4] MP3/M4A 포맷 지원 (librosa) 설치...
pip install librosa

echo.
echo ============================================
echo   설치 완료!
echo   run.bat 으로 프로그램을 실행하세요.
echo ============================================
pause

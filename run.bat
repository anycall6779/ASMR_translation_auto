@echo off
chcp 65001 > nul
title ASMR 자동 자막 생성기

:: 이 배치 파일이 있는 디렉터리로 이동
cd /d "%~dp0"

:: Python 확인
python --version > nul 2>&1
if errorlevel 1 (
    echo [오류] Python을 찾을 수 없습니다. setup.bat을 먼저 실행하세요.
    pause
    exit /b 1
)

:: faster-whisper 설치 여부 확인
python -c "import faster_whisper" > nul 2>&1
if errorlevel 1 (
    echo [경고] faster-whisper가 설치되지 않았습니다.
    echo setup.bat을 실행하여 의존성을 설치해주세요.
    echo.
    set /p SETUP="지금 바로 설치할까요? (Y/N): "
    if /i "%SETUP%"=="Y" (
        call setup.bat
    )
)

python main.py %*

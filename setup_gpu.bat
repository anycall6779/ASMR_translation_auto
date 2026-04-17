@echo off
chcp 65001 > nul
title ASMR 자막 생성기 - GPU(CUDA) 설정

echo ============================================
echo   GPU(CUDA) 지원 설치
echo   감지된 GPU: NVIDIA GeForce RTX 2060
echo   드라이버 CUDA: 13.1 -> CUDA 12.x 호환
echo ============================================
echo.

:: PyTorch CPU 버전 제거
echo [1/4] 기존 CPU 전용 PyTorch 제거...
pip uninstall torch torchvision torchaudio -y

:: PyTorch CUDA 12.4 버전 설치 (드라이버 591 이상이면 호환됨)
echo.
echo [2/4] PyTorch CUDA 12.4 버전 설치 중... (약 2GB, 시간이 걸립니다)
pip install torch --index-url https://download.pytorch.org/whl/cu124

:: ctranslate2 CUDA 지원 버전 재설치
echo.
echo [3/4] ctranslate2 CUDA 지원 버전 재설치...
pip uninstall ctranslate2 -y
pip install ctranslate2

:: 설치 확인
echo.
echo [4/4] GPU 인식 확인...
python -c "import torch; print('CUDA 사용 가능:', torch.cuda.is_available()); print('GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else '미감지')"

echo.
echo ============================================
echo   완료! run.bat 으로 프로그램을 실행하세요.
echo   CUDA 사용 가능: True 가 뜨면 성공입니다.
echo ============================================
pause

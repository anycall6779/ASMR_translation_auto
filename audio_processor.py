# -*- coding: utf-8 -*-
"""
ASMR 오디오 전처리 모듈
- 스테레오 → 모노 변환
- 노이즈 감소 (noisereduce)
- 정규화
"""

import numpy as np


def load_audio(file_path: str):
    """
    오디오 파일 로드 (WAV / MP3 / FLAC / M4A 등)
    반환: (audio: np.ndarray float32, sample_rate: int)
    """
    try:
        import soundfile as sf
        audio, sr = sf.read(str(file_path), dtype="float32", always_2d=False)
    except Exception:
        # soundfile이 지원하지 않는 형식(mp3 등)은 librosa로 폴백
        import librosa
        audio, sr = librosa.load(str(file_path), sr=None, mono=False)
        audio = np.asarray(audio, dtype=np.float32)

    # 스테레오 / 멀티채널 → 모노 (채널 평균)
    if audio.ndim > 1:
        # soundfile: (samples, channels), librosa: (channels, samples)
        if audio.shape[0] < audio.shape[1]:
            # librosa 형태
            audio = audio.mean(axis=0)
        else:
            audio = audio.mean(axis=1)

    return audio.astype(np.float32), sr


def apply_denoise(audio: np.ndarray, sr: int, strength: float = 0.55) -> np.ndarray:
    """
    ASMR 전용 노이즈 감소.

    ASMR 특성:
    - 속삭임(whisper): 저진폭, 고주파 성분 많음 → 과도한 제거 금지
    - 배경 환경음(빗소리, 자연음 등): 비정상적(non-stationary) 노이즈
    - 클릭음, 키보드음 등: 임펄스 노이즈

    Parameters
    ----------
    strength : 0.0(감소 없음) ~ 1.0(최대 감소), 기본 0.55
               너무 높으면 속삭임 음성이 손상됨
    """
    try:
        import noisereduce as nr
    except ImportError:
        # noisereduce 없으면 원본 반환
        return audio

    # prop_decrease: 잡음 주파수 성분을 얼마나 줄일지
    # ASMR은 0.4~0.65 범위가 적절 (너무 강하면 속삭임 파괴)
    prop_decrease = max(0.0, min(1.0, strength))

    denoised = nr.reduce_noise(
        y=audio,
        sr=sr,
        stationary=False,          # ASMR 배경음은 비정상 노이즈
        prop_decrease=prop_decrease,
        n_fft=2048,
        win_length=2048,
        hop_length=512,
        time_mask_smooth_ms=50,
        freq_mask_smooth_hz=500,
    )

    return denoised.astype(np.float32)


def normalize_audio(audio: np.ndarray, target_peak: float = 0.95) -> np.ndarray:
    """
    오디오 정규화 (피크 정규화).
    ASMR 특성상 볼륨이 낮은 경우가 많아 정규화 후 인식률이 올라감.
    """
    max_val = np.max(np.abs(audio))
    if max_val > 1e-6:
        audio = audio / max_val * target_peak
    return audio

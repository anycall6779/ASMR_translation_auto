# -*- coding: utf-8 -*-
"""
ASMR 음성 인식 핵심 모듈
- faster-whisper (우선) / openai-whisper (폴백) 지원
- ASMR 속삭임 음성에 최적화된 파라미터
"""

import os
import tempfile
import numpy as np
from pathlib import Path


# ─────────────────────────────────────────────
# SRT 타임코드 변환
# ─────────────────────────────────────────────
def seconds_to_srt_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int(round((seconds % 1) * 1000))
    if ms >= 1000:
        ms = 999
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


# ─────────────────────────────────────────────
# ASMR 전용 initial_prompt
# ─────────────────────────────────────────────
ASMR_PROMPTS = {
    "ja": "ASMRの囁き声。ゆっくりとした丁寧な話し方。雑音が混じることがあります。",
    "ko": "ASMR 속삭임 음성. 천천히 부드럽게 말하는 방식. 배경 잡음이 있을 수 있습니다.",
    "en": "ASMR whispering voice. Slow and gentle speech. Background noise may be present.",
    "zh": "ASMR耳语声音。缓慢温柔的说话方式。可能有背景噪音。",
}


# ─────────────────────────────────────────────
# Whisper 백엔드 감지
# ─────────────────────────────────────────────
def detect_whisper_backend() -> str:
    try:
        import faster_whisper  # noqa: F401
        return "faster_whisper"
    except ImportError:
        pass
    try:
        import whisper  # noqa: F401
        return "openai_whisper"
    except ImportError:
        pass
    return "none"


# ─────────────────────────────────────────────
# 핵심 변환 함수
# ─────────────────────────────────────────────
def transcribe_audio(
    audio_path: str,
    model_size: str = "large-v3-turbo",
    language: str = "ja",
    use_denoise: bool = True,
    denoise_strength: float = 0.55,
    vad_threshold: float = 0.30,
    no_speech_threshold: float = 0.35,
    beam_size: int = 1,
    cpu_threads: int = 0,
    log_fn=None,
    progress_fn=None,
) -> str:
    """
    ASMR 오디오 파일을 SRT 자막으로 변환.

    Parameters
    ----------
    audio_path        : 입력 오디오 파일 경로
    model_size        : Whisper 모델 크기
    language          : 언어 코드 (ja / ko / en / zh)
    use_denoise       : 노이즈 감소 전처리 여부
    denoise_strength  : 노이즈 감소 강도 (0.0~1.0, 기본 0.55)
    vad_threshold     : VAD 무음 감지 임계값 (낮을수록 작은 소리 인식)
    no_speech_threshold: Whisper no-speech 판단 임계값
    log_fn            : 로그 출력 콜백 (str) -> None
    progress_fn       : 진행률 콜백 (int 0~100) -> None

    Returns
    -------
    생성된 SRT 파일 경로
    """
    from audio_processor import load_audio, apply_denoise, normalize_audio
    import soundfile as sf

    def log(msg: str):
        if log_fn:
            log_fn(msg)

    def prog(pct: int):
        if progress_fn:
            progress_fn(pct)

    audio_path = Path(audio_path)
    output_srt = audio_path.with_suffix(".srt")

    # 1) 오디오 로드
    log(f"[{audio_path.name}] 오디오 로드 중...")
    prog(5)
    audio, sr = load_audio(str(audio_path))

    # 2) 노이즈 감소 전처리
    if use_denoise:
        log(f"[{audio_path.name}] 노이즈 감소 전처리 중... (강도={denoise_strength:.2f})")
        prog(15)
        audio = apply_denoise(audio, sr, strength=denoise_strength)

    audio = normalize_audio(audio)

    # 3) 전처리된 오디오를 임시 파일로 저장
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".wav")
    os.close(tmp_fd)
    try:
        sf.write(tmp_path, audio, sr)

        backend = detect_whisper_backend()
        if backend == "none":
            raise ImportError(
                "faster-whisper 또는 openai-whisper가 설치되지 않았습니다.\n"
                "setup.bat을 실행하여 의존성을 설치해주세요."
            )

        # 4) 음성 인식
        log(f"[{audio_path.name}] Whisper 모델 로드 중 ({model_size}, {backend})...")
        prog(25)

        srt_lines = []

        if backend == "faster_whisper":
            srt_lines = _transcribe_faster_whisper(
                tmp_path, model_size, language,
                vad_threshold, no_speech_threshold,
                beam_size, cpu_threads,
                log, prog,
            )
        else:
            srt_lines = _transcribe_openai_whisper(
                tmp_path, model_size, language,
                no_speech_threshold,
                log, prog,
            )

    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

    # 5) SRT 파일 저장
    prog(95)
    log(f"[{audio_path.name}] SRT 파일 저장 중...")
    with open(str(output_srt), "w", encoding="utf-8-sig") as f:
        f.write("\n".join(srt_lines))

    prog(100)
    log(f"[{audio_path.name}] 완료 → {output_srt.name}")
    return str(output_srt)


# ─────────────────────────────────────────────
# faster-whisper 백엔드
# ─────────────────────────────────────────────
def _transcribe_faster_whisper(
    audio_path, model_size, language,
    vad_threshold, no_speech_threshold,
    beam_size, cpu_threads,
    log, prog,
):
    import os
    from faster_whisper import WhisperModel

    # device 자동 선택 (CUDA → CPU)
    try:
        import torch
        if torch.cuda.is_available():
            device = "cuda"
            # VRAM 여유 확인 후 compute_type 결정
            vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024 ** 3)
            compute_type = "float16" if vram_gb >= 4 else "int8_float16"
            gpu_name = torch.cuda.get_device_name(0)
            log(f"  GPU 감지: {gpu_name} (VRAM {vram_gb:.1f}GB) → {compute_type}")
        else:
            device = "cpu"
            compute_type = "int8"
    except ImportError:
        device = "cpu"
        compute_type = "int8"

    # cpu_threads=0 이면 시스템 코어 수 자동 사용 (GPU 사용 시에도 전처리용으로 필요)
    _threads = cpu_threads if cpu_threads > 0 else (os.cpu_count() or 4)
    _workers = min(2, _threads // 4) or 1  # 동시 오디오 처리 워커

    model = WhisperModel(
        model_size,
        device=device,
        compute_type=compute_type,
        cpu_threads=_threads,
        num_workers=_workers,
    )
    if device == "cpu":
        log(f"  디바이스: CPU / compute_type: {compute_type} / threads: {_threads}")
    prog(40)

    # beam_size=1 이면 greedy 디코딩 (2~3배 빠름)
    _best_of = beam_size if beam_size > 1 else 1

    segments, info = model.transcribe(
        audio_path,
        language=language,
        beam_size=beam_size,
        best_of=_best_of,
        temperature=0.0,
        condition_on_previous_text=True,
        initial_prompt=ASMR_PROMPTS.get(language, ""),
        # VAD 필터 – 속삭임용으로 낮은 임계값
        vad_filter=True,
        vad_parameters={
            "threshold": vad_threshold,           # 낮을수록 작은 소리도 음성으로 감지
            "min_speech_duration_ms": 100,
            "min_silence_duration_ms": 500,
            "speech_pad_ms": 300,
        },
        no_speech_threshold=no_speech_threshold,
        log_prob_threshold=-1.0,
        compression_ratio_threshold=2.4,
        word_timestamps=False,
    )

    log(f"  감지 언어: {info.language} (확률 {info.language_probability:.2f})")
    prog(60)

    srt_lines = []
    idx = 1
    for seg in segments:
        text = seg.text.strip()
        if not text:
            continue
        srt_lines.append(str(idx))
        srt_lines.append(
            f"{seconds_to_srt_time(seg.start)} --> {seconds_to_srt_time(seg.end)}"
        )
        srt_lines.append(text)
        srt_lines.append("")
        idx += 1

    prog(90)
    return srt_lines


# ─────────────────────────────────────────────
# openai-whisper 백엔드 (폴백)
# ─────────────────────────────────────────────
def _transcribe_openai_whisper(
    audio_path, model_size, language,
    no_speech_threshold,
    log, prog,
):
    import whisper

    model = whisper.load_model(model_size)
    prog(40)
    log("  openai-whisper 백엔드 사용 중 (속도가 느릴 수 있습니다)")

    result = model.transcribe(
        audio_path,
        language=language,
        fp16=False,
        initial_prompt=ASMR_PROMPTS.get(language, ""),
        no_speech_threshold=no_speech_threshold,
        condition_on_previous_text=True,
        temperature=0.0,
    )

    prog(85)
    srt_lines = []
    idx = 1
    for seg in result.get("segments", []):
        text = seg["text"].strip()
        if not text:
            continue
        srt_lines.append(str(idx))
        srt_lines.append(
            f"{seconds_to_srt_time(seg['start'])} --> {seconds_to_srt_time(seg['end'])}"
        )
        srt_lines.append(text)
        srt_lines.append("")
        idx += 1

    prog(90)
    return srt_lines

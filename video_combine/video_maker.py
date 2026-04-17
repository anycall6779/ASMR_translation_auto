# -*- coding: utf-8 -*-
"""
ASMR 영상 생성 모듈
────────────────────────────────────────────────
- 출력: 오디오 파일 폴더 내 video_make/ 서브폴더에 .mkv 저장
- 영상 코덱: libx264 -crf 0 (무손실)  /  GPU: h264_nvenc lossless
- 오디오 코덱: FLAC (무손실)
- 자막: SRT를 MKV 소프트 자막 트랙으로 임베드 → 타임스탬프 원본 그대로 보존
"""

import os
import re
import shutil
import subprocess
import tempfile
import textwrap
from pathlib import Path

# 스크립트 파일 위치(ASMR 루트) 기준으로 video_make 폴더 고정
VIDEO_OUT_DIR = Path(__file__).parent / "video_make"


# ─────────────────────────────────────────────
# SRT 자막 줄바꿈 처리
# ─────────────────────────────────────────────
def _is_cjk(ch: str) -> bool:
    """일본어·중국어·한자 등 CJK 문자 여부"""
    cp = ord(ch)
    return (
        0x3000 <= cp <= 0x9FFF    # CJK 통합 한자 + 일본어 가나
        or 0xF900 <= cp <= 0xFAFF  # CJK 호환 한자
        or 0x20000 <= cp <= 0x2A6DF  # CJK 확장 B
    )


def _wrap_line(text: str, max_chars: int = 40) -> str:
    """한 줄 자막을 max_chars 기준으로 줄바꿈"""
    if not text.strip():
        return text
    cjk_ratio = sum(1 for c in text if _is_cjk(c)) / max(len(text), 1)
    if cjk_ratio > 0.3:
        # 일본어 등 CJK: 문자 단위로 자름 (더 좁게)
        limit = min(max_chars, 22)
        lines, buf = [], []
        count = 0
        for ch in text:
            buf.append(ch)
            count += 1
            if count >= limit:
                lines.append("".join(buf))
                buf, count = [], 0
        if buf:
            lines.append("".join(buf))
        return "\n".join(lines)
    else:
        # 영어·한국어: 단어 단위 줄바꿈
        return textwrap.fill(text, width=max_chars)


def _wrap_srt(src: str, dst: str, max_chars: int = 40):
    """(내부 호환용 — _split_sentences_srt 호출)"""
    _split_sentences_srt(src, dst, max_chars)


# ─────────────────────────────────────────────
# SRT 자막 문장 분리 + 시간 배분 + 줄바꿈
# ─────────────────────────────────────────────
def _parse_tc(s: str) -> float:
    """SRT 타임코드 문자열 → 영어(float)"""
    m = re.match(r"(\d+):(\d+):(\d+)[,.](\d+)", s.strip())
    if not m:
        return 0.0
    h, mn, sec, ms = int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))
    # ms 자릿수 자동 보정 (3자리 기준)
    ms_str = m.group(4)
    ms = int(ms_str) * (10 ** (3 - len(ms_str))) if len(ms_str) < 3 else int(ms_str)
    return h * 3600 + mn * 60 + sec + ms / 1000


def _fmt_tc(t: float) -> str:
    """float 영어 → SRT 타임코드 문자열"""
    t = max(0.0, t)
    h   = int(t // 3600)
    mn  = int((t % 3600) // 60)
    sec = int(t % 60)
    ms  = min(999, int(round((t - int(t)) * 1000)))
    return f"{h:02d}:{mn:02d}:{sec:02d},{ms:03d}"


def _split_sentences_srt(src: str, dst: str, max_chars: int = 40):
    """
    SRT 자막을 문장 단위(。！？・연속 구분자)로 분리하고
    시간을 글자 수 비례로 배분한 뒤 줄바꿈도 적용.

    • 각 SRT 블록에 여러 문장이 담겨 있으면 별도 블록으로 분리
    • 시간은 원본 start–end 범위 안에서 글자 수 비례로 배분
    • 문장이 하나인 블록은 줄바꿈만 적용
    """
    with open(src, encoding="utf-8-sig", errors="replace") as f:
        content = f.read()

    blocks = re.split(r"\n\s*\n", content.strip())
    out_blocks = []
    counter = 1

    for block in blocks:
        lines = block.strip().splitlines()
        if len(lines) < 3:
            out_blocks.append(block)
            continue

        # 타임코드 파싱
        tc_parts = lines[1].split("-->")
        if len(tc_parts) != 2:
            out_blocks.append(block)
            continue
        t_start = _parse_tc(tc_parts[0])
        t_end   = _parse_tc(tc_parts[1])
        duration = t_end - t_start
        if duration <= 0:
            out_blocks.append(block)
            continue

        # 텍스트 합치
        full_text = " ".join(lines[2:]).strip()

        # 문장 분리: 。！？ 뒤에서 자름
        # 단, 구분자가 한 단어 안에 없도록 조심스럽게
        sents = re.split(r"(?<=[。！？!?])", full_text)
        sents = [s.strip() for s in sents if s.strip()]

        if len(sents) <= 1:
            # 분리 불가 → 줄바꿈만
            wrapped = _wrap_line(full_text, max_chars)
            out_blocks.append(f"{counter}\n{_fmt_tc(t_start)} --> {_fmt_tc(t_end)}\n{wrapped}")
            counter += 1
            continue

        # 글자 수 기준 시간 비례 배분
        total_chars = sum(len(s) for s in sents) or 1
        cur = t_start
        for i, sent in enumerate(sents):
            if i == len(sents) - 1:
                seg_end = t_end
            else:
                seg_end = cur + duration * len(sent) / total_chars
                # 최소 0.3초 보장
                seg_end = max(seg_end, cur + 0.3)
                # 시간이 이미 끝을 넘지 않도록
                seg_end = min(seg_end, t_end - 0.1 * (len(sents) - i - 1))

            wrapped = _wrap_line(sent, max_chars)
            out_blocks.append(f"{counter}\n{_fmt_tc(cur)} --> {_fmt_tc(seg_end)}\n{wrapped}")
            counter += 1
            cur = seg_end

    with open(dst, "w", encoding="utf-8", errors="replace") as f:
        f.write("\n\n".join(out_blocks))


# ─────────────────────────────────────────────
# FFmpeg 경로 탐색
# ─────────────────────────────────────────────
def _get_ffmpeg() -> str:
    if shutil.which("ffmpeg"):
        return "ffmpeg"
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        pass
    raise FileNotFoundError(
        "FFmpeg를 찾을 수 없습니다.\n"
        "https://ffmpeg.org/download.html 에서 설치하거나\n"
        "pip install imageio-ffmpeg 를 실행하세요."
    )


# ─────────────────────────────────────────────
# GPU lossless nvenc 지원 여부
# ─────────────────────────────────────────────
def _probe_nvenc(ffmpeg: str) -> bool:
    try:
        r = subprocess.run(
            [ffmpeg, "-hide_banner", "-encoders"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            errors="replace",
            timeout=10,
        )
        output = (r.stdout or "") + (r.stderr or "")
        return "h264_nvenc" in output
    except Exception:
        return False


# ─────────────────────────────────────────────
# 오디오 길이(초) 조회
# ─────────────────────────────────────────────
def _get_duration(ffmpeg: str, path: str) -> float:
    r = subprocess.run(
        [ffmpeg, "-i", path, "-f", "null", "-"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )
    # FFmpeg는 진단 정보를 stderr에 출력; stdout도 같이 검사
    output = (r.stderr or "") + (r.stdout or "")
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+)\.(\d+)", output)
    if m:
        h, mn, s, cs = int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))
        return h * 3600 + mn * 60 + s + cs / 100
    return 0.0


# ─────────────────────────────────────────────
# FFmpeg 실행 + 진행률 파싱
# ─────────────────────────────────────────────
def _run_ffmpeg(cmd: list, total_sec: float, log, prog):
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    for line in proc.stdout:
        m = re.search(r"time=(\d+):(\d+):(\d+)\.(\d+)", line)
        if m and total_sec > 0:
            cur = (int(m.group(1)) * 3600 + int(m.group(2)) * 60
                   + int(m.group(3)) + int(m.group(4)) / 100)
            pct = min(int(cur / total_sec * 80) + 15, 95)
            prog(pct)
    proc.wait()
    if proc.returncode != 0:
        raise RuntimeError(f"FFmpeg 실패 (exit code {proc.returncode})")


# ─────────────────────────────────────────────
# 핵심: 영상 생성 함수
# ─────────────────────────────────────────────
def create_video(
    audio_path: str,
    srt_path: str,
    image_path: str,
    output_path: str = None,
    font_size: int = 22,
    font_color: str = "white",
    use_gpu: bool = True,
    log_fn=None,
    progress_fn=None,
) -> str:
    """
    정지 이미지 + 오디오 + SRT 자막 → 무손실 MKV 영상 생성.

    출력 위치: <오디오 파일 폴더>/video_make/<파일명>.mkv

    자막 처리:
      - SRT 파일을 MKV 소프트 자막 트랙으로 임베드
      - 타임스탬프 원본 그대로 → 싱크 오류 없음
      - VLC, MPC-HC, mpv 등에서 자막 켜기/끄기 가능

    코덱:
      - 영상: libx264 -crf 0 (무손실) / GPU: h264_nvenc lossless
      - 오디오: FLAC (무손실)
      - 컨테이너: MKV
    """
    def log(msg):
        if log_fn:
            log_fn(msg)

    def prog(pct):
        if progress_fn:
            progress_fn(pct)

    audio_path = Path(audio_path)
    srt_path   = Path(srt_path)
    image_path = Path(image_path)

    # 경로 존재 확인
    for p, label in [(audio_path, "오디오"), (srt_path, "SRT"), (image_path, "이미지")]:
        if not p.exists():
            raise FileNotFoundError(f"{label} 파일을 찾을 수 없습니다: {p}")

    # 출력 폴더: ASMR 루트의 video_make 폴더 (고정)
    if output_path is None:
        VIDEO_OUT_DIR.mkdir(parents=True, exist_ok=True)
        output_path = VIDEO_OUT_DIR / (audio_path.stem + ".mkv")
    else:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

    ffmpeg = _get_ffmpeg()
    prog(5)

    # 코덱 선택
    if use_gpu and _probe_nvenc(ffmpeg):
        vcodec = "h264_nvenc"
        # h264_nvenc lossless: -preset lossless 사용, yuv444p 필수
        # (-rc lossless 는 유효하지 않은 옵션, yuv420p 는 lossless 미지원)
        encode_opts = ["-preset", "lossless"]
        pix_fmt = "yuv444p"
        log("  영상 코덱: h264_nvenc (GPU lossless, yuv444p)")
    else:
        vcodec = "libx264"
        encode_opts = ["-crf", "0", "-preset", "ultrafast"]
        pix_fmt = "yuv420p"
        log("  영상 코덱: libx264 -crf 0 (CPU 무손실)")

    log("  오디오 코덱: FLAC (무손실)")
    log("  자막: 하드 번인 (영상에 직접 삽입)")
    prog(10)

    # 오디오 길이 파악
    duration = _get_duration(ffmpeg, str(audio_path))
    log(f"  오디오 길이: {int(duration // 60)}분 {int(duration % 60)}초 ({duration:.1f}s)")
    prog(15)

    # SRT를 임시 ASCII 경로로 복사 + 줄바꿈 처리 (FFmpeg 한/일 경로 오류 방지)
    tmp_dir = tempfile.mkdtemp()
    tmp_srt = os.path.join(tmp_dir, "subtitle.srt")
    try:
        _wrap_srt(str(srt_path), tmp_srt)  # 줄바꿈 적용 후 저장

        # subtitles 필터용 경로: 슬래시 + 콜론 이스케이프
        _srt_fwd = tmp_srt.replace("\\", "/")
        # 드라이브 콜론만 \: 로 이스케이프 (C:/ → C\:/)
        _srt_fwd = re.sub(r"^([A-Za-z]):/", r"\1\\:/", _srt_fwd)

        # 자막 색상 변환
        color_map = {"white": "&H00FFFFFF", "yellow": "&H0000FFFF", "cyan": "&H00FFFF00"}
        primary = color_map.get(font_color, "&H00FFFFFF")

        # 자막 스타일 (ASMR용: 굵음 + 외곽선 + 좌우 여백)
        style = (
            f"FontSize={font_size},FontName=Arial,Bold=1,"
            f"PrimaryColour={primary},OutlineColour=&H00000000,"
            f"BackColour=&H80000000,Outline=2,Shadow=1,"
            f"Alignment=2,MarginV=30,MarginL=40,MarginR=40,"
            f"WrapStyle=0"
        )
        sub_filter = f"subtitles='{_srt_fwd}':force_style='{style}'"
        vf = f"scale=trunc(iw/2)*2:trunc(ih/2)*2,{sub_filter}"

        log(f"[{audio_path.name}] MKV 합성 중 (자막 번인)...")

        cmd = [
            ffmpeg, "-y",
            # 입력 0: 정지 이미지 루프
            "-loop", "1",
            "-framerate", "1",
            "-i", str(image_path),
            # 입력 1: 오디오
            "-i", str(audio_path),
            # 스트림 매핑 (자막은 번인이므로 별도 트랙 불필요)
            "-map", "0:v",
            "-map", "1:a",
            # 영상: 무손실 + 자막 번인
            "-vf", vf,
            "-c:v", vcodec,
            *encode_opts,
            "-pix_fmt", pix_fmt,
            # 오디오: FLAC 무손실
            "-c:a", "flac",
            # 재생 시간 = 오디오 길이
            "-t", str(duration),
            str(output_path),
        ]

        _run_ffmpeg(cmd, duration, log, prog)

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    size_mb = output_path.stat().st_size / (1024 * 1024)
    prog(100)
    log(f"[{audio_path.name}] 완료 → {output_path.relative_to(audio_path.parent.parent) if output_path.is_relative_to(audio_path.parent.parent) else output_path.name}  ({size_mb:.1f} MB)")
    return str(output_path)


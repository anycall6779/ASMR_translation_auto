# -*- coding: utf-8 -*-
"""
ASMR 자동 자막 생성기
────────────────────────────────────────────────
엔트리포인트: python main.py [파일경로 ...]
의존성: setup.bat 실행 후 사용
"""

import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from pathlib import Path

# ── 전역 상수 ─────────────────────────────────
SUPPORTED_EXTS = {".wav", ".mp3", ".flac", ".m4a", ".ogg", ".aac", ".opus"}

MODEL_SIZES = ["tiny", "base", "small", "medium", "large-v2", "large-v3", "large-v3-turbo", "distil-large-v3"]
MODEL_RECOMMEND = "large-v3-turbo"   # ASMR 속도/품질 균형 최적

LANGUAGES = {
    "日本語 (ja)": "ja",
    "한국어 (ko)": "ko",
    "English (en)": "en",
    "中文 (zh)": "zh",
    "自動検出": None,
}

DARK = {
    "bg":        "#1e1e2e",
    "surface":   "#313244",
    "overlay":   "#45475a",
    "text":      "#cdd6f4",
    "subtext":   "#a6adc8",
    "accent":    "#89b4fa",
    "green":     "#a6e3a1",
    "red":       "#f38ba8",
    "yellow":    "#f9e2af",
}


# ══════════════════════════════════════════════
# 메인 애플리케이션
# ══════════════════════════════════════════════
class ASMRSubtitleApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ASMR 자동 자막 생성기")
        self.geometry("800x640")
        self.minsize(700, 560)
        self.configure(bg=DARK["bg"])

        self._file_list: list[str] = []
        self._running = False

        self._build_styles()
        self._build_ui()
        self._apply_dark_scrollbar()

        # CLI 인자로 파일을 전달받은 경우 자동 추가
        for arg in sys.argv[1:]:
            p = Path(arg)
            if p.is_file() and p.suffix.lower() in SUPPORTED_EXTS:
                self._add_files([str(p)])

    # ── 스타일 ──────────────────────────────
    def _build_styles(self):
        s = ttk.Style(self)
        s.theme_use("clam")

        s.configure(".",
                     background=DARK["bg"],
                     foreground=DARK["text"],
                     fieldbackground=DARK["surface"],
                     troughcolor=DARK["overlay"],
                     selectbackground=DARK["accent"],
                     selectforeground=DARK["bg"],
                     font=("Segoe UI", 10))

        s.configure("TFrame",   background=DARK["bg"])
        s.configure("TLabel",   background=DARK["bg"],     foreground=DARK["text"])
        s.configure("Sub.TLabel", background=DARK["bg"],   foreground=DARK["subtext"], font=("Segoe UI", 9))
        s.configure("Head.TLabel", background=DARK["bg"],  foreground=DARK["accent"],  font=("Segoe UI", 11, "bold"))
        s.configure("TLabelframe",
                     background=DARK["bg"],
                     foreground=DARK["subtext"],
                     relief="flat")
        s.configure("TLabelframe.Label",
                     background=DARK["bg"],
                     foreground=DARK["subtext"],
                     font=("Segoe UI", 9))
        s.configure("TButton",
                     background=DARK["surface"],
                     foreground=DARK["text"],
                     relief="flat",
                     padding=(8, 4))
        s.map("TButton",
              background=[("active", DARK["overlay"]), ("pressed", DARK["accent"])],
              foreground=[("pressed", DARK["bg"])])
        s.configure("Accent.TButton",
                     background=DARK["accent"],
                     foreground=DARK["bg"],
                     font=("Segoe UI", 10, "bold"),
                     padding=(12, 6))
        s.map("Accent.TButton",
              background=[("active", "#74c7ec"), ("disabled", DARK["overlay"])],
              foreground=[("disabled", DARK["subtext"])])
        s.configure("TCombobox",
                     fieldbackground=DARK["surface"],
                     background=DARK["surface"],
                     foreground=DARK["text"],
                     arrowcolor=DARK["accent"],
                     selectbackground=DARK["surface"])
        s.map("TCombobox",
              fieldbackground=[("readonly", DARK["surface"])],
              foreground=[("readonly", DARK["text"])])
        s.configure("TCheckbutton",
                     background=DARK["bg"],
                     foreground=DARK["text"],
                     indicatorcolor=DARK["surface"],
                     selectcolor=DARK["accent"])
        s.configure("TScale",
                     background=DARK["bg"],
                     troughcolor=DARK["surface"],
                     sliderlength=16)
        s.configure("TProgressbar",
                     troughcolor=DARK["surface"],
                     background=DARK["accent"],
                     lightcolor=DARK["accent"],
                     darkcolor=DARK["accent"])
        s.configure("Treeview",
                     background=DARK["surface"],
                     foreground=DARK["text"],
                     fieldbackground=DARK["surface"],
                     rowheight=24)
        s.configure("Treeview.Heading",
                     background=DARK["overlay"],
                     foreground=DARK["subtext"],
                     relief="flat")
        s.map("Treeview",
              background=[("selected", DARK["accent"])],
              foreground=[("selected", DARK["bg"])])

    # ── UI 구성 ──────────────────────────────
    def _build_ui(self):
        pad = {"padx": 12, "pady": 6}

        # 상단 헤더
        hdr = ttk.Frame(self)
        hdr.pack(fill="x", padx=14, pady=(12, 4))
        ttk.Label(hdr, text="🎙  ASMR 자동 자막 생성기", style="Head.TLabel").pack(side="left")

        # ── 파일 목록 섹션 ──
        file_frm = ttk.LabelFrame(self, text=" 변환할 오디오 파일 ", padding=8)
        file_frm.pack(fill="both", expand=True, padx=14, pady=4)

        btn_bar = ttk.Frame(file_frm)
        btn_bar.pack(fill="x", pady=(0, 4))
        ttk.Button(btn_bar, text="파일 추가",   command=self._on_add_files).pack(side="left", padx=(0, 4))
        ttk.Button(btn_bar, text="폴더 추가",   command=self._on_add_folder).pack(side="left", padx=(0, 4))
        ttk.Button(btn_bar, text="선택 제거",   command=self._on_remove_selected).pack(side="left", padx=(0, 4))
        ttk.Button(btn_bar, text="전체 지우기", command=self._on_clear).pack(side="left")

        # 트리뷰+스크롤바 전용 내부 프레임 (grid 사용)
        tree_frm = ttk.Frame(file_frm)
        tree_frm.pack(fill="both", expand=True)

        cols = ("파일명", "경로", "상태")
        self._tree = ttk.Treeview(tree_frm, columns=cols, show="headings", height=8)
        self._tree.heading("파일명", text="파일명")
        self._tree.heading("경로",   text="경로")
        self._tree.heading("상태",   text="상태")
        self._tree.column("파일명", width=200, stretch=False)
        self._tree.column("경로",   width=380, stretch=True)
        self._tree.column("상태",   width=80,  stretch=False, anchor="center")
        vsb = ttk.Scrollbar(tree_frm, orient="vertical",   command=self._tree.yview)
        hsb = ttk.Scrollbar(tree_frm, orient="horizontal", command=self._tree.xview)
        self._tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self._tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        tree_frm.rowconfigure(0, weight=1)
        tree_frm.columnconfigure(0, weight=1)

        # ── 설정 섹션 ──
        cfg_outer = ttk.Frame(self)
        cfg_outer.pack(fill="x", padx=14, pady=4)

        # 왼쪽: 모델 / 언어
        cfg_left = ttk.LabelFrame(cfg_outer, text=" Whisper 설정 ", padding=8)
        cfg_left.pack(side="left", fill="both", expand=True, padx=(0, 6))

        ttk.Label(cfg_left, text="모델 크기").grid(row=0, column=0, sticky="w", pady=2)
        self._var_model = tk.StringVar(value=MODEL_RECOMMEND)
        cb_model = ttk.Combobox(cfg_left, textvariable=self._var_model,
                                values=MODEL_SIZES, state="readonly", width=16)
        cb_model.grid(row=0, column=1, sticky="w", padx=(8, 0))
        ttk.Label(cfg_left, text="  ← turbo 권장 (속도↑)", style="Sub.TLabel").grid(
            row=0, column=2, sticky="w", padx=4)

        ttk.Label(cfg_left, text="언어").grid(row=1, column=0, sticky="w", pady=2)
        self._var_lang_label = tk.StringVar(value="日本語 (ja)")
        cb_lang = ttk.Combobox(cfg_left, textvariable=self._var_lang_label,
                               values=list(LANGUAGES.keys()), state="readonly", width=16)
        cb_lang.grid(row=1, column=1, sticky="w", padx=(8, 0))

        ttk.Label(cfg_left, text="Beam Size").grid(row=2, column=0, sticky="w", pady=2)
        self._var_beam = tk.IntVar(value=1)
        beam_frm = ttk.Frame(cfg_left)
        beam_frm.grid(row=2, column=1, columnspan=2, sticky="w", padx=(8, 0))
        self._scale_beam = ttk.Scale(beam_frm, from_=1, to=5,
                                     variable=self._var_beam, orient="horizontal", length=100,
                                     command=lambda v: self._lbl_beam_val.configure(
                                         text=str(int(float(v)))))
        self._scale_beam.pack(side="left")
        self._lbl_beam_val = ttk.Label(beam_frm, text="1", width=2, style="Sub.TLabel")
        self._lbl_beam_val.pack(side="left", padx=(4, 0))
        ttk.Label(beam_frm, text="  1=최고속  5=최고정확", style="Sub.TLabel").pack(side="left", padx=4)

        # 오른쪽: 노이즈 / 임계값
        cfg_right = ttk.LabelFrame(cfg_outer, text=" ASMR 전처리 설정 ", padding=8)
        cfg_right.pack(side="left", fill="both", expand=True)

        self._var_denoise = tk.BooleanVar(value=True)
        ttk.Checkbutton(cfg_right, text="노이즈 감소 전처리",
                        variable=self._var_denoise,
                        command=self._toggle_denoise).grid(row=0, column=0, columnspan=3,
                                                           sticky="w", pady=2)

        ttk.Label(cfg_right, text="감소 강도").grid(row=1, column=0, sticky="w")
        self._var_dn_str = tk.DoubleVar(value=0.55)
        self._scale_dn = ttk.Scale(cfg_right, from_=0.1, to=0.9,
                                   variable=self._var_dn_str, orient="horizontal", length=120,
                                   command=lambda v: self._lbl_dn_val.configure(
                                       text=f"{float(v):.2f}"))
        self._scale_dn.grid(row=1, column=1, padx=(6, 4))
        self._lbl_dn_val = ttk.Label(cfg_right, text="0.55", width=4, style="Sub.TLabel")
        self._lbl_dn_val.grid(row=1, column=2, sticky="w")
        ttk.Label(cfg_right, text="  ↑ 너무 높으면 속삭임 손상", style="Sub.TLabel").grid(
            row=1, column=3, sticky="w", padx=4)

        ttk.Label(cfg_right, text="VAD 임계값").grid(row=2, column=0, sticky="w")
        self._var_vad = tk.DoubleVar(value=0.30)
        self._scale_vad = ttk.Scale(cfg_right, from_=0.1, to=0.9,
                                    variable=self._var_vad, orient="horizontal", length=120,
                                    command=lambda v: self._lbl_vad_val.configure(
                                        text=f"{float(v):.2f}"))
        self._scale_vad.grid(row=2, column=1, padx=(6, 4))
        self._lbl_vad_val = ttk.Label(cfg_right, text="0.30", width=4, style="Sub.TLabel")
        self._lbl_vad_val.grid(row=2, column=2, sticky="w")
        ttk.Label(cfg_right, text="  ↑ 낮을수록 속삭임 인식", style="Sub.TLabel").grid(
            row=2, column=3, sticky="w", padx=4)

        # ── 진행 표시 ──
        prog_frm = ttk.Frame(self)
        prog_frm.pack(fill="x", padx=14, pady=(4, 0))
        self._var_status = tk.StringVar(value="대기 중")
        ttk.Label(prog_frm, textvariable=self._var_status, style="Sub.TLabel").pack(
            side="left", padx=(0, 8))
        self._progress = ttk.Progressbar(prog_frm, mode="determinate", maximum=100, length=1)
        self._progress.pack(side="left", fill="x", expand=True)
        self._lbl_count = ttk.Label(prog_frm, text="0 / 0", style="Sub.TLabel", width=8)
        self._lbl_count.pack(side="right")

        # ── 로그 ──
        log_frm = ttk.LabelFrame(self, text=" 로그 ", padding=4)
        log_frm.pack(fill="x", padx=14, pady=4)
        self._log = scrolledtext.ScrolledText(
            log_frm, height=6, wrap="word",
            bg=DARK["surface"], fg=DARK["text"],
            insertbackground=DARK["text"],
            font=("Consolas", 9), relief="flat",
            state="disabled")
        self._log.pack(fill="x")

        # ── 하단 버튼 ──
        btn_frm = ttk.Frame(self)
        btn_frm.pack(fill="x", padx=14, pady=(4, 12))
        self._btn_start = ttk.Button(btn_frm, text="▶  자막 생성 시작",
                                     style="Accent.TButton",
                                     command=self._on_start)
        self._btn_start.pack(side="right", padx=(6, 0))
        self._btn_stop = ttk.Button(btn_frm, text="■  중지",
                                    command=self._on_stop, state="disabled")
        self._btn_stop.pack(side="right")

    def _apply_dark_scrollbar(self):
        """로그 ScrolledText의 스크롤바 색상 통일"""
        self._log.vbar.configure(
            bg=DARK["overlay"], troughcolor=DARK["surface"],
            activebackground=DARK["accent"], relief="flat", width=8)

    # ── 파일 관리 ────────────────────────────
    def _on_add_files(self):
        files = filedialog.askopenfilenames(
            title="오디오 파일 선택",
            filetypes=[
                ("오디오 파일", "*.wav *.mp3 *.flac *.m4a *.ogg *.aac *.opus"),
                ("모든 파일", "*.*"),
            ])
        if files:
            self._add_files(list(files))

    def _on_add_folder(self):
        folder = filedialog.askdirectory(title="오디오 파일이 있는 폴더 선택")
        if not folder:
            return
        files = [
            str(p) for p in Path(folder).rglob("*")
            if p.suffix.lower() in SUPPORTED_EXTS
        ]
        if not files:
            messagebox.showinfo("알림", "선택한 폴더에 지원 오디오 파일이 없습니다.")
            return
        self._add_files(files)

    def _add_files(self, paths: list[str]):
        existing = set(self._file_list)
        added = 0
        for p in paths:
            if p not in existing:
                self._file_list.append(p)
                existing.add(p)
                name = Path(p).name
                self._tree.insert("", "end", iid=p,
                                  values=(name, p, "대기"))
                added += 1
        self._update_count()
        if added:
            self._log_write(f"파일 {added}개 추가됨")

    def _on_remove_selected(self):
        for iid in self._tree.selection():
            self._tree.delete(iid)
            if iid in self._file_list:
                self._file_list.remove(iid)
        self._update_count()

    def _on_clear(self):
        self._tree.delete(*self._tree.get_children())
        self._file_list.clear()
        self._update_count()

    def _update_count(self):
        n = len(self._file_list)
        self._lbl_count.configure(text=f"0 / {n}")

    # ── 노이즈 토글 ──────────────────────────
    def _toggle_denoise(self):
        state = "normal" if self._var_denoise.get() else "disabled"
        self._scale_dn.configure(state=state)
        self._scale_vad.configure(state=state)

    # ── 시작 / 중지 ──────────────────────────
    def _on_start(self):
        if not self._file_list:
            messagebox.showwarning("경고", "변환할 파일을 먼저 추가해주세요.")
            return
        if self._running:
            return

        self._running = True
        self._btn_start.configure(state="disabled")
        self._btn_stop.configure(state="normal")
        self._progress["value"] = 0

        lang_label = self._var_lang_label.get()
        lang_code  = LANGUAGES.get(lang_label)   # None이면 자동 감지

        params = {
            "model_size":          self._var_model.get(),
            "language":            lang_code,
            "use_denoise":         self._var_denoise.get(),
            "denoise_strength":    round(self._var_dn_str.get(), 2),
            "vad_threshold":       round(self._var_vad.get(), 2),
            "no_speech_threshold": 0.35,
            "beam_size":           int(self._var_beam.get()),
            "cpu_threads":         12,
        }

        thread = threading.Thread(target=self._run_batch, args=(params,), daemon=True)
        thread.start()

    def _on_stop(self):
        self._running = False
        self._log_write("⚠ 사용자에 의해 중지 요청됨 (현재 파일 완료 후 중단)")

    def _run_batch(self, params: dict):
        files = list(self._file_list)
        total = len(files)
        done  = 0

        # 상태 초기화
        for f in files:
            self._tree_set_status(f, "대기")

        for idx, fpath in enumerate(files):
            if not self._running:
                break

            self._tree_set_status(fpath, "처리중")
            self._set_status(f"처리 중 ({idx + 1}/{total}): {Path(fpath).name}")

            try:
                from transcriber import transcribe_audio

                def per_file_progress(pct: int):
                    # 전체 진행률: 각 파일이 100/total만큼 기여
                    base = idx * 100 // total
                    contrib = pct * (100 // total) // 100
                    self._set_progress(base + contrib)

                transcribe_audio(
                    audio_path=fpath,
                    model_size=params["model_size"],
                    language=params["language"],
                    use_denoise=params["use_denoise"],
                    denoise_strength=params["denoise_strength"],
                    vad_threshold=params["vad_threshold"],
                    no_speech_threshold=params["no_speech_threshold"],
                    beam_size=params["beam_size"],
                    cpu_threads=params["cpu_threads"],
                    log_fn=self._log_write,
                    progress_fn=per_file_progress,
                )
                self._tree_set_status(fpath, "완료 ✓")
                done += 1

            except Exception as exc:
                self._log_write(f"[오류] {Path(fpath).name}: {exc}")
                self._tree_set_status(fpath, "오류 ✗")

            self._set_count(done, total)

        self._set_progress(100)
        self._set_status(f"완료 ({done}/{total}개 성공)")
        self._log_write(f"─── 배치 완료: {done}/{total} 파일 ───")
        self._running = False
        self.after(0, lambda: self._btn_start.configure(state="normal", text="▶  자막 생성 시작"))
        self.after(0, lambda: self._btn_stop.configure(state="disabled"))

    # ── 스레드→UI 헬퍼 ──────────────────────
    def _log_write(self, msg: str):
        def _do():
            self._log.configure(state="normal")
            self._log.insert("end", msg + "\n")
            self._log.see("end")
            self._log.configure(state="disabled")
        self.after(0, _do)

    def _set_status(self, msg: str):
        self.after(0, lambda: self._var_status.set(msg))

    def _set_progress(self, pct: int):
        self.after(0, lambda: self._progress.configure(value=pct))

    def _set_count(self, done: int, total: int):
        self.after(0, lambda: self._lbl_count.configure(text=f"{done} / {total}"))

    def _tree_set_status(self, iid: str, status: str):
        def _do():
            if self._tree.exists(iid):
                self._tree.set(iid, "상태", status)
        self.after(0, _do)


# ══════════════════════════════════════════════
# 엔트리포인트
# ══════════════════════════════════════════════
if __name__ == "__main__":
    # 이 파일이 있는 디렉터리를 sys.path에 추가
    _here = os.path.dirname(os.path.abspath(__file__))
    if _here not in sys.path:
        sys.path.insert(0, _here)

    app = ASMRSubtitleApp()
    app.mainloop()

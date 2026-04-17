# -*- coding: utf-8 -*-
"""
ASMR 영상 생성기 (독립 프로그램)
────────────────────────────────────────────────
자막 추출기(main.py)와 완전 분리된 영상 합성 전용 도구.

사용법:
  python video_app.py

기능:습니다. 자막이 
  - SRT 자막 + 오디오 파일 쌍을 여러 개 추가
  - 배경 이미지 하나 지정
  - 무손실 MKV 영상 생성 (FLAC 오디오 + 소프트 SRT 자막 트랙)
  - 출력: C:\\Users\\USER\\Desktop\\ASMR\\video_make\\ 폴더
"""

import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from pathlib import Path

SUPPORTED_AUDIO = {".wav", ".mp3", ".flac", ".m4a", ".ogg", ".aac", ".opus"}

# 번역 플러그인(plugin/translate)이 생성하는 파일 접미사 언어 코드 목록
TRANSLATE_LANGS = ["ko", "en", "ja", "zh", "zh-tw"]

DARK = {
    "bg":      "#1e1e2e",
    "surface": "#313244",
    "overlay": "#45475a",
    "text":    "#cdd6f4",
    "subtext": "#a6adc8",
    "accent":  "#89b4fa",
    "green":   "#a6e3a1",
    "red":     "#f38ba8",
}


# ══════════════════════════════════════════════
# 영상 생성 전용 앱
# ══════════════════════════════════════════════
class VideoMakerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ASMR 영상 생성기")
        self.geometry("820x620")
        self.minsize(700, 500)
        self.configure(bg=DARK["bg"])
        self.resizable(True, True)

        self._pairs: list[dict] = []   # {"audio": str, "srt": str}
        self._running = False

        self._build_styles()
        self._build_ui()
        self.after(100, self._apply_dark_scrollbar)

    # ── 스타일 ─────────────────────────────────
    def _build_styles(self):
        s = ttk.Style(self)
        s.theme_use("clam")
        s.configure(".", background=DARK["bg"], foreground=DARK["text"],
                    fieldbackground=DARK["surface"], troughcolor=DARK["overlay"],
                    bordercolor=DARK["overlay"], lightcolor=DARK["overlay"],
                    darkcolor=DARK["overlay"], font=("Segoe UI", 10))
        s.configure("TFrame",      background=DARK["bg"])
        s.configure("TLabelframe", background=DARK["bg"], bordercolor=DARK["overlay"])
        s.configure("TLabelframe.Label", background=DARK["bg"],
                    foreground=DARK["accent"], font=("Segoe UI", 10, "bold"))
        s.configure("Treeview", background=DARK["surface"], foreground=DARK["text"],
                    fieldbackground=DARK["surface"], rowheight=24)
        s.configure("Treeview.Heading", background=DARK["overlay"],
                    foreground=DARK["text"], font=("Segoe UI", 9, "bold"))
        s.map("Treeview", background=[("selected", DARK["accent"])],
              foreground=[("selected", DARK["bg"])])
        s.configure("Sub.TLabel", background=DARK["bg"], foreground=DARK["subtext"],
                    font=("Segoe UI", 9))
        s.configure("Accent.TButton", background=DARK["accent"], foreground=DARK["bg"],
                    font=("Segoe UI", 10, "bold"))
        s.map("Accent.TButton", background=[("active", DARK["overlay"])])
        s.configure("TButton", background=DARK["overlay"], foreground=DARK["text"])
        s.configure("TProgressbar", troughcolor=DARK["surface"],
                    background=DARK["accent"], bordercolor=DARK["bg"])

    # ── UI 구성 ────────────────────────────────
    def _build_ui(self):
        # ── 파일 목록 ──
        file_frm = ttk.LabelFrame(self, text=" 변환할 파일 목록 (오디오 + SRT 쌍) ", padding=8)
        file_frm.pack(fill="both", expand=True, padx=14, pady=(10, 4))

        btn_bar = ttk.Frame(file_frm)
        btn_bar.pack(fill="x", pady=(0, 6))
        ttk.Button(btn_bar, text="＋ 오디오 추가",  command=self._on_add_audio).pack(side="left", padx=(0, 4))
        ttk.Button(btn_bar, text="＋ 폴더 추가",    command=self._on_add_folder).pack(side="left", padx=(0, 4))
        ttk.Button(btn_bar, text="SRT 자동 연결",   command=self._on_auto_link_srt).pack(side="left", padx=(0, 4))
        ttk.Button(btn_bar, text="선택 제거",        command=self._on_remove).pack(side="left", padx=(0, 4))
        ttk.Button(btn_bar, text="전체 지우기",      command=self._on_clear).pack(side="left")

        tree_frm = ttk.Frame(file_frm)
        tree_frm.pack(fill="both", expand=True)
        cols = ("audio", "srt", "status")
        self._tree = ttk.Treeview(tree_frm, columns=cols, show="headings", selectmode="extended")
        self._tree.heading("audio",  text="오디오 파일")
        self._tree.heading("srt",    text="SRT 자막 파일")
        self._tree.heading("status", text="상태")
        self._tree.column("audio",  width=280, anchor="w")
        self._tree.column("srt",    width=280, anchor="w")
        self._tree.column("status", width=90,  anchor="center")
        vsb = ttk.Scrollbar(tree_frm, orient="vertical",   command=self._tree.yview)
        hsb = ttk.Scrollbar(tree_frm, orient="horizontal",  command=self._tree.xview)
        self._tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self._tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        tree_frm.rowconfigure(0, weight=1)
        tree_frm.columnconfigure(0, weight=1)

        # ── 이미지 + 설정 ──
        cfg_frm = ttk.LabelFrame(self, text=" 설정 ", padding=8)
        cfg_frm.pack(fill="x", padx=14, pady=4)

        ttk.Label(cfg_frm, text="배경 이미지").grid(row=0, column=0, sticky="w")
        self._var_image = tk.StringVar()
        ttk.Entry(cfg_frm, textvariable=self._var_image, width=50).grid(
            row=0, column=1, sticky="ew", padx=(8, 4))
        ttk.Button(cfg_frm, text="찾아보기", command=self._on_pick_image, width=8).grid(
            row=0, column=2, padx=(0, 8))
        cfg_frm.columnconfigure(1, weight=1)

        ttk.Label(cfg_frm, text="출력 폴더", style="Sub.TLabel").grid(
            row=1, column=0, sticky="w", pady=(4, 0))
        out_dir = Path(__file__).parent / "video_make"
        ttk.Label(cfg_frm, text=str(out_dir), style="Sub.TLabel").grid(
            row=1, column=1, sticky="w", padx=(8, 0), pady=(4, 0))

        # 자막 크기
        ttk.Label(cfg_frm, text="자막 크기").grid(row=2, column=0, sticky="w", pady=(6, 0))
        self._var_font_size = tk.IntVar(value=22)
        _scale_font = ttk.Scale(cfg_frm, from_=14, to=48,
                                variable=self._var_font_size, orient="horizontal", length=120,
                                command=lambda v: self._lbl_font_val.configure(text=str(int(float(v)))))
        _scale_font.grid(row=2, column=1, sticky="w", padx=(8, 4), pady=(6, 0))
        self._lbl_font_val = ttk.Label(cfg_frm, text="22", width=3, style="Sub.TLabel")
        self._lbl_font_val.grid(row=2, column=2, sticky="w", pady=(6, 0))

        # 자막 색상
        ttk.Label(cfg_frm, text="자막 색상").grid(row=3, column=0, sticky="w", pady=(4, 0))
        self._var_font_color = tk.StringVar(value="white")
        color_frm = ttk.Frame(cfg_frm)
        color_frm.grid(row=3, column=1, sticky="w", padx=(8, 0), pady=(4, 0))
        for color, label in [("white", "흰색"), ("yellow", "노란색"), ("cyan", "하늘색")]:
            ttk.Radiobutton(color_frm, text=label,
                            variable=self._var_font_color, value=color).pack(side="left", padx=(0, 10))

        # 다국어 SRT 우선 언어
        ttk.Label(cfg_frm, text="자막 언어 우선").grid(row=4, column=0, sticky="w", pady=(4, 0))
        self._var_pref_lang = tk.StringVar(value="ko")
        lang_frm = ttk.Frame(cfg_frm)
        lang_frm.grid(row=4, column=1, sticky="w", padx=(8, 0), pady=(4, 0))
        for code, lbl in [("ko", "한국어"), ("en", "English"), ("ja", "日本語"), ("zh", "中文"), ("orig", "원본")]:
            ttk.Radiobutton(lang_frm, text=lbl,
                            variable=self._var_pref_lang, value=code).pack(side="left", padx=(0, 8))
        ttk.Label(lang_frm, text="← 번역 플러그인 SRT 우선 탐색", style="Sub.TLabel").pack(side="left")

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
            log_frm, height=7, wrap="word",
            bg=DARK["surface"], fg=DARK["text"],
            insertbackground=DARK["text"],
            font=("Consolas", 9), relief="flat",
            state="disabled")
        self._log.pack(fill="x")

        # ── 버튼 ──
        btn_frm = ttk.Frame(self)
        btn_frm.pack(fill="x", padx=14, pady=(4, 12))
        self._btn_start = ttk.Button(btn_frm, text="▶  영상 생성 시작",
                                     style="Accent.TButton",
                                     command=self._on_start)
        self._btn_start.pack(side="right", padx=(6, 0))
        self._btn_stop = ttk.Button(btn_frm, text="■  중지",
                                    command=self._on_stop, state="disabled")
        self._btn_stop.pack(side="right")

    def _apply_dark_scrollbar(self):
        try:
            self._log.vbar.configure(
                bg=DARK["overlay"], troughcolor=DARK["surface"],
                activebackground=DARK["accent"], relief="flat", width=8)
        except Exception:
            pass

    # ── SRT 탐색 헬퍼 ───────────────────────────
    def _find_best_srt(self, audio_path: str) -> tuple:
        """
        오디오 경로를 받아 최적 SRT 경로를 반환.
        우선순위:
          1. 선호 언어 번역본  (예: _ko.srt)
          2. 다른 번역 언어본  (예: _en.srt, _ja.srt …)
          3. 원본 SRT          (오디오와 동일 stem.srt)
        반환: (srt_path str, display_name str)  — 없으면 ("", "")
        """
        p    = Path(audio_path)
        pref = self._var_pref_lang.get()

        # 1순위: 선호 언어 번역본
        if pref != "orig":
            candidate = p.parent / f"{p.stem}_{pref}.srt"
            if candidate.exists():
                return str(candidate), candidate.name

        # 2순위: 다른 번역 언어 (선호 언어 제외)
        for lang in TRANSLATE_LANGS:
            if lang == pref:
                continue
            candidate = p.parent / f"{p.stem}_{lang}.srt"
            if candidate.exists():
                return str(candidate), candidate.name

        # 3순위: 원본 SRT
        orig = p.with_suffix(".srt")
        if orig.exists():
            return str(orig), orig.name

        return "", ""

    # ── 파일 추가 ──────────────────────────────
    def _on_add_audio(self):
        files = filedialog.askopenfilenames(
            title="오디오 파일 선택",
            filetypes=[("오디오 파일", "*.wav *.mp3 *.flac *.m4a *.ogg *.aac *.opus"),
                       ("모든 파일", "*.*")])
        if not files:
            return
        added = 0
        existing_audio = {p["audio"] for p in self._pairs}
        for f in files:
            if f in existing_audio:
                continue
            srt, srt_name = self._find_best_srt(f)
            self._pairs.append({"audio": f, "srt": srt})
            self._tree.insert("", "end", iid=f,
                              values=(Path(f).name,
                                      srt_name if srt else "⚠ SRT 없음",
                                      "대기"))
            added += 1
        self._update_count()
        self._log_write(f"파일 {added}개 추가됨 (SRT 자동 연결 포함)")

    def _on_add_folder(self):
        folder = filedialog.askdirectory(title="오디오 파일이 있는 폴더 선택")
        if not folder:
            return
        files = [str(p) for p in Path(folder).rglob("*")
                 if p.suffix.lower() in SUPPORTED_AUDIO]
        if not files:
            messagebox.showinfo("알림", "선택한 폴더에 지원 오디오 파일이 없습니다.")
            return
        existing = {p["audio"] for p in self._pairs}
        added = 0
        for f in sorted(files):
            if f in existing:
                continue
            srt, srt_name = self._find_best_srt(f)
            self._pairs.append({"audio": f, "srt": srt})
            self._tree.insert("", "end", iid=f,
                              values=(Path(f).name,
                                      srt_name if srt else "⚠ SRT 없음",
                                      "대기"))
            added += 1
        self._update_count()
        self._log_write(f"폴더에서 {added}개 추가됨")

    def _on_auto_link_srt(self):
        """선택된 행(또는 전체)의 오디오와 같은 위치에서 .srt 파일 재탐색"""
        targets = list(self._tree.selection()) or list(self._tree.get_children())
        updated = 0
        for iid in targets:
            for pair in self._pairs:
                if pair["audio"] == iid:
                    srt, srt_name = self._find_best_srt(pair["audio"])
                    if srt:
                        pair["srt"] = srt
                        self._tree.set(iid, "srt", srt_name)
                        updated += 1
                    break
        self._log_write(f"SRT 자동 연결: {updated}개 갱신됨")

    def _on_remove(self):
        for iid in self._tree.selection():
            self._tree.delete(iid)
            self._pairs = [p for p in self._pairs if p["audio"] != iid]
        self._update_count()

    def _on_clear(self):
        self._tree.delete(*self._tree.get_children())
        self._pairs.clear()
        self._update_count()

    def _update_count(self):
        self._lbl_count.configure(text=f"0 / {len(self._pairs)}")

    def _on_pick_image(self):
        path = filedialog.askopenfilename(
            title="배경 이미지 선택",
            filetypes=[("이미지 파일", "*.jpg *.jpeg *.png *.webp *.bmp"),
                       ("모든 파일", "*.*")])
        if path:
            self._var_image.set(path)

    # ── 시작 / 중지 ────────────────────────────
    def _on_start(self):
        if self._running:
            return
        if not self._pairs:
            messagebox.showwarning("경고", "변환할 파일을 먼저 추가해주세요.")
            return
        image_path = self._var_image.get().strip()
        if not image_path:
            messagebox.showwarning("경고", "배경 이미지를 선택해주세요.")
            return
        missing_srt = [p for p in self._pairs if not p["srt"]]
        if missing_srt:
            names = "\n".join(Path(p["audio"]).name for p in missing_srt[:5])
            if not messagebox.askyesno("경고",
                    f"SRT 파일이 없는 항목이 있습니다:\n{names}\n\n계속하시겠습니까? (해당 항목은 건너뜁니다)"):
                return

        self._running = True
        self._btn_start.configure(state="disabled")
        self._btn_stop.configure(state="normal")
        self._progress["value"] = 0

        t = threading.Thread(target=self._run_batch, args=(image_path,), daemon=True)
        t.start()

    def _on_stop(self):
        self._running = False
        self._log_write("⚠ 중지 요청됨 (현재 파일 완료 후 중단)")

    def _run_batch(self, image_path: str):
        from video_maker import create_video

        pairs = list(self._pairs)
        total = len(pairs)
        done = 0

        for iid in [p["audio"] for p in pairs]:
            self._tree.set(iid, "status", "대기")

        for idx, pair in enumerate(pairs):
            if not self._running:
                break
            audio = pair["audio"]
            srt   = pair["srt"]

            if not srt or not Path(srt).exists():
                self._log_write(f"[건너뜀] {Path(audio).name}: SRT 파일 없음")
                self._set_tree_status(audio, "건너뜀")
                continue

            self._set_tree_status(audio, "생성중")
            self._set_status(f"영상 생성 중 ({idx + 1}/{total}): {Path(audio).name}")

            try:
                def prog(pct, _idx=idx):
                    base = _idx * 100 // total
                    contrib = pct * (100 // total) // 100
                    self._set_progress(base + contrib)

                create_video(
                    audio_path=audio,
                    srt_path=srt,
                    image_path=image_path,
                    font_size=int(self._var_font_size.get()),
                    font_color=self._var_font_color.get(),
                    log_fn=self._log_write,
                    progress_fn=prog,
                )
                self._set_tree_status(audio, "완료 ✓")
                done += 1
            except Exception as e:
                self._log_write(f"[오류] {Path(audio).name}: {e}")
                self._set_tree_status(audio, "오류 ✗")

            self.after(0, lambda d=done, t=total: self._lbl_count.configure(text=f"{d} / {t}"))

        self._set_progress(100)
        self._set_status(f"완료 ({done}/{total}개 성공)")
        self._log_write(f"─── 배치 완료: {done}/{total} 파일 ───")
        self._log_write(f"출력 폴더: {Path(__file__).parent / 'video_make'}")
        self._running = False
        self.after(0, lambda: self._btn_start.configure(state="normal"))
        self.after(0, lambda: self._btn_stop.configure(state="disabled"))

    # ── 스레드→UI 헬퍼 ─────────────────────────
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

    def _set_tree_status(self, iid: str, text: str):
        self.after(0, lambda: self._tree.set(iid, "status", text))


# ── 진입점 ─────────────────────────────────────
if __name__ == "__main__":
    app = VideoMakerApp()
    app.mainloop()

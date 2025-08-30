#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Licitagov — Criador de Licitações (GUI) — Página inteira rolável
- Toda a janela é scrollável (Canvas + Frame), inclusive o console de log.
- Botão “Criar licitação” no topo (toolbar) e também acima do console.
- Seção de anexos sempre visível; destino padrão: "0. EDITAL_ANEXOS".
- Log colorido (ok/info/warn/error), barra de progresso e badge de status.
"""

import os, sys, re, shutil, unicodedata
from pathlib import Path
from typing import List, Optional, Dict, Callable
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# ======================== Domínio ===========================
MESES = [
    "01. JANEIRO", "02. FEVEREIRO", "03. MARCO", "04. ABRIL",
    "05. MAIO", "06. JUNHO", "07. JULHO", "08. AGOSTO",
    "09. SETEMBRO", "10. OUTUBRO", "11. NOVEMBRO", "12. DEZEMBRO",
]

SUBPASTAS_DESTINO = [
    "0. EDITAL_ANEXOS",
    "1. HABILITACAO/1. HAB_JURIDICA",
    "1. HABILITACAO/2. HAB_FISCAL",
    "1. HABILITACAO/3. HAB_ECON_FINAN",
    "1. HABILITACAO/4. QUALIFICACAO_TECNICA",
    "1. HABILITACAO/5. ACT_CAT",
    "1. HABILITACAO/6. DECLARACOES",
    "2. PROPOSTA",
    "3. EDITAVEIS/1. DECLARACAO",
    "3. EDITAVEIS/2. PROPOSTA",
    "3. EDITAVEIS/3. PLANILHA",
]

SUBPASTAS_PADRAO_PRESELECIONADAS = {
    "1. HABILITACAO/1. HAB_JURIDICA",
    "1. HABILITACAO/3. HAB_ECON_FINAN",
    "1. HABILITACAO/4. QUALIFICACAO_TECNICA",
    "3. EDITAVEIS/1. DECLARACAO",
    "3. EDITAVEIS/2. PROPOSTA",
    "3. EDITAVEIS/3. PLANILHA",
}

SUBPASTA_DEFAULT_ANEXOS = "0. EDITAL_ANEXOS"

# ====================== Utilidades ==========================
def _strip_accents(s: str) -> str:
    return "".join(ch for ch in unicodedata.normalize("NFD", s) if unicodedata.category(ch) != "Mn")

def _normalize_token(name: str) -> str:
    s = _strip_accents(name).lower().strip()
    s = re.sub(r"^\d+\s*[\.\-]?\s*", "", s)
    s = s.replace(" ", "").replace(".", "").replace("_", "").replace("-", "")
    return s

def caminho_participar() -> Path:
    return Path(__file__).parent.resolve()

def caminho_licitacao_raiz() -> Path:
    return caminho_participar().parent

def detectar_pasta_modelos() -> Optional[Path]:
    lic = caminho_licitacao_raiz()
    if not lic.exists():
        return None
    cand = [c for c in lic.iterdir() if c.is_dir() and "modelo" in _normalize_token(c.name)]
    cand.sort(key=lambda p: p.name)
    return cand[0] if cand else None

def detectar_pasta_template(modelos_dir: Path) -> Optional[Path]:
    if not modelos_dir or not modelos_dir.exists():
        return None
    cand = []
    for c in modelos_dir.iterdir():
        if c.is_dir():
            n = _normalize_token(c.name)
            if "idlct" in n or ("id" in n and "lct" in n):
                cand.append(c)
    if not cand:
        for c in modelos_dir.iterdir():
            if c.is_dir():
                cand.append(c); break
    cand.sort(key=lambda p: p.name)
    return cand[0] if cand else None

def resolver_pasta_mes(base_participar: Path, mes_escolhido: str) -> Path:
    try:
        mes_texto = mes_escolhido.split(".")[1].strip()
    except Exception:
        mes_texto = mes_escolhido
    token = _normalize_token(mes_texto)
    for c in base_participar.iterdir():
        if c.is_dir() and token in _normalize_token(c.name):
            return c
    pasta = base_participar / mes_escolhido
    pasta.mkdir(parents=True, exist_ok=True)
    return pasta

def montar_nome_licitacao(dia: str, id_lct: str, portal: str, gp: bool, cidade_uf: str) -> str:
    return f"{dia.strip()}_{id_lct.strip()}_{portal.strip()}{('_GP' if gp else '')}_{cidade_uf.strip()}"

def criar_estrutura_licitacao(destino_raiz: Path) -> None:
    for rel in SUBPASTAS_DESTINO:
        (destino_raiz / rel).mkdir(parents=True, exist_ok=True)

def _listar_subdirs(p: Path) -> List[Path]:
    return sorted([c for c in p.iterdir() if c.is_dir()], key=lambda x: x.name)

def _resolver_subpasta_flex(model_root: Path, rel_path: str) -> Optional[Path]:
    current = model_root
    for part in Path(rel_path).parts:
        alvo = _normalize_token(part)
        escolhido = None
        for c in _listar_subdirs(current):
            if _normalize_token(c.name) == alvo:
                escolhido = c; break
        if not escolhido:
            for c in _listar_subdirs(current):
                n = _normalize_token(c.name)
                if alvo in n or n in alvo:
                    escolhido = c; break
        if not escolhido:
            return None
        current = escolhido
    return current

def _proximo_nome_livre(pasta: Path, nome: str) -> Path:
    stem, suf = Path(nome).stem, Path(nome).suffix
    i = 1; cand = pasta / nome
    while cand.exists():
        cand = pasta / f"{stem}_{i}{suf}"; i += 1
    return cand

def copiar_padrao_resiliente(raiz_modelo_template: Path, raiz_destino: Path,
                             subpastas_selecionadas: List[str], politica: str,
                             log: Callable[[str, str], None]) -> None:
    for rel in subpastas_selecionadas:
        src_dir = raiz_modelo_template / rel
        if not src_dir.exists():
            alt = _resolver_subpasta_flex(raiz_modelo_template, rel)
            if alt is not None and alt.exists():
                src_dir = alt
            else:
                log("warn", f"Pasta modelo não encontrada: {raiz_modelo_template / rel}")
                continue
        dst_dir = raiz_destino / rel
        dst_dir.mkdir(parents=True, exist_ok=True)
        for item in src_dir.iterdir():
            if not item.is_file(): continue
            destino = dst_dir / item.name
            try:
                if destino.exists():
                    if politica == "pular":
                        log("info", f"[pular] {destino.name} já existe.")
                    elif politica == "substituir":
                        shutil.copy2(item, destino); log("ok", f"[substituir] {destino.name}")
                    else:
                        destino = _proximo_nome_livre(dst_dir, item.name)
                        shutil.copy2(item, destino); log("ok", f"[duplicar] {destino.name}")
                else:
                    shutil.copy2(item, destino); log("ok", f"[copiar] {destino.name}")
            except Exception as e:
                log("error", f"Falha ao copiar '{item.name}': {e}")

def anexar_arquivos(arquivos: List[Path], raiz_destino: Path, subpasta_destino_rel: str,
                    politica: str, log: Callable[[str, str], None]) -> None:
    dst_dir = raiz_destino / subpasta_destino_rel
    dst_dir.mkdir(parents=True, exist_ok=True)
    for src in arquivos:
        if not src.exists() or not src.is_file():
            log("warn", f"Ignorado (não é arquivo): {src}"); continue
        destino = dst_dir / src.name
        try:
            if destino.exists():
                if politica == "pular":
                    log("info", f"[pular] {destino.name} já existe.")
                elif politica == "substituir":
                    shutil.copy2(src, destino); log("ok", f"[substituir] {destino.name}")
                else:
                    destino = _proximo_nome_livre(dst_dir, src.name)
                    shutil.copy2(src, destino); log("ok", f"[duplicar] {destino.name}")
            else:
                shutil.copy2(src, destino); log("ok", f"[copiar] {destino.name}")
        except Exception as e:
            log("error", f"Falha ao anexar '{src.name}': {e}")

# =============== Frame rolável para a PÁGINA INTEIRA ===============
class PageScroll(ttk.Frame):
    """Frame que torna TODO o conteúdo rolável (Canvas + Frame interno)."""
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.canvas = tk.Canvas(self, highlightthickness=0, bg="#F5F7FA")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.content = ttk.Frame(self.canvas)  # tudo do app vai aqui
        self._window_id = self.canvas.create_window((0,0), window=self.content, anchor="nw")

        self.content.bind("<Configure>", self._on_content_config)
        self.canvas.bind("<Configure>", self._on_canvas_config)

        # rolagem do mouse global
        self._bind_mousewheel(self.canvas)
        self._bind_mousewheel(self.content)

    def _on_content_config(self, _):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_config(self, event):
        # manter largura do frame igual à largura visível do canvas
        self.canvas.itemconfigure(self._window_id, width=event.width)

    def _bind_mousewheel(self, widget):
        widget.bind("<Enter>", lambda e: widget.bind_all("<MouseWheel>", self._on_mousewheel))
        widget.bind("<Leave>", lambda e: widget.unbind_all("<MouseWheel>"))
        widget.bind("<Enter>", lambda e: widget.bind_all("<Button-4>", self._on_mousewheel_linux))
        widget.bind("<Enter>", lambda e: widget.bind_all("<Button-5>", self._on_mousewheel_linux))
        widget.bind("<Leave>", lambda e: widget.unbind_all("<Button-4>"))
        widget.bind("<Leave>", lambda e: widget.unbind_all("<Button-5>"))

    def _on_mousewheel(self, event):
        delta = event.delta
        if sys.platform == "darwin":
            self.canvas.yview_scroll(int(-1 * delta), "units")
        else:
            self.canvas.yview_scroll(int(-1 * (delta/120)), "units")

    def _on_mousewheel_linux(self, event):
        self.canvas.yview_scroll(-1 if event.num == 4 else +1, "units")

# =============================== APP ===============================
class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Licitagov — Criar Licitação no Mês")
        self.geometry("1100x780"); self.minsize(980, 720)
        try:
            self.call("tk", "scaling", 1.15)
        except tk.TclError:
            pass

        # Paleta / estilos
        self.PRIMARY = "#1363DF"; self.ACCENT = "#16A34A"
        self.WARN = "#EAB308"; self.ERROR = "#DC2626"
        self.BG = "#F5F7FA"; self.CARD = "#FFFFFF"
        self.TEXT = "#0F172A"; self.MUTED = "#6B7280"

        style = ttk.Style(self)
        try: style.theme_use("vista")
        except Exception: style.theme_use("clam")
        style.configure(".", font=("Segoe UI", 10))
        style.configure("TFrame", background=self.BG)
        style.configure("Card.TFrame", background=self.CARD)
        style.configure("Header.TFrame", background=self.CARD)
        style.configure("TLabel", background=self.BG, foreground=self.TEXT)
        style.configure("Header.TLabel", background=self.CARD, foreground=self.TEXT, font=("Segoe UI Semibold", 16))
        style.configure("Subheader.TLabel", background=self.CARD, foreground=self.MUTED, font=("Segoe UI", 10))
        style.configure("Section.TLabelframe", background=self.BG)
        style.configure("Section.TLabelframe.Label", background=self.BG, foreground=self.TEXT, font=("Segoe UI Semibold", 11))
        style.configure("Section.TLabelframe", relief="flat")
        style.configure("Primary.TButton", foreground=self.TEXT, padding=8)  # texto preto
        style.configure("TProgressbar", troughcolor="#E5E7EB", background=self.PRIMARY)

        # Estado
        self.error_count = 0; self.warn_count = 0; self.last_status = "ok"

        # Vars
        self.var_mes = tk.StringVar(value=MESES[0])
        self.var_dia = tk.StringVar(value="01")
        self.var_idlct = tk.StringVar(value="CE001")
        self.var_portal = tk.StringVar(value="BLL")
        self.var_gp = tk.BooleanVar(value=False)
        self.var_cidadeuf = tk.StringVar(value="Salvador-BA")

        modelos_auto = detectar_pasta_modelos()
        template_auto = detectar_pasta_template(modelos_auto) if modelos_auto else None
        self.var_modelos_path = tk.StringVar(value=str(modelos_auto) if modelos_auto else "")
        self.var_template_path = tk.StringVar(value=str(template_auto) if template_auto else "")
        self.var_politica = tk.StringVar(value="duplicar")

        self.anexos_arquivos: List[Path] = []
        self.var_anexos_destino = tk.StringVar(value=SUBPASTA_DEFAULT_ANEXOS)
        self.vars_subpastas: Dict[str, tk.BooleanVar] = {
            rel: tk.BooleanVar(value=(rel in SUBPASTAS_PADRAO_PRESELECIONADAS))
            for rel in SUBPASTAS_DESTINO
        }

        self.destino_criado: Optional[Path] = None

        # ======= Página inteira rolável =======
        page = PageScroll(self); page.pack(fill="both", expand=True)
        root = page.content  # tudo abaixo vai dentro de root (rolável)

        # Toolbar (topo) — inclui botão Criar
        toolbar = ttk.Frame(root, style="Header.TFrame", padding=12)
        toolbar.pack(fill="x", pady=(8, 10))
        ttk.Label(toolbar, text="Licitagov — Criar Licitação", style="Header.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(toolbar, text="Preencha, selecione o modelo e anexe arquivos. O console mostra tudo.",
                  style="Subheader.TLabel").grid(row=1, column=0, sticky="w")
        self.btn_criar_top = ttk.Button(toolbar, text="Criar licitação", style="Primary.TButton", command=self._criar)
        self.btn_criar_top.grid(row=0, column=1, rowspan=2, sticky="e")
        self.status_badge = ttk.Label(toolbar, text="🟢 OK", style="Subheader.TLabel")
        self.status_badge.grid(row=0, column=2, sticky="e", padx=(12,0))
        self.status_counts = ttk.Label(toolbar, text="Avisos: 0  |  Erros: 0", style="Subheader.TLabel")
        self.status_counts.grid(row=1, column=2, sticky="e")

        # Grid 2 colunas de blocos
        grid = ttk.Frame(root); grid.pack(fill="both", expand=True, padx=12)
        grid.columnconfigure(0, weight=1); grid.columnconfigure(1, weight=1)

        # Bloco 1 — Mês & Nome
        b1 = ttk.Labelframe(grid, text="1) Mês e nome da licitação", style="Section.TLabelframe", padding=12)
        b1.grid(row=0, column=0, sticky="ew", padx=(0, 8), pady=(0, 12))
        ttk.Label(b1, text="Mês").grid(row=0, column=0, sticky="w")
        ttk.Combobox(b1, values=MESES, textvariable=self.var_mes, state="readonly", width=18)\
            .grid(row=0, column=1, sticky="w", padx=(6, 0))
        ttk.Label(b1, text="Dia (00)").grid(row=0, column=2, sticky="w", padx=(12, 0))
        ttk.Entry(b1, textvariable=self.var_dia, width=6).grid(row=0, column=3, sticky="w")
        ttk.Label(b1, text="ID-LCT").grid(row=1, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(b1, textvariable=self.var_idlct, width=12).grid(row=1, column=1, sticky="w", pady=(8, 0))
        ttk.Label(b1, text="Portal").grid(row=1, column=2, sticky="w", pady=(8, 0))
        ttk.Entry(b1, textvariable=self.var_portal, width=12).grid(row=1, column=3, sticky="w", pady=(8, 0))
        ttk.Checkbutton(b1, text="GP", variable=self.var_gp).grid(row=1, column=4, sticky="w", padx=(12, 0), pady=(8, 0))
        ttk.Label(b1, text="Cidade-UF").grid(row=2, column=0, sticky="w", pady=(8, 2))
        ttk.Entry(b1, textvariable=self.var_cidadeuf, width=24).grid(row=2, column=1, columnspan=3, sticky="w", pady=(8, 2))
        ttk.Label(b1, text="Prévia do nome").grid(row=3, column=0, sticky="w", pady=(10, 0))
        self.lbl_preview = ttk.Label(b1, text="", foreground=self.PRIMARY)
        self.lbl_preview.grid(row=3, column=1, columnspan=4, sticky="w", pady=(10, 0))
        for v in (self.var_dia, self.var_idlct, self.var_portal, self.var_gp, self.var_cidadeuf):
            v.trace_add("write", self._update_preview)
        self._update_preview()

        # Bloco 2 — Modelo & Template
        b2 = ttk.Labelframe(grid, text="2) Pasta MODELOS e subpasta TEMPLATE (fonte)", style="Section.TLabelframe", padding=12)
        b2.grid(row=0, column=1, sticky="ew", padx=(8, 0), pady=(0, 12))
        ttk.Label(b2, text="MODELOS (raiz)").grid(row=0, column=0, sticky="w")
        ttk.Entry(b2, textvariable=self.var_modelos_path).grid(row=1, column=0, columnspan=2, sticky="ew", pady=(2, 6))
        ttk.Button(b2, text="Alterar…", command=self._escolher_modelos).grid(row=1, column=2, sticky="w", padx=(8, 0))
        b2.columnconfigure(0, weight=1)
        ttk.Label(b2, text="TEMPLATE (ex.: 00_ID-LCT_...)").grid(row=2, column=0, sticky="w", pady=(6, 0))
        ttk.Entry(b2, textvariable=self.var_template_path).grid(row=3, column=0, columnspan=2, sticky="ew", pady=(2, 6))
        ttk.Button(b2, text="Detectar de novo", command=self._detectar_template).grid(row=3, column=2, sticky="w", padx=(8, 0))
        ttk.Label(b2, text="Política de conflito").grid(row=4, column=0, sticky="w", pady=(8, 0))
        ttk.Combobox(b2, values=["pular", "substituir", "duplicar"], textvariable=self.var_politica, state="readonly", width=12)\
            .grid(row=4, column=1, sticky="w", pady=(8, 0))

        # Bloco 3 — Subpastas (com rolagem própria)
        b3 = ttk.Labelframe(grid, text="3) Subpastas de PADRÃO para copiar (** = pré-selecionadas)", style="Section.TLabelframe", padding=12)
        b3.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(0, 12))
        grid.rowconfigure(1, weight=1)
        # mini-scroll interno só para a grade de subpastas
        mini_canvas = tk.Canvas(b3, highlightthickness=0, height=230, bg=self.CARD)
        mini_canvas.pack(side="left", fill="both", expand=True)
        mini_sb = ttk.Scrollbar(b3, orient="vertical", command=mini_canvas.yview); mini_sb.pack(side="right", fill="y")
        mini_canvas.configure(yscrollcommand=mini_sb.set)
        inner = ttk.Frame(mini_canvas, style="Card.TFrame"); mini_id = mini_canvas.create_window((0,0), window=inner, anchor="nw")
        def _mini_conf(_): mini_canvas.configure(scrollregion=mini_canvas.bbox("all"))
        def _mini_resize(e): mini_canvas.itemconfigure(mini_id, width=e.width)
        inner.bind("<Configure>", _mini_conf); mini_canvas.bind("<Configure>", _mini_resize)
        mini_canvas.bind_all("<MouseWheel>", lambda ev: mini_canvas.yview_scroll(int(-1*(ev.delta/120)), "units"))
        # grid 2 colunas
        total = len(SUBPASTAS_DESTINO); half = (total + 1)//2
        for i, rel in enumerate(SUBPASTAS_DESTINO):
            col = 0 if i < half else 1
            row = i if col == 0 else i - half
            ttk.Checkbutton(inner, text=rel, variable=self.vars_subpastas[rel]).grid(row=row, column=col, sticky="w", pady=2, padx=4)
        inner.columnconfigure(0, weight=1); inner.columnconfigure(1, weight=1)

        # Bloco 4 — Anexos
        b4 = ttk.Labelframe(grid, text="4) Anexos do usuário", style="Section.TLabelframe", padding=12)
        b4.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0,12))
        ttk.Label(b4, text="Destino dos anexos").grid(row=0, column=0, sticky="w")
        ttk.Combobox(b4, values=SUBPASTAS_DESTINO, textvariable=self.var_anexos_destino, state="readonly", width=40)\
            .grid(row=0, column=1, sticky="w")
        ttk.Button(b4, text="Adicionar arquivos…", command=self._add_anexos).grid(row=0, column=2, padx=(8, 0))
        ttk.Button(b4, text="Limpar lista", command=self._limpar_anexos).grid(row=0, column=3, padx=(6, 0))
        self.lst_anexos = tk.Listbox(b4, height=5)
        self.lst_anexos.grid(row=1, column=0, columnspan=4, sticky="ew", pady=(6, 0))
        b4.columnconfigure(0, weight=1)

        # Linha de ações + progresso (duplico o botão aqui também)
        actions = ttk.Frame(root, padding=(12,0)); actions.pack(fill="x")
        self.btn_criar = ttk.Button(actions, text="Criar licitação", style="Primary.TButton", command=self._criar)
        self.btn_criar.pack(side="left")
        ttk.Button(actions, text="Abrir pasta", command=self._abrir_destino).pack(side="left", padx=(8,0))
        ttk.Button(actions, text="Limpar console", command=self._log_clear).pack(side="left", padx=(8,0))
        self.progress = ttk.Progressbar(actions, mode="determinate"); self.progress.pack(side="right", fill="x", expand=True, padx=(8,0))

        # Console (rodapé da página rolável)
        console_wrap = ttk.Frame(root, padding=12); console_wrap.pack(fill="both", expand=True)
        ttk.Label(console_wrap, text="Console (log de execução)").pack(anchor="w", pady=(0,6))
        self.txt_log = tk.Text(console_wrap, height=14, wrap="word", relief="flat", padx=12, pady=12, bg=self.CARD, fg=self.TEXT)
        self.txt_log.pack(fill="both", expand=True, side="left")
        sb = ttk.Scrollbar(console_wrap, orient="vertical", command=self.txt_log.yview)
        sb.pack(fill="y", side="right"); self.txt_log.configure(yscrollcommand=sb.set)
        self.txt_log.tag_config("ok", foreground=self.ACCENT)
        self.txt_log.tag_config("info", foreground=self.PRIMARY)
        self.txt_log.tag_config("warn", foreground=self.WARN)
        self.txt_log.tag_config("error", foreground=self.ERROR, underline=1)

        # Toast
        self.toast = ttk.Label(root, text="", style="Subheader.TLabel"); self.toast.pack(fill="x", padx=12, pady=(0,8))

    # ======= LOG / STATUS =======
    def _log(self, level: str, msg: str) -> None:
        self.txt_log.insert("end", f"[{level.upper()}] {msg}\n", (level,))
        self.txt_log.see("end")
        if level == "warn":
            self.warn_count += 1
            self.last_status = "warn" if self.last_status != "error" else "error"
        elif level == "error":
            self.error_count += 1; self.last_status = "error"
        badge = "🟢 OK" if self.last_status=="ok" else ("🟡 Avisos" if self.last_status=="warn" else "🔴 Erros")
        self.status_badge.config(text=badge)
        self.status_counts.config(text=f"Avisos: {self.warn_count}  |  Erros: {self.error_count}")

    def _log_clear(self) -> None:
        self.txt_log.delete("1.0", "end")
        self.warn_count = 0; self.error_count = 0; self.last_status = "ok"
        self.status_badge.config(text="🟢 OK"); self.status_counts.config(text="Avisos: 0  |  Erros: 0")
        self.toast.config(text="")

    def _toast(self, msg: str, level: str="info") -> None:
        color = {"ok": self.ACCENT, "info": self.PRIMARY, "warn": self.WARN, "error": self.ERROR}.get(level, self.MUTED)
        self.toast.config(text=msg, foreground=color)
        self.after(3500, lambda: self.toast.config(text="", foreground=self.MUTED))

    # ======= UI handlers =======
    def _update_preview(self, *_):
        self.lbl_preview.config(text=montar_nome_licitacao(
            self.var_dia.get(), self.var_idlct.get(), self.var_portal.get(), self.var_gp.get(), self.var_cidadeuf.get()
        ))

    def _escolher_modelos(self):
        p = filedialog.askdirectory(title="Selecione a pasta MODELOS (raiz)")
        if p:
            self.var_modelos_path.set(p); self._detectar_template()

    def _detectar_template(self):
        modelos = Path(self.var_modelos_path.get().strip())
        if not modelos.exists():
            modelos = detectar_pasta_modelos() or modelos
            self.var_modelos_path.set(str(modelos) if modelos else "")
        template = detectar_pasta_template(modelos) if modelos else None
        self.var_template_path.set(str(template) if template else "")
        self._toast("Template detectado." if template and template.exists() else "Não foi possível detectar o template.",
                    "ok" if template and template.exists() else "warn")

    def _add_anexos(self):
        files = filedialog.askopenfilenames(title="Selecione os arquivos para anexar")
        if files:
            for f in files:
                p = Path(f)
                if p not in self.anexos_arquivos:
                    self.anexos_arquivos.append(p); self.lst_anexos.insert("end", str(p))

    def _limpar_anexos(self):
        self.anexos_arquivos.clear(); self.lst_anexos.delete(0, "end")

    def _abrir_destino(self):
        if not self.destino_criado:
            messagebox.showinfo("Info", "Crie uma licitação primeiro."); return
        path = str(Path(self.destino_criado).resolve())
        try:
            if os.name == "nt": os.startfile(path)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                import subprocess; subprocess.run(["open", path])
            else:
                import subprocess; subprocess.run(["xdg-open", path])
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível abrir a pasta:\n{e}")

    # ======= Execução =======
    def _criar(self):
        self._log_clear(); self._toast("Iniciando criação…", "info")
        self.btn_criar.config(state="disabled"); self.btn_criar_top.config(state="disabled")
        self.progress.config(mode="indeterminate"); self.progress.start(12)
        try:
            base_participar = caminho_participar()
            pasta_mes = resolver_pasta_mes(base_participar, self.var_mes.get())
            if not pasta_mes.exists():
                try:
                    pasta_mes.mkdir(parents=True, exist_ok=True)
                    self._log("info", f"Pasta do mês criada: {pasta_mes}")
                except Exception as e:
                    self._log("error", f"Falha ao criar pasta do mês: {e}")
                    messagebox.showerror("Erro", f"Não foi possível criar a pasta do mês:\n{e}")
                    return

            nome = self.lbl_preview.cget("text")
            destino_raiz = pasta_mes / nome
            try:
                destino_raiz.mkdir(parents=True, exist_ok=True)
                self._log("ok", f"Licitação: {destino_raiz}")
            except Exception as e:
                self._log("error", f"Falha ao criar pasta da licitação: {e}")
                messagebox.showerror("Erro", f"Não foi possível criar a pasta da licitação:\n{e}")
                return

            try:
                criar_estrutura_licitacao(destino_raiz)
            except Exception as e:
                self._log("error", f"Falha ao criar subpastas: {e}")
                messagebox.showerror("Erro", f"Falha ao criar subpastas:\n{e}")
                return

            modelos = Path(self.var_modelos_path.get().strip())
            template = Path(self.var_template_path.get().strip())
            if not modelos.exists():
                modelos = detectar_pasta_modelos() or modelos
                self.var_modelos_path.set(str(modelos) if modelos else "")
            if modelos.exists() and (not template.exists()):
                template = detectar_pasta_template(modelos) or template
                self.var_template_path.set(str(template) if template else "")

            if not modelos.exists():
                self._log("warn", "Pasta MODELOS (raiz) não encontrada. Selecione manualmente.")
            elif not template.exists():
                self._log("warn", "Subpasta TEMPLATE não encontrada dentro da pasta MODELOS.")
            else:
                selecionadas = [rel for rel, var in self.vars_subpastas.items() if var.get()]
                if selecionadas:
                    self._log("info", f"Copiando padrões de: {template}")
                    try:
                        copiar_padrao_resiliente(template, destino_raiz, selecionadas, self.var_politica.get(), self._log)
                    except Exception as e:
                        self._log("error", f"Falha ao copiar padrões: {e}")
                        messagebox.showerror("Erro", f"Falha ao copiar padrões:\n{e}")
                        return

            # Anexos (por padrão, 0. EDITAL_ANEXOS)
            if self.anexos_arquivos:
                try:
                    anexar_arquivos(self.anexos_arquivos, destino_raiz, self.var_anexos_destino.get(),
                                    self.var_politica.get(), self._log)
                except Exception as e:
                    self._log("error", f"Falha ao anexar arquivos: {e}")
                    messagebox.showerror("Erro", f"Falha ao anexar arquivos:\n{e}")
                    return

            self.destino_criado = destino_raiz
            if self.error_count > 0:
                self._toast("Concluído com erros. Verifique o console.", "error")
            elif self.warn_count > 0:
                self._toast("Concluído com avisos. Verifique o console.", "warn")
            else:
                self._toast("Licitação criada com sucesso!", "ok")
        finally:
            self.progress.stop(); self.progress.config(mode="determinate", value=100)
            self.btn_criar.config(state="normal"); self.btn_criar_top.config(state="normal")

# ------------------- Entrada -------------------
if __name__ == "__main__":
    App().mainloop()
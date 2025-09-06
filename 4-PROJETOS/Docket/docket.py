#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Docket — Organizador de Licitações (Facelift Visual)
- Visual moderno com ícones (redimensionados), cards arredondados e console colorido.
- Mantém a LÓGICA de criação/cópia/anexos intacta.
"""

import os, sys, re, shutil, unicodedata
from pathlib import Path
from typing import List, Optional, Dict, Callable
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# ======================== Constantes (UI + domínio) ========================

MESES = [
    "01. JANEIRO", "02. FEVEREIRO", "03. MARCO", "04. ABRIL",
    "05. MAIO", "06. JUNHO", "07. JULHO", "08. AGOSTO",
    "09. SETEMBRO", "10. OUTUBRO", "11. NOVEMBRO", "12. DEZEMBRO",
]

# Subpastas que o usuário pode copiar do TEMPLATE (e quais ficam ligadas por padrão)
SUBPASTAS_PRESELECIONADAS: Dict[str, bool] = {
    "0. EDITAL_ANEXOS": False,

    "1. HABILITACAO/1. HAB_JURIDICA": True,
    "1. HABILITACAO/2. HAB_FISCAL": False,
    "1. HABILITACAO/3. HAB_ECON_FINAN": True,
    "1. HABILITACAO/4. QUALIFICACAO_TECNICA": True,
    "1. HABILITACAO/5. ACT_CAT": False,
    "1. HABILITACAO/6. DECLARACOES": False,

    "2. PROPOSTA": False,

    # OBS: a lógica tolera DECLARACAO vs DECLARACOES na origem
    "3. EDITAVEIS/1. DECLARACAO": True,
    "3. EDITAVEIS/2. PROPOSTA": True,
    "3. EDITAVEIS/3. PLANILHA": True,
}

# Combobox de destino de anexos do usuário
SUBPASTAS_DESTINO = list(SUBPASTAS_PRESELECIONADAS.keys())

# Subpasta padrão de anexos
SUBPASTA_DEFAULT_ANEXOS = "0. EDITAL_ANEXOS"

# ======================== Ícones (loader com resize) ========================

ICON_CACHE: Dict[tuple, tk.PhotoImage] = {}

def _resource_path(rel: str) -> Path:
    """Resolve caminho do asset tanto no .py quanto no .exe (PyInstaller)."""
    base = getattr(sys, "_MEIPASS", None)
    root = Path(base) if base else Path(__file__).parent
    return root / rel

def _load_icon(name: str, size: int = 24) -> tk.PhotoImage:
    """
    Carrega assets/icons/<name>.png e redimensiona para 'size' (px).
    - Com Pillow: LANCZOS (melhor qualidade).
    - Sem Pillow: fallback com subsample aproximado.
    - Cache para manter referência viva e evitar GC.
    """
    key = (name, size)
    if key in ICON_CACHE:
        return ICON_CACHE[key]
    p = _resource_path(f"assets/icons/{name}.png")

    # Melhor caminho: PIL
    try:
        from PIL import Image, ImageTk  # type: ignore
        im = Image.open(p).convert("RGBA")
        im = im.resize((size, size), Image.LANCZOS)
        img = ImageTk.PhotoImage(im)
        ICON_CACHE[key] = img
        return img
    except Exception:
        pass

    # Fallback nativo
    try:
        img = tk.PhotoImage(file=str(p))
        fx = max(1, img.width() // size)
        fy = max(1, img.height() // size)
        if fx > 1 or fy > 1:
            img = img.subsample(fx, fy)
    except Exception:
        img = tk.PhotoImage(width=1, height=1)
        img.put("{#ffffff00}")

    ICON_CACHE[key] = img
    return img

# ======================== Utilidades (domínio) ========================

def _strip_accents(s: str) -> str:
    return "".join(ch for ch in unicodedata.normalize("NFD", s) if unicodedata.category(ch) != "Mn")

def _normalize_token(name: str) -> str:
    s = _strip_accents(name).lower().strip()
    s = re.sub(r"^\d+\s*[\.\-]?\s*", "", s)
    s = s.replace(" ", "").replace(".", "").replace("_", "").replace("-", "")
    return s

def caminho_participar() -> Path:
    """Pasta onde o app está (base usada para procurar os meses)."""
    return Path(__file__).parent.resolve()

def caminho_licitacao_raiz() -> Path:
    """Um nível acima (onde costuma existir '5. Modelos_Padrao', etc.)."""
    return caminho_participar().parent

def detectar_pasta_modelos() -> Optional[Path]:
    """Tenta achar 'Modelos_Padrao' (ou similar) um nível acima."""
    lic = caminho_licitacao_raiz()
    if not lic.exists():
        return None
    cand = [c for c in lic.iterdir() if c.is_dir() and "modelo" in _normalize_token(c.name)]
    cand.sort(key=lambda p: p.name)
    return cand[0] if cand else None

def detectar_pasta_template(modelos_dir: Path) -> Optional[Path]:
    """Dentro de Modelos, tenta achar subpasta tipo '00_ID-LCT_...'."""
    if not modelos_dir or not modelos_dir.exists():
        return None
    cand: List[Path] = []
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
    """Localiza o mês existente ('2.FEVEREIRO' x '2. FEVEREIRO'); cria se não existir."""
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
    """Ex.: '18_CE004_BLL_GP_Salvador-BA'"""
    return f"{dia.strip()}_{id_lct.strip()}_{portal.strip()}{('_GP' if gp else '')}_{cidade_uf.strip()}"

def _listar_subdirs(p: Path) -> List[Path]:
    return sorted([c for c in p.iterdir() if c.is_dir()], key=lambda x: x.name)

def _resolver_subpasta_flex(model_root: Path, rel_path: str) -> Optional[Path]:
    """
    Resolve subpasta por aproximação (tolerante a 'DECLARACAO' x 'DECLARACOES' e prefixos).
    """
    current = model_root
    for part in Path(rel_path).parts:
        alvo = _normalize_token(part)
        escolhido = None
        # match exato
        for c in _listar_subdirs(current):
            if _normalize_token(c.name) == alvo:
                escolhido = c; break
        # aproximação
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
    """
    Copia arquivos das subpastas do TEMPLATE para o destino, respeitando política:
    - 'pular' (não sobrescreve),
    - 'substituir' (overwrite),
    - 'duplicar' (salva com sufixo _1, _2...).
    Tenta resolver nomes próximos (DECLARACAO/DECLARACOES).
    """
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
            if not item.is_file():
                continue
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
    """Anexa arquivos do usuário na subpasta selecionada, respeitando a política."""
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

# =============================== APP ===============================

class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()

        # ===== Janela base
        self.title("Docket — Organizador de Licitações")
        self.geometry("1120x780"); self.minsize(1000, 720)
        try: self.call("tk", "scaling", 1.15)
        except tk.TclError: pass

        # ===== Paleta / estilos
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
        style.configure("Section.TLabelframe", background=self.BG, relief="flat")
        style.configure("Section.TLabelframe.Label", background=self.BG, foreground=self.TEXT, font=("Segoe UI Semibold", 11))
        style.configure("Primary.TButton", foreground=self.TEXT, padding=8)
        style.map("Primary.TButton", background=[("active", "#FFD84D")])

        # ===== Estado / vars
        self.error_count = 0; self.warn_count = 0; self.last_status = "ok"
        self.destino_criado: Optional[Path] = None

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

        # checkboxes de subpastas
        self.vars_subpastas: Dict[str, tk.BooleanVar] = {}
        for rel, preset in SUBPASTAS_PRESELECIONADAS.items():
            self.vars_subpastas[rel] = tk.BooleanVar(value=preset)

        # ===== Ícones =====
        self.ic_app      = _load_icon("ic_app", 48)        # header
        self.ic_ok       = _load_icon("ic_ok", 24)
        self.ic_warn     = _load_icon("ic_warn", 24)
        self.ic_error    = _load_icon("ic_error", 24)
        self.ic_calendar = _load_icon("ic_calendar", 24)
        self.ic_folder   = _load_icon("ic_folder", 24)
        self.ic_template = _load_icon("ic_template", 24)
        self.ic_detect   = _load_icon("ic_detect", 24)
        self.ic_attach   = _load_icon("ic_attach", 24)
        self.ic_trash    = _load_icon("ic_trash", 24)
        self.ic_open     = _load_icon("ic_open", 24)
        self.ic_play     = _load_icon("ic_play", 24)

        # ===== Layout base
        self.configure(bg=self.BG)
        root = ttk.Frame(self, padding=12, style="TFrame"); root.pack(fill="both", expand=True)

        # ---------- HEADER ----------
        header = ttk.Frame(root, padding=12, style="Header.TFrame"); header.pack(fill="x")
        tk.Label(header, image=self.ic_app, bg=self.CARD).pack(side="left", padx=(0,8))
        ttk.Label(header, text="Docket — Organizador de Licitações", style="Header.TLabel").pack(side="left", pady=(2,0))
        ttk.Label(header, text="Crie pastas, copie padrões e anexe documentos em segundos.", style="Subheader.TLabel")\
            .pack(side="left", padx=(12,0), pady=(6,0))

        status = ttk.Frame(header, style="Header.TFrame"); status.pack(side="right")
        self.status_badge = ttk.Label(status, text="🟢 OK", style="Subheader.TLabel")
        self.status_badge.pack(side="top", anchor="e")
        self.status_counts = ttk.Label(status, text="Avisos: 0  |  Erros: 0", style="Subheader.TLabel")
        self.status_counts.pack(side="top", anchor="e")

        # ---------- CONTEÚDO ROLÁVEL ----------
        canvas = tk.Canvas(root, bg=self.BG, highlightthickness=0)
        scroll_y = ttk.Scrollbar(root, orient="vertical", command=canvas.yview)
        body = ttk.Frame(canvas, style="TFrame", padding=(0,8))
        body.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window(0, 0, window=body, anchor="nw")
        canvas.configure(yscrollcommand=scroll_y.set)
        canvas.pack(side="left", fill="both", expand=True); scroll_y.pack(side="right", fill="y")

        # colunas responsivas
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=1)

        # ---------- CARD 1: MÊS & NOME ----------
        card1, b1 = self._card(body, "1) Mês e nome da licitação")
        card1.grid(row=0, column=0, sticky="nsew", padx=(0,12), pady=(0,12))
        b1.columnconfigure(1, weight=1)

        ttk.Label(b1, text="Mês").grid(row=0, column=0, sticky="w")
        frm_mes = ttk.Frame(b1, style="TFrame"); frm_mes.grid(row=0, column=1, sticky="w")
        tk.Label(frm_mes, image=self.ic_calendar, bg=self.BG).pack(side="left", padx=(0,6))
        ttk.Combobox(frm_mes, values=MESES, textvariable=self.var_mes, state="readonly", width=24).pack(side="left")

        ttk.Label(b1, text="Dia (00)").grid(row=0, column=2, sticky="w", padx=(12,0))
        ttk.Entry(b1, textvariable=self.var_dia, width=6).grid(row=0, column=3, sticky="w")

        ttk.Label(b1, text="ID-LCT").grid(row=1, column=0, sticky="w", pady=(8,0))
        ttk.Entry(b1, textvariable=self.var_idlct, width=10).grid(row=1, column=1, sticky="w", pady=(8,0))
        ttk.Label(b1, text="Portal").grid(row=1, column=2, sticky="w", pady=(8,0))
        ttk.Entry(b1, textvariable=self.var_portal, width=10).grid(row=1, column=3, sticky="w", pady=(8,0))

        ttk.Checkbutton(b1, text="GP", variable=self.var_gp).grid(row=2, column=0, sticky="w", pady=(8,0))
        ttk.Label(b1, text="Cidade-UF").grid(row=2, column=1, sticky="w", pady=(8,0))
        ttk.Entry(b1, textvariable=self.var_cidadeuf, width=24).grid(row=2, column=1, sticky="e", padx=(0,140), pady=(8,0))

        ttk.Label(b1, text="Prévia do nome").grid(row=3, column=0, sticky="w", pady=(8,0))
        self.lbl_preview = ttk.Label(b1, text="", foreground=self.PRIMARY)
        self.lbl_preview.grid(row=3, column=1, columnspan=3, sticky="w", pady=(8,0))

        for v in (self.var_mes, self.var_dia, self.var_idlct, self.var_portal, self.var_gp, self.var_cidadeuf):
            v.trace_add("write", self._update_preview)
        self._update_preview()

        # ---------- CARD 2: MODELOS / TEMPLATE ----------
        card2, b2 = self._card(body, "2) Pasta MODELOS e subpasta TEMPLATE (fonte)")
        card2.grid(row=0, column=1, sticky="nsew", pady=(0,12))
        b2.columnconfigure(1, weight=1)

        ttk.Label(b2, text="MODELOS (raiz)").grid(row=0, column=0, sticky="w")
        frm_m = ttk.Frame(b2, style="TFrame"); frm_m.grid(row=0, column=1, sticky="ew"); frm_m.columnconfigure(0, weight=1)
        ttk.Entry(frm_m, textvariable=self.var_modelos_path).grid(row=0, column=0, sticky="ew")
        ttk.Button(frm_m, image=self.ic_folder, text=" Alterar…", compound="left", command=self._escolher_modelos).grid(row=0, column=1, padx=(8,0))

        ttk.Label(b2, text="TEMPLATE (ex.: 00_ID-LCT_...)").grid(row=1, column=0, sticky="w", pady=(8,0))
        frm_t = ttk.Frame(b2, style="TFrame"); frm_t.grid(row=1, column=1, sticky="ew"); frm_t.columnconfigure(0, weight=1)
        ttk.Entry(frm_t, textvariable=self.var_template_path).grid(row=0, column=0, sticky="ew")
        ttk.Button(frm_t, image=self.ic_detect, text=" Detectar de novo", compound="left", command=self._detectar_template).grid(row=0, column=1, padx=(8,0))

        ttk.Label(b2, text="Política de conflito").grid(row=2, column=0, sticky="w", pady=(8,0))
        ttk.Combobox(b2, values=["duplicar", "substituir", "pular"], textvariable=self.var_politica, state="readonly", width=18)\
            .grid(row=2, column=1, sticky="w", pady=(8,0))

        # ---------- CARD 3: SUBPASTAS PADRÃO ----------
        card3, b3 = self._card(body, "3) Subpastas de PADRÃO para copiar (** = pré-selecionadas)")
        card3.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(0,12))
        left = ttk.Frame(b3, style="TFrame"); left.grid(row=0, column=0, sticky="nsew", padx=(0,12))
        right = ttk.Frame(b3, style="TFrame"); right.grid(row=0, column=1, sticky="nsew")
        b3.columnconfigure(0, weight=1); b3.columnconfigure(1, weight=1)

        rels = list(self.vars_subpastas.keys())
        mid = len(rels)//2 or len(rels)
        cols = (rels[:mid], rels[mid:])
        for col_idx, rels_col in enumerate(cols):
            parent = left if col_idx == 0 else right
            for rel in rels_col:
                ttk.Checkbutton(parent, text=rel + (" **" if SUBPASTAS_PRESELECIONADAS.get(rel) else ""),
                                variable=self.vars_subpastas[rel]).pack(anchor="w", pady=2)

        # ---------- CARD 4: ANEXOS ----------
        card4, b4 = self._card(body, "4) Anexos do usuário")
        card4.grid(row=2, column=0, columnspan=2, sticky="nsew", pady=(0,12))
        ttk.Label(b4, text="Destino dos anexos").grid(row=0, column=0, sticky="w")
        ttk.Combobox(b4, values=SUBPASTAS_DESTINO, textvariable=self.var_anexos_destino, state="readonly", width=40)\
            .grid(row=0, column=1, sticky="w")
        ttk.Button(b4, image=self.ic_attach, text=" Adicionar arquivos…", compound="left", command=self._add_anexos).grid(row=0, column=2, padx=(8,0))
        ttk.Button(b4, image=self.ic_trash, text=" Limpar lista", compound="left", command=self._limpar_anexos).grid(row=0, column=3, padx=(6,0))
        self.lst_anexos = tk.Listbox(b4, height=5)
        self.lst_anexos.grid(row=1, column=0, columnspan=4, sticky="ew", pady=(6,0))
        b4.columnconfigure(0, weight=1)

        # ---------- AÇÕES ----------
        actions = ttk.Frame(root, padding=(12,0)); actions.pack(fill="x")
        self.btn_criar_top = ttk.Button(actions, image=self.ic_play, text=" CRIAR LICITAÇÃO", style="Primary.TButton",
                                        compound="left", command=self._criar)
        self.btn_criar_top.pack(side="right")
        ttk.Button(actions, image=self.ic_open, text=" Abrir pasta", compound="left", command=self._abrir_destino)\
            .pack(side="left")
        ttk.Button(actions, image=self.ic_trash, text=" Limpar console", compound="left", command=self._log_clear)\
            .pack(side="left", padx=(8,0))
        self.progress = ttk.Progressbar(actions, mode="determinate"); self.progress.pack(side="right", fill="x", expand=True, padx=(8,0))

        # ---------- CONSOLE ----------
        console_wrap = ttk.Frame(root, padding=12); console_wrap.pack(fill="both", expand=True)
        ttk.Label(console_wrap, text="Console (log de execução)").pack(anchor="w", pady=(0,6))
        self.txt_log = tk.Text(console_wrap, height=14, wrap="word", relief="flat", padx=12, pady=12,
                               bg=self.CARD, fg=self.TEXT, insertbackground=self.TEXT)
        self.txt_log.pack(fill="both", expand=True, side="left")
        sb = ttk.Scrollbar(console_wrap, orient="vertical", command=self.txt_log.yview)
        sb.pack(fill="y", side="right"); self.txt_log.configure(yscrollcommand=sb.set)
        self.txt_log.tag_config("ok", foreground=self.ACCENT)
        self.txt_log.tag_config("info", foreground=self.PRIMARY)
        self.txt_log.tag_config("warn", foreground=self.WARN)
        self.txt_log.tag_config("error", foreground=self.ERROR, underline=1)

        # ---------- TOAST ----------
        self.toast = ttk.Label(root, text="", style="Subheader.TLabel"); self.toast.pack(fill="x", padx=12, pady=(0,8))

    # ======= Card arredondado (Canvas + GRID) =======
    def _card(self, parent, title: str, radius: int = 10, padding: int = 12):
        """
        Cria um card com cantos arredondados.
        Retorna (container, content) — organize seus widgets em 'content' com GRID.
        """
        container = ttk.Frame(parent, style="TFrame")
        container.grid_propagate(False)

        cv = tk.Canvas(container, bg=self.BG, bd=0, highlightthickness=0)
        cv.pack(fill="both", expand=True)

        shell = ttk.Frame(cv, style="Card.TFrame", padding=padding)
        win = cv.create_window(0, 0, window=shell, anchor="nw")
        shell.columnconfigure(0, weight=1)

        lbl = ttk.Label(shell, text=title, style="Section.TLabelframe.Label")
        lbl.grid(row=0, column=0, sticky="w", pady=(0, 8))

        content = ttk.Frame(shell, style="Card.TFrame")
        content.grid(row=1, column=0, sticky="nsew")

        def _redraw(_evt=None):
            cv.delete("round")
            w = container.winfo_width() or 200
            h = container.winfo_height() or 100
            r = radius
            cv.coords(win, 0, 0)
            cv.config(width=w, height=h)
            cv.create_rectangle(r, 0, w - r, h, fill=self.CARD, outline="", tags="round")
            cv.create_rectangle(0, r, w, h - r, fill=self.CARD, outline="", tags="round")
            cv.create_oval(0, 0, 2*r, 2*r, fill=self.CARD, outline="", tags="round")
            cv.create_oval(w - 2*r, 0, w, 2*r, fill=self.CARD, outline="", tags="round")
            cv.create_oval(0, h - 2*r, 2*r, h, fill=self.CARD, outline="", tags="round")
            cv.create_oval(w - 2*r, h - 2*r, w, h, fill=self.CARD, outline="", tags="round")

        container.bind("<Configure>", _redraw)
        container.after(50, _redraw)
        return container, content

    # ======= Log / Status =======
    def _log(self, level: str, msg: str) -> None:
        self.txt_log.insert("end", f"[{level.upper()}] {msg}\n", (level,))
        self.txt_log.see("end")
        if level == "warn":
            self.warn_count += 1
            self.last_status = "warn" if self.last_status != "error" else "error"
        elif level == "error":
            self.error_count += 1; self.last_status = "error"
        else:
            self.last_status = "ok" if (self.warn_count==0 and self.error_count==0) else self.last_status
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

    # ======= Handlers =======
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
        self.btn_criar_top.config(state="disabled")
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
                messagebox.showerror("Erro", f"Falha ao criar pasta da licitação:\n{e}")
                return

            # criar subpastas marcadas
            try:
                for rel, var in self.vars_subpastas.items():
                    if var.get():
                        (destino_raiz / rel).mkdir(parents=True, exist_ok=True)
            except Exception as e:
                self._log("error", f"Falha ao criar subpastas: {e}")
                messagebox.showerror("Erro", f"Falha ao criar subpastas:\n{e}")
                return

            # copiar padrão do TEMPLATE
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

            # anexos do usuário
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
            self.btn_criar_top.config(state="normal")

# ------------------- Entrada -------------------
if __name__ == "__main__":
    App().mainloop()
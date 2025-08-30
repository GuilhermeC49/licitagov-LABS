#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Licitagov — Criador de Licitações por Mês (GUI) — Edição UI Premium
-------------------------------------------------------------------
• Coloque este app dentro de:  01. Licitacao/01. Participar/
• Escolha o MÊS, monte o NOME, cria a estrutura e copia padrões da pasta MODELO.

Destaques de UI:
- Tema ttk customizado (cores, espaçamentos, botões primários/secundários).
- Cabeçalho estilizado + seções organizadas.
- Log colorido com tags (info, ok, warn, error) e filtros (Tudo/Info/Avisos/Erros).
- Badge de Status (🟢/🟡/🔴) com contadores de Avisos/Erros.
- Barra de progresso durante operações, toasts sutis de feedback.
- Mantém toda a lógica resiliente (modelo/mês/cópias/anexos).

Compatível com Python 3.8+ (Tkinter nativo no Windows).
"""

from __future__ import annotations

import os
import re
import shutil
import unicodedata
from pathlib import Path
from typing import Dict, List, Optional, Callable
import tkinter as tk
from tkinter import ttk, filedialog, messagebox


# ============================================================
# Constantes de domínio
# ============================================================

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


# ============================================================
# Utilidades de normalização / matching
# ============================================================

def _strip_accents(s: str) -> str:
    return "".join(ch for ch in unicodedata.normalize("NFD", s) if unicodedata.category(ch) != "Mn")

def _normalize_token(name: str) -> str:
    """
    Normaliza um nome para comparação:
    - minúsculas, sem acentos
    - remove prefixo numérico/pontuação (ex.: "12. ")
    - remove espaços, '.', '_' e '-'
    """
    s = _strip_accents(name).lower().strip()
    s = re.sub(r"^\d+\s*[\.\-]?\s*", "", s)
    s = s.replace(" ", "").replace(".", "").replace("_", "").replace("-", "")
    return s

def _normalize_path_parts(rel_path: str) -> List[str]:
    return [_normalize_token(p) for p in Path(rel_path).parts]


# ============================================================
# Descoberta de caminhos (Participar, Modelos, Template)
# ============================================================

def caminho_participar() -> Path:
    """ Diretório do app: .../1. Licitacao/01. Participar/ """
    return Path(__file__).parent.resolve()

def caminho_licitacao_raiz() -> Path:
    """ .../1. Licitacao/ """
    return caminho_participar().parent

def detectar_pasta_modelos() -> Optional[Path]:
    """
    Procura dentro de .../1. Licitacao/ por pasta contendo 'modelo' (case/acentos agnóstico),
    seja '4.Modelos_Padrao' ou '5. Modelos_Padrao'.
    """
    lic = caminho_licitacao_raiz()
    if not lic.exists():
        return None
    candidatos = []
    for child in lic.iterdir():
        if child.is_dir():
            norm = _normalize_token(child.name)
            if "modelo" in norm:
                candidatos.append(child)
    candidatos.sort(key=lambda p: p.name)
    return candidatos[0] if candidatos else None

def detectar_pasta_template(modelos_dir: Path) -> Optional[Path]:
    """
    Dentro de MODELOS, escolhe subpasta-template (ex.: '00_ID-LCT_...').
    Critério: conter 'idlct' ou ('id' e 'lct').
    """
    if not modelos_dir.exists():
        return None
    candidatos = []
    for child in modelos_dir.iterdir():
        if child.is_dir():
            n = _normalize_token(child.name)
            if "idlct" in n or ("id" in n and "lct" in n):
                candidatos.append(child)
    if not candidatos:
        for child in modelos_dir.iterdir():
            if child.is_dir():
                candidatos.append(child)
                break
    candidatos.sort(key=lambda p: p.name)
    return candidatos[0] if candidatos else None


# ============================================================
# Resolução do mês existente (variações como "2. FEVEREIRO" vs "2.FEVEREIRO")
# ============================================================

def resolver_pasta_mes(base_participar: Path, mes_escolhido: str) -> Path:
    try:
        mes_texto = mes_escolhido.split(".")[1].strip()
    except Exception:
        mes_texto = mes_escolhido
    token_mes_puro = _normalize_token(mes_texto)

    for child in base_participar.iterdir():
        if child.is_dir():
            n = _normalize_token(child.name)
            if token_mes_puro in n:
                return child

    pasta = base_participar / mes_escolhido
    pasta.mkdir(parents=True, exist_ok=True)
    return pasta


# ============================================================
# Montagem do nome da licitação
# ============================================================

def montar_nome_licitacao(dia: str, id_lct: str, portal: str, gp: bool, cidade_uf: str) -> str:
    token_gp = "_GP" if gp else ""
    return f"{dia.strip()}_{id_lct.strip()}_{portal.strip()}{token_gp}_{cidade_uf.strip()}"


# ============================================================
# Criação de árvore e cópias (resiliente)
# ============================================================

def criar_estrutura_licitacao(destino_raiz: Path) -> None:
    for rel in SUBPASTAS_DESTINO:
        (destino_raiz / rel).mkdir(parents=True, exist_ok=True)

def _listar_subdirs(p: Path) -> List[Path]:
    return sorted([c for c in p.iterdir() if c.is_dir()], key=lambda x: x.name)

def _resolver_subpasta_flex(model_root: Path, rel_path: str) -> Optional[Path]:
    """
    Resolve '3. EDITAVEIS/1. DECLARACAO' no template tolerando variações
    (números, pontos, acentos, underscores). Matching nível a nível.
    """
    current = model_root
    for part in Path(rel_path).parts:
        alvo = _normalize_token(part)
        candidatos = _listar_subdirs(current)
        escolhido = None

        # 1) match exato após normalização
        for c in candidatos:
            if _normalize_token(c.name) == alvo:
                escolhido = c
                break

        # 2) contém/contido
        if not escolhido:
            for c in candidatos:
                n = _normalize_token(c.name)
                if alvo in n or n in alvo:
                    escolhido = c
                    break

        if not escolhido:
            return None

        current = escolhido

    return current

def _proximo_nome_livre(pasta: Path, nome: str) -> Path:
    stem = Path(nome).stem
    suf = Path(nome).suffix
    i = 1
    candidato = pasta / nome
    while candidato.exists():
        candidato = pasta / f"{stem}_{i}{suf}"
        i += 1
    return candidato

def copiar_padrao_resiliente(
    raiz_modelo_template: Path,
    raiz_destino: Path,
    subpastas_selecionadas: List[str],
    politica: str,
    log: Callable[[str, str], None],
) -> None:
    """
    Copia arquivos padrão com resolução flexível das subpastas.
    Usa log(level, msg) com níveis: "ok", "info", "warn", "error".
    """
    for rel in subpastas_selecionadas:
        # tentativa direta:
        src_dir = raiz_modelo_template / rel
        if not src_dir.exists():
            # fallback: resolução flexível
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
            destino_arquivo = dst_dir / item.name

            try:
                if destino_arquivo.exists():
                    if politica == "pular":
                        log("info", f"[pular] {destino_arquivo.name} já existe.")
                        continue
                    elif politica == "substituir":
                        shutil.copy2(item, destino_arquivo)
                        log("ok", f"[substituir] {destino_arquivo.name}")
                    else:  # duplicar
                        destino_arquivo = _proximo_nome_livre(dst_dir, item.name)
                        shutil.copy2(item, destino_arquivo)
                        log("ok", f"[duplicar] {destino_arquivo.name}")
                else:
                    shutil.copy2(item, destino_arquivo)
                    log("ok", f"[copiar] {destino_arquivo.name}")
            except Exception as e:
                log("error", f"Falha ao copiar '{item.name}': {e}")

def anexar_arquivos(
    arquivos: List[Path],
    raiz_destino: Path,
    subpasta_destino_rel: str,
    politica: str,
    log: Callable[[str, str], None],
) -> None:
    dst_dir = raiz_destino / subpasta_destino_rel
    dst_dir.mkdir(parents=True, exist_ok=True)

    for src in arquivos:
        if not src.exists() or not src.is_file():
            log("warn", f"Ignorado (não é arquivo): {src}")
            continue

        try:
            destino = dst_dir / src.name
            if destino.exists():
                if politica == "pular":
                    log("info", f"[pular] {destino.name} já existe.")
                    continue
                elif politica == "substituir":
                    shutil.copy2(src, destino)
                    log("ok", f"[substituir] {destino.name}")
                else:  # duplicar
                    destino = _proximo_nome_livre(dst_dir, src.name)
                    shutil.copy2(src, destino)
                    log("ok", f"[duplicar] {destino.name}")
            else:
                shutil.copy2(src, destino)
                log("ok", f"[copiar] {destino.name}")
        except Exception as e:
            log("error", f"Falha ao anexar '{src.name}': {e}")


# ============================================================
# UI — Tema e componentes
# ============================================================

class StyledApp(tk.Tk):
    """
    Janela principal — com tema e componentes estilizados (ttk).
    """
    def __init__(self) -> None:
        super().__init__()

        # --------- Tema base ---------
        self.title("Licitagov — Criar Licitação no Mês")
        self.geometry("980x680")
        self.minsize(920, 640)

        try:
            self.call("tk", "scaling", 1.2)
        except tk.TclError:
            pass

        # Paleta
        self.PRIMARY = "#0B5ED7"     # azul principal
        self.PRIMARY_DARK = "#0948A8"
        self.BG = "#F6F7FB"
        self.CARD = "#FFFFFF"
        self.TEXT = "#1B1F23"
        self.MUTED = "#6B7280"
        self.OK = "#16A34A"
        self.WARN = "#EAB308"
        self.ERROR = "#DC2626"

        # ----- ttk Style -----
        style = ttk.Style(self)
        if "vista" in style.theme_names():
            style.theme_use("vista")
        else:
            try:
                style.theme_use("clam")
            except Exception:
                pass

        style.configure(".", font=("Segoe UI", 10))

        style.configure("TFrame", background=self.BG)
        style.configure("Card.TFrame", background=self.CARD, relief="flat")
        style.configure("Header.TFrame", background=self.CARD)

        style.configure("TLabel", background=self.BG, foreground=self.TEXT)
        style.configure("Header.TLabel", background=self.CARD, foreground=self.TEXT, font=("Segoe UI Semibold", 16))
        style.configure("Subheader.TLabel", background=self.CARD, foreground=self.MUTED, font=("Segoe UI", 10))

        style.configure("Section.TLabelframe", background=self.BG)
        style.configure("Section.TLabelframe.Label", background=self.BG, foreground=self.TEXT, font=("Segoe UI Semibold", 11))
        style.configure("Section.TLabelframe.Label", padding=4)
        style.configure("Section.TLabelframe", relief="flat")

        # Botões
        style.configure("Primary.TButton", background=self.PRIMARY, foreground="#fff")
        style.map("Primary.TButton",
                  background=[("active", self.PRIMARY_DARK)],
                  foreground=[("active", "#fff")])
        style.configure("TButton", padding=6)

        # Combobox/Entry
        style.configure("TCombobox", padding=4)
        style.configure("TEntry", padding=4)

        # Progressbar
        style.configure("TProgressbar", troughcolor="#E5E7EB", background=self.PRIMARY)

        # --------- Estado global ---------
        self.error_count = 0
        self.warn_count = 0
        self.last_status = "ok"  # ok | warn | error

        # --------- Variáveis de negócio ---------
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

        # --------- Layout raiz ---------
        root = ttk.Frame(self, style="TFrame", padding=14)
        root.pack(fill="both", expand=True)

        # Header Card
        header = ttk.Frame(root, style="Header.TFrame", padding=16)
        header.pack(fill="x", expand=False, pady=(0, 12))
        ttk.Label(header, text="Licitagov — Criador de Licitações", style="Header.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(header, text="Crie licitações padrão, copie modelos e anexe arquivos — sem erros.", style="Subheader.TLabel")\
            .grid(row=1, column=0, sticky="w", pady=(4, 0))

        # Status badge + contadores
        self.status_wrap = ttk.Frame(header, style="Header.TFrame")
        self.status_wrap.grid(row=0, column=1, rowspan=2, sticky="e")
        self.status_badge = ttk.Label(self.status_wrap, text="🟢 OK", style="Subheader.TLabel", font=("Segoe UI Semibold", 10))
        self.status_badge.grid(row=0, column=0, sticky="e")
        self.status_counts = ttk.Label(self.status_wrap, text="Avisos: 0  |  Erros: 0", style="Subheader.TLabel")
        self.status_counts.grid(row=1, column=0, sticky="e", pady=(4, 0))

        # Corpo dividido em 2 colunas (esq: inputs, dir: revisão/log)
        body = ttk.Frame(root, style="TFrame")
        body.pack(fill="both", expand=True)

        # Coluna esquerda (inputs)
        left = ttk.Frame(body, style="TFrame")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        # Seção 1 — Mês e Nome
        sec1 = ttk.Labelframe(left, text="1) Mês e nome da licitação", style="Section.TLabelframe", padding=12)
        sec1.pack(fill="x", pady=(0, 10))
        row = 0
        ttk.Label(sec1, text="Mês").grid(row=row, column=0, sticky="w"); 
        ttk.Combobox(sec1, values=MESES, textvariable=self.var_mes, state="readonly", width=18)\
            .grid(row=row, column=1, sticky="w", padx=(6, 0))
        ttk.Label(sec1, text="Dia (00)").grid(row=row, column=2, sticky="w", padx=(12, 0)); 
        ttk.Entry(sec1, textvariable=self.var_dia, width=6).grid(row=row, column=3, sticky="w")
        row += 1
        ttk.Label(sec1, text="ID-LCT").grid(row=row, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(sec1, textvariable=self.var_idlct, width=12).grid(row=row, column=1, sticky="w", pady=(8, 0))
        ttk.Label(sec1, text="Portal").grid(row=row, column=2, sticky="w", pady=(8, 0))
        ttk.Entry(sec1, textvariable=self.var_portal, width=12).grid(row=row, column=3, sticky="w", pady=(8, 0))
        ttk.Checkbutton(sec1, text="GP", variable=self.var_gp).grid(row=row, column=4, sticky="w", padx=(12, 0), pady=(8, 0))

        row += 1
        ttk.Label(sec1, text="Cidade-UF").grid(row=row, column=0, sticky="w", pady=(8, 2))
        ttk.Entry(sec1, textvariable=self.var_cidadeuf, width=24).grid(row=row, column=1, columnspan=3, sticky="w", pady=(8, 2))

        row += 1
        ttk.Label(sec1, text="Prévia do nome").grid(row=row, column=0, sticky="w", pady=(10, 0))
        self.lbl_preview = ttk.Label(sec1, text="", foreground=self.PRIMARY, font=("Segoe UI Semibold", 10))
        self.lbl_preview.grid(row=row, column=1, columnspan=4, sticky="w", pady=(10, 0))
        for v in (self.var_dia, self.var_idlct, self.var_portal, self.var_gp, self.var_cidadeuf):
            v.trace_add("write", self._update_preview)
        self._update_preview()

        # Seção 2 — Modelo & Template
        sec2 = ttk.Labelframe(left, text="2) Pasta MODELOS e subpasta TEMPLATE (fonte)", style="Section.TLabelframe", padding=12)
        sec2.pack(fill="x", pady=(0, 10))
        ttk.Label(sec2, text="MODELOS (raiz)").grid(row=0, column=0, sticky="w")
        ttk.Entry(sec2, textvariable=self.var_modelos_path).grid(row=1, column=0, columnspan=2, sticky="ew", pady=(2, 6))
        ttk.Button(sec2, text="Alterar…", command=self._escolher_modelos).grid(row=1, column=2, sticky="w", padx=(8, 0))
        sec2.columnconfigure(0, weight=1)

        ttk.Label(sec2, text="TEMPLATE (ex.: 00_ID-LCT_...)").grid(row=2, column=0, sticky="w", pady=(6, 0))
        ttk.Entry(sec2, textvariable=self.var_template_path).grid(row=3, column=0, columnspan=2, sticky="ew", pady=(2, 6))
        ttk.Button(sec2, text="Detectar de novo", command=self._detectar_template).grid(row=3, column=2, sticky="w", padx=(8, 0))

        ttk.Label(sec2, text="Política de conflito").grid(row=4, column=0, sticky="w", pady=(8, 0))
        ttk.Combobox(sec2, values=["pular", "substituir", "duplicar"], textvariable=self.var_politica, state="readonly", width=12)\
            .grid(row=4, column=1, sticky="w", pady=(8, 0))

        # Seção 3 — Subpastas padrão
        sec3 = ttk.Labelframe(left, text="3) Subpastas de PADRÃO para copiar (** = pré-selecionadas)", style="Section.TLabelframe", padding=12)
        sec3.pack(fill="both", expand=True, pady=(0, 10))
        # Grid dinâmico (2 colunas) para não ficar muito alto
        for i, rel in enumerate(SUBPASTAS_DESTINO):
            col = 0 if i < (len(SUBPASTAS_DESTINO)+1)//2 else 1
            row = i if col == 0 else i - (len(SUBPASTAS_DESTINO)+1)//2
            ttk.Checkbutton(sec3, text=rel, variable=self.vars_subpastas[rel]).grid(row=row, column=col, sticky="w", pady=2, padx=2)
        sec3.columnconfigure(0, weight=1); sec3.columnconfigure(1, weight=1)

        # Seção 4 — Anexos
        sec4 = ttk.Labelframe(left, text="4) Anexos do usuário", style="Section.TLabelframe", padding=12)
        sec4.pack(fill="x", pady=(0, 10))
        ttk.Label(sec4, text="Destino dos anexos").grid(row=0, column=0, sticky="w")
        ttk.Combobox(sec4, values=SUBPASTAS_DESTINO, textvariable=self.var_anexos_destino, state="readonly", width=40)\
            .grid(row=0, column=1, sticky="w")
        ttk.Button(sec4, text="Adicionar arquivos…", command=self._add_anexos).grid(row=0, column=2, padx=(8, 0))
        ttk.Button(sec4, text="Limpar lista", command=self._limpar_anexos).grid(row=0, column=3, padx=(6, 0))
        self.lst_anexos = tk.Listbox(sec4, height=5)
        self.lst_anexos.grid(row=1, column=0, columnspan=4, sticky="ew", pady=(6, 0))
        sec4.columnconfigure(0, weight=1)

        # Coluna direita (revisão / execução / log)
        right = ttk.Frame(body, style="TFrame")
        right.grid(row=0, column=1, sticky="nsew")
        body.columnconfigure(1, weight=1)

        # Card de execução
        exec_card = ttk.Frame(right, style="Card.TFrame", padding=16)
        exec_card.pack(fill="x", pady=(0, 10))
        ttk.Label(exec_card, text="Execução", style="Header.TLabel", font=("Segoe UI Semibold", 12)).grid(row=0, column=0, sticky="w")

        self.btn_criar = ttk.Button(exec_card, text="Criar licitação", style="Primary.TButton", command=self._criar)
        self.btn_criar.grid(row=1, column=0, sticky="w", pady=(8, 0))
        ttk.Button(exec_card, text="Abrir pasta", command=self._abrir_destino).grid(row=1, column=1, sticky="w", padx=(8, 0), pady=(8, 0))
        ttk.Button(exec_card, text="Limpar log", command=self._log_clear).grid(row=1, column=2, sticky="w", padx=(8, 0), pady=(8, 0))

        # Barra de progresso
        self.progress = ttk.Progressbar(exec_card, mode="determinate")
        self.progress.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(10, 0))
        exec_card.columnconfigure(0, weight=1)

        # Filtros de log
        filter_card = ttk.Frame(right, style="Card.TFrame", padding=10)
        filter_card.pack(fill="x", pady=(0, 10))
        ttk.Label(filter_card, text="Log — Filtros").grid(row=0, column=0, sticky="w")
        self.log_filter = tk.StringVar(value="all")
        for i, (val, label) in enumerate([("all", "Tudo"), ("info", "Info"), ("warn", "Avisos"), ("error", "Erros")]):
            ttk.Radiobutton(filter_card, text=label, value=val, variable=self.log_filter, command=self._apply_log_filter)\
                .grid(row=0, column=i+1, sticky="w", padx=6)

        # Log (Text) com tags coloridas
        log_card = ttk.Frame(right, style="Card.TFrame", padding=0)
        log_card.pack(fill="both", expand=True)
        self.txt_log = tk.Text(log_card, height=16, wrap="word", relief="flat", padx=12, pady=12, bg=self.CARD, fg=self.TEXT)
        self.txt_log.pack(fill="both", expand=True, side="left")
        sb = ttk.Scrollbar(log_card, orient="vertical", command=self.txt_log.yview)
        sb.pack(fill="y", side="right")
        self.txt_log.configure(yscrollcommand=sb.set)
        # Tags de cor
        self.txt_log.tag_config("ok", foreground=self.OK)
        self.txt_log.tag_config("info", foreground=self.PRIMARY)
        self.txt_log.tag_config("warn", foreground=self.WARN)
        self.txt_log.tag_config("error", foreground=self.ERROR, underline=1)

        # Linha de status (toast)
        self.toast = ttk.Label(root, text="", style="Subheader.TLabel")
        self.toast.pack(fill="x", pady=(10, 0))

    # -------------------- helpers UI --------------------

    def _set_status(self, level: str) -> None:
        """Atualiza badge de status e contadores."""
        if level == "error":
            self.last_status = "error"
            self.error_count += 1
        elif level == "warn":
            if self.last_status != "error":
                self.last_status = "warn"
            self.warn_count += 1
        # badge
        badge = "🟢 OK"
        if self.last_status == "warn":
            badge = "🟡 Avisos"
        elif self.last_status == "error":
            badge = "🔴 Erros"
        self.status_badge.config(text=badge)
        self.status_counts.config(text=f"Avisos: {self.warn_count}  |  Erros: {self.error_count}")

    def _toast(self, msg: str, level: str = "info") -> None:
        """Mensagem breve na linha de status."""
        color = {"ok": self.OK, "info": self.PRIMARY, "warn": self.WARN, "error": self.ERROR}.get(level, self.MUTED)
        self.toast.config(text=msg, foreground=color)
        # reverte após alguns segundos
        self.after(4000, lambda: self.toast.config(text="", foreground=self.MUTED))

    def _log_line(self, level: str, msg: string) -> None:  # type: ignore[name-defined]
        """Escreve uma linha no log com tag de cor e aplica filtro atual."""
        # armazenar nível na própria linha (como tag e prefixo oculto entre colchetes)
        line = f"[{level.upper()}] {msg}\n"
        self.txt_log.insert("end", line, (level,))
        self.txt_log.see("end")
        self._apply_log_filter()  # re-filtra
        if level in ("warn", "error"):
            self._set_status(level)

    # python 3.8 compat
    def _log(self, level: str, msg: str) -> None:
        self._log_line(level, msg)

    def _log_clear(self) -> None:
        self.txt_log.delete("1.0", "end")
        self.toast.config(text="")
        self.error_count = 0
        self.warn_count = 0
        self.last_status = "ok"
        self._set_status("ok")  # reseta badge/contadores (sem incrementar)

    def _apply_log_filter(self) -> None:
        """Mostra/esconde linhas por tag de nível."""
        show = self.log_filter.get()  # all | info | warn | error
        # habilita tudo
        self.txt_log.tag_configure("hidden", elide=False)
        # esconde seletivamente
        if show != "all":
            for lvl in ("ok", "info", "warn", "error"):
                self.txt_log.tag_remove("hidden", "1.0", "end")
                if lvl != show:
                    # percorre linhas e marca as que têm apenas essa tag
                    start = "1.0"
                    while True:
                        idx = self.txt_log.search(rf"\[{lvl.upper()}\]", start, stopindex="end", regexp=True)
                        if not idx:
                            break
                        line_end = f"{idx.split('.')[0]}.end"
                        self.txt_log.tag_add("hidden", idx, line_end)
                        start = line_end
            self.txt_log.tag_configure("hidden", elide=True)
        else:
            self.txt_log.tag_configure("hidden", elide=False)

    def _update_preview(self, *_args) -> None:
        nome = montar_nome_licitacao(
            self.var_dia.get(), self.var_idlct.get(), self.var_portal.get(),
            self.var_gp.get(), self.var_cidadeuf.get()
        )
        self.lbl_preview.config(text=nome)

    def _escolher_modelos(self) -> None:
        p = filedialog.askdirectory(title="Selecione a pasta MODELOS (raiz)")
        if p:
            self.var_modelos_path.set(p)
            self._detectar_template()

    def _detectar_template(self) -> None:
        modelos = Path(self.var_modelos_path.get().strip())
        if not modelos.exists():
            modelos = detectar_pasta_modelos() or modelos
            self.var_modelos_path.set(str(modelos) if modelos else "")
        template = detectar_pasta_template(modelos) if modelos else None
        self.var_template_path.set(str(template) if template else "")
        if template and template.exists():
            self._toast("Template detectado com sucesso.", "ok")
        else:
            self._toast("Não foi possível detectar o template.", "warn")

    def _add_anexos(self) -> None:
        files = filedialog.askopenfilenames(title="Selecione os arquivos para anexar")
        if files:
            for f in files:
                p = Path(f)
                if p not in self.anexos_arquivos:
                    self.anexos_arquivos.append(p)
                    self.lst_anexos.insert("end", str(p))

    def _limpar_anexos(self) -> None:
        self.anexos_arquivos.clear()
        self.lst_anexos.delete(0, "end")

    def _abrir_destino(self) -> None:
        if not self.destino_criado:
            messagebox.showinfo("Info", "Crie uma licitação primeiro.")
            return
        path = str(Path(self.destino_criado).resolve())
        try:
            if os.name == "nt":
                os.startfile(path)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                import subprocess; subprocess.run(["open", path])
            else:
                import subprocess; subprocess.run(["xdg-open", path])
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível abrir a pasta:\n{e}")

    # -------------------- ação principal --------------------

    def _criar(self) -> None:
        """Pipeline completo com progress bar e logs coloridos."""
        self._log_clear()
        self._toast("Iniciando criação…", "info")
        self.btn_criar.state(["disabled"])
        self.progress.config(mode="indeterminate")
        self.progress.start(12)

        try:
            # 1) Pasta do mês
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

            # 2) Pasta da licitação
            nome = self.lbl_preview.cget("text")
            destino_raiz = pasta_mes / nome
            try:
                destino_raiz.mkdir(parents=True, exist_ok=True)
                self._log("ok", f"Licitação: {destino_raiz}")
            except Exception as e:
                self._log("error", f"Falha ao criar pasta da licitação: {e}")
                messagebox.showerror("Erro", f"Não foi possível criar a pasta da licitação:\n{e}")
                return

            # 3) Subpastas
            try:
                criar_estrutura_licitacao(destino_raiz)
            except Exception as e:
                self._log("error", f"Falha ao criar subpastas: {e}")
                messagebox.showerror("Erro", f"Falha ao criar subpastas:\n{e}")
                return

            # 4) MODELOS + TEMPLATE
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
                        copiar_padrao_resiliente(
                            raiz_modelo_template=template,
                            raiz_destino=destino_raiz,
                            subpastas_selecionadas=selecionadas,
                            politica=self.var_politica.get(),
                            log=self._log,
                        )
                    except Exception as e:
                        self._log("error", f"Falha ao copiar padrões: {e}")
                        messagebox.showerror("Erro", f"Falha ao copiar padrões:\n{e}")
                        return

            # 5) Anexos do usuário
            if self.anexos_arquivos:
                try:
                    anexar_arquivos(
                        arquivos=self.anexos_arquivos,
                        raiz_destino=destino_raiz,
                        subpasta_destino_rel=self.var_anexos_destino.get(),
                        politica=self.var_politica.get(),
                        log=self._log,
                    )
                except Exception as e:
                    self._log("error", f"Falha ao anexar arquivos: {e}")
                    messagebox.showerror("Erro", f"Falha ao anexar arquivos:\n{e}")
                    return

            self.destino_criado = destino_raiz
            if self.error_count > 0:
                self._toast("Concluído com erros. Verifique o log.", "error")
            elif self.warn_count > 0:
                self._toast("Concluído com avisos. Verifique o log.", "warn")
            else:
                self._toast("Licitação criada com sucesso!", "ok")

        finally:
            self.progress.stop()
            self.progress.config(mode="determinate", value=100)
            self.btn_criar.state(["!disabled"])

# ------------------------------------------------------------
# Entrada
# ------------------------------------------------------------

if __name__ == "__main__":
    StyledApp().mainloop()
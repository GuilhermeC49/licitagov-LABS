#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Licitagov — Criador de Estruturas de Pastas (GUI)
--------------------------------------------------
Aplicativo simples com interface gráfica para criar automaticamente
uma árvore de pastas/subpastas a partir de um modelo (dict aninhado).

• Você cola o caminho da pasta do cliente OU seleciona pelo botão.
• Clica em "Criar estrutura" e a árvore é criada.

Requisitos: Python 3.8+ (Tkinter já vem com o Python padrão no Windows).
"""

from __future__ import annotations

import tkinter as tk                    # Toolkit básico da interface
from tkinter import ttk, filedialog, messagebox
from pathlib import Path                # Manipulação elegante de caminhos (Windows/Linux/Mac)
from typing import Callable, Iterable, Mapping, Union

# ------------------------------------------------------------
# MODELO DE ESTRUTURA
# ------------------------------------------------------------
# Representa a árvore de pastas que será criada.
# • Dicionário = pasta com filhos (subpastas).
# • {} (dict vazio) = pasta “folha” (sem filhos).
# • Você pode renomear, adicionar ou remover nós livremente.
ESTRUTURA_PADRAO: Mapping[str, Union[dict, list]] = {
    "00. Editais_ANALISAR": {},
    "01. Licitacao": {
        "01. Participar": {
            "01. JANEIRO": {},
            "02. FEVEREIRO": {},
            "03. MARCO": {},
            "04. ABRIL": {},
            "05. MAIO": {},
            "06. JUNHO": {},
            "07. JULHO": {},
            "08. AGOSTO": {},
            "09. SETEMBRO": {},
            "10. OUTUBRO": {},
            "11. NOVEMBRO": {},
            "12. DEZEMBRO": {},
        },
        "02. Vencedora": {},
        "03. Declinada": {},
        "04. Suspensa": {},
        "05. Modelos_Padrao": {
            "DECLARACAO": {},
            "PROPOSTA": {},
            "PLANILHA": {},
        },
    },
    "02. Empresa": {
        "01. CNPJ": {},
        "02. Socios": {},
        "03. Alvara": {},
        "04. Dados_Bancarios": {},
        "05. Contrato_Social": {},
        "06. Balanco_Patrimonial": {},
        "07. Certidoes": {},
        "08. Acessos": {},
        "09. CAF_Digital_BA": {},
        "10. SICAF": {},
        "11. Compras_Salvador": {},
        "12. Encargos_Tributacao": {},
        "13. SMS": {},
        "14. Compras_FIEB": {},
        "15. Impostos": {},
        "16. Juridico": {},
        "17. Financeiro": {},
        "18. Antecipa_EMBASA": {},
        "19. Inscricao_Estadual": {},
        "20. Inscricao_Municipal": {},
    },
    "03. Qualificacao_Tecnica": {
        "01. RT": {},
        "02. ACT": {},
        "03. CAT": {},
        "04. CAO": {},
        "05. CREA_PJ": {},
        "06. CREA_PF": {},
        "07. ART_CONTRATOS": {},
    },
    "04. Orcamentos_Propostas": {},
    "05. Planejamento_Gestao": {},
    "06. Biblioteca": {
        "01. Logo_Marca": {},
        "02. Carimbos": {},
        "03. Assinatura": {},
        "04. Modelos_Administrativos": {
            "01. Recurso": {},
            "02. Contrarrazao": {},
            "03. Impugnacao": {},
            "04. Esclarecimento": {},
        },
    },
}


# ------------------------------------------------------------
# FUNÇÕES DE LÓGICA (independentes da interface)
# ------------------------------------------------------------
def criar_arvore(
    base: Path,
    modelo: Union[Mapping[str, Union[dict, list]], Iterable[str]],
    log: Callable[[str], None] = lambda _msg: None,
    nivel: int = 0,
) -> None:
    """
    Cria diretórios recursivamente a partir de um 'modelo'.

    Parâmetros:
    • base: pasta raiz onde a estrutura será criada.
    • modelo: dict (pastas -> filhos) OU lista (pastas folhas).
    • log: função de logging (para imprimir na UI).
    • nivel: profundidade atual (apenas para formatação do log).

    Observações:
    • Se a pasta já existir, não dá erro (exist_ok=True).
    • Mantém a ordem declarada (Python 3.7+ preserva ordem de dict).
    """
    # Se vier um dict, iteramos pelos pares (nome, subárvore).
    if isinstance(modelo, Mapping):
        itens = modelo.items()
    else:
        # Se vier uma lista, cada item é uma pasta “folha”.
        itens = [(nome, {}) for nome in modelo]

    for nome, sub in itens:
        destino = base / str(nome)

        try:
            # Cria a pasta atual (e qualquer pai ausente)
            destino.mkdir(parents=True, exist_ok=True)
            log(f"{'  ' * nivel}Criado: {destino}")
        except Exception as e:
            # Registra e continua (não aborta a execução inteira)
            log(f"{'  ' * nivel}[ERRO] {destino} -> {e}")

        # Caso haja filhos (subpastas), chamamos recursivamente
        if isinstance(sub, (Mapping, list)) and sub:
            criar_arvore(destino, sub, log, nivel + 1)


# ------------------------------------------------------------
# INTERFACE GRÁFICA (Tkinter)
# ------------------------------------------------------------
class App(tk.Tk):
    """
    Janela principal do aplicativo.
    Optamos por uma classe para:
    • Encapsular estados (ex.: campo de caminho, caixa de log).
    • Manter o código organizado e fácil de evoluir.
    """

    def __init__(self) -> None:
        super().__init__()

        # --- Metadados da janela ---
        self.title("Licitagov — Criador de Estruturas")
        self.geometry("760x460")   # Tamanho inicial da janela
        self.minsize(700, 400)     # Tamanho mínimo (evita “quebrar” o layout)

        # Escala de DPI (melhora a legibilidade em telas densas)
        try:
            self.call("tk", "scaling", 1.2)
        except tk.TclError:
            pass

        # --- Frame raiz com padding para “respiro” visual ---
        root = ttk.Frame(self, padding=16)
        root.pack(fill="both", expand=True)

        # --- Linha 0: Texto explicativo ---
        ttk.Label(
            root,
            text="Cole o caminho da pasta do cliente ou selecione:",
        ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 8))

        # --- Linha 1: Campo de caminho + botão "Selecionar pasta..." ---
        self.var_path = tk.StringVar()
        self.entry_path = ttk.Entry(root, textvariable=self.var_path)
        self.entry_path.grid(row=1, column=0, columnspan=2, sticky="ew", padx=(0, 8))
        root.columnconfigure(0, weight=1)  # Permite expandir a coluna 0

        ttk.Button(
            root,
            text="Selecionar pasta…",
            command=self.selecionar_pasta,
        ).grid(row=1, column=2, sticky="ew")

        # --- Linha 2: Botões de ação ---
        self.btn_criar = ttk.Button(root, text="Criar estrutura", command=self.acao_criar)
        self.btn_criar.grid(row=2, column=0, sticky="w", pady=(12, 8))

        ttk.Button(root, text="Limpar log", command=self.limpar_log).grid(
            row=2, column=1, sticky="w", pady=(12, 8)
        )

        # --- Linha 3: Caixa de log + Scrollbar ---
        self.txt_log = tk.Text(root, height=14, wrap="word")
        self.txt_log.grid(row=3, column=0, columnspan=3, sticky="nsew", pady=(8, 0))
        root.rowconfigure(3, weight=1)  # Área central cresce quando a janela é redimensionada

        sb = ttk.Scrollbar(root, orient="vertical", command=self.txt_log.yview)
        sb.grid(row=3, column=3, sticky="ns")
        self.txt_log.configure(yscrollcommand=sb.set)

        # --- Linha 4: Rodapé (uma dica de uso) ---
        ttk.Label(
            root,
            text="Dica: caminhos como C:\\Clientes\\EmpresaX ou \\\\Servidor\\Compartilhamento são aceitos.",
            foreground="#555",
        ).grid(row=4, column=0, columnspan=3, sticky="w", pady=(8, 0))

    # ---------------------------
    # Utilitários de interface
    # ---------------------------
    def log(self, msg: str) -> None:
        """Escreve uma linha na caixa de log e rola até o fim."""
        self.txt_log.insert("end", msg + "\n")
        self.txt_log.see("end")
        self.update_idletasks()

    def limpar_log(self) -> None:
        """Limpa todo o conteúdo da caixa de log."""
        self.txt_log.delete("1.0", "end")

    def selecionar_pasta(self) -> None:
        """Abre um seletor de pastas e preenche o campo com o caminho escolhido."""
        pasta = filedialog.askdirectory(title="Selecione a pasta do cliente")
        if pasta:
            self.var_path.set(pasta)

    # ---------------------------
    # Ação principal (criar)
    # ---------------------------
    def acao_criar(self) -> None:
        """
        Valida o caminho informado, garante que exista (cria se necessário)
        e dispara a criação recursiva da estrutura.
        """
        caminho = self.var_path.get().strip()

        if not caminho:
            messagebox.showwarning("Atenção", "Informe ou selecione a pasta do cliente.")
            return

        base = Path(caminho)

        # Se a pasta base não existir, tentamos criá-la (com pais, se preciso)
        if not base.exists():
            try:
                base.mkdir(parents=True, exist_ok=True)
                self.log(f"Pasta base inexistente — criada: {base}")
            except Exception as e:
                messagebox.showerror("Erro", f"Não foi possível criar a pasta base:\n{e}")
                return

        # Feedback visual: desabilita o botão enquanto executa
        self.btn_criar.config(state="disabled")
        self.log(f"Iniciando criação em: {base}")

        try:
            # Cria toda a árvore e faz log em cada passo
            criar_arvore(base, ESTRUTURA_PADRAO, log=self.log)
            self.log("Concluído.")
            messagebox.showinfo("Pronto", "Estrutura criada com sucesso!")
        except Exception as e:
            # Qualquer erro inesperado é mostrado e registrado
            self.log(f"[ERRO] {e}")
            messagebox.showerror("Erro", f"Ocorreu um erro:\n{e}")
        finally:
            # Reabilita o botão, independente do resultado
            self.btn_criar.config(state="normal")


# ------------------------------------------------------------
# PONTO DE ENTRADA
# ------------------------------------------------------------
if __name__ == "__main__":
    # Inicia a aplicação. O mainloop mantém a janela “viva” até o usuário fechar.
    App().mainloop()
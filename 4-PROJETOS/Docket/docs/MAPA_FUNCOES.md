# Mapa de Funções — Docket
> Índice técnico com IDs para referência rápida em discussões, issues e PRs.  
> Convenções de status: ✅ Ok · 🔧 Melhorar · 🆕 Planejado

---

## 0) Convenções gerais

- **Arquivos (organização recomendada)**
  - `core/naming.py` — nomenclatura da licitação
  - `core/paths.py` — detecção de cliente e resolução de caminhos
  - `core/copyops.py` — cópias, conflitos, anexos, filtros de seleção
  - `core/map_client.py` — mapeamento de fontes do cliente (documentos por subpasta)
  - `core/config.py` — leitura/escrita de configurações (JSON)
  - `core/keywords.py` — gestão de keywords (lista branca) e utilidades
  - `core/blacklist.py` — gestão de blacklist por **tag fixa**
  - `core/editaveis.py` — geração de Declarações/Propostas (placeholders)
  - `core/utils.py` — utilidades (normalização, logs, datas, contadores)
  - `ui/` — camada PySide6 (janela principal, wizard, revisão, console)
- **Política de conflito:** `"duplicar" | "substituir" | "pular"`
- **Normalização:** remover numeração/pontos/acentos/hífens/underscores e minúsculas (tokenização).
- **Tags para seleção de arquivos:**
  - **Tag de whitelist (configurável pelo usuário):** `tag_prefix`, padrão `DOCKET__`  
    Ex.: `DOCKET__CNPJ_ConsulTop.pdf`
  - **Tag de blacklist (fixa, não configurável):** `BLACKLIST_TAG` = `DOCKETBLK__`  
    Ex.: `DOCKETBLK__CNPJ_antigo.pdf`  
  - Regras: whitelist tem prioridade; blacklist **sempre exclui**; se não houver whitelist, usa-se **keywords** com aviso.

---

## 1) Núcleo de nomenclatura e caminhos

**F01 — `montar_nome_licitacao(dia, mes_combo, id_lct, portal, gp, cidade_uf) -> str`**  
Gera o nome no padrão `DD-MM_ID-LCT_PORTAL[_GP]_Cidade-UF`.  
- `DD` = dia da disputa (01–31)  
- `MM` = mês numérico a partir do combo (ex.: "03. MARCO" → "03")  
- `PORTAL` = sempre MAIÚSCULO  
- `Cidade` = TitleCase (mantendo “de/da/do/das/dos” minúsculas)  
- `UF` = sempre MAIÚSCULO  
**Local:** `core/naming.py` · **Status:** 🔧 Melhorar (logar `[WARN]` se dia fora de 01–31)  
**Explicação simples:** monta automaticamente o **nome da pasta** seguindo um padrão único para toda a equipe.

---

**F02 — `resolver_pasta_mes_somente_existente(base_participar: Path, mes_combo: str) -> Optional[Path]`**  
Procura a pasta de **mês existente** em `1. Licitacao/1. Participar/`.  
- Tolerante a variações (`2.FEVEREIRO` ↔ `2. FEVEREIRO`)  
- **Nunca cria** pasta nova: se não achar, retorna `None` (UI deve avisar).  
**Local:** `core/paths.py` · **Status:** ✅ Ok  
**Explicação simples:** garante que vamos usar **exatamente as pastas de mês já criadas**, evitando duplicidade.

---

**F03 — `detectar_cliente(path_atual: Path) -> Optional[Path]`**  
Detecta se estamos dentro de uma pasta de **cliente**, verificando presença de `1. Licitacao` e `2. Empresa`.  
**Local:** `core/paths.py` · **Status:** 🆕 Planejado  
**Explicação simples:** entende se o app foi aberto “dentro de um cliente”, para poder localizar todas as pastas padrão automaticamente.

---

**F04 — `detectar_participar_dir(cliente_dir: Path) -> Optional[Path]`**  
Retorna `cliente_dir / "1. Licitacao" / "1. Participar"` se existir.  
**Local:** `core/paths.py` · **Status:** 🆕 Planejado  
**Explicação simples:** acha a pasta “Participar”, onde ficam os meses.

---

**F05 — `detectar_modelos_cliente(cliente_dir: Path) -> Optional[Path]`**  
Opcional: retorna `"5. Modelos_Padrao"` ou `"4. Modelos_Padrao"` se existir.  
**Local:** `core/paths.py` · **Status:** 🆕 Planejado  
**Explicação simples:** permite aplicar modelos do cliente se o usuário desejar (recurso extra).

---

## 2) Configurações, Wizard e persistência

**F06 — `load_settings() -> dict`**  
Carrega `settings.json`. Se não existir, retorna defaults.  
- Defaults: `tag_prefix="DOCKET__"`, `BLACKLIST_TAG="DOCKETBLK__"`, caminhos padrão, keywords base.  
**Local:** `core/config.py` · **Status:** 🆕 Planejado  
**Explicação simples:** lê as configurações salvas (tag, keywords, blacklist, caminhos).

---

**F07 — `save_settings(cfg: dict) -> None`**  
Salva `settings.json`.  
**Local:** `core/config.py` · **Status:** 🆕 Planejado  
**Explicação simples:** grava alterações para persistirem após fechar o app.

---

**F08 — `wizard_primeiro_uso(cliente_dir: Path, cfg: dict) -> dict`**  
Assistente inicial:  
1) Usuário escolhe/ajusta `tag_prefix` (padrão `DOCKET__`).  
2) Confirma **pastas padrão** (CNPJ, Sócios, Contrato, Balanço, CREA, etc.).  
3) Para cada pasta: lista arquivos → usuário **marca “oficiais” (whitelist)** e **marca “blacklist”**.  
4) Programa **renomeia em massa**:  
   - oficiais → adiciona `tag_prefix` no começo  
   - blacklist → adiciona `BLACKLIST_TAG` no começo  
5) Atualiza `cfg` com caminhos e keywords.  
**Local:** `ui/wizard.py` (orquestra) + `core/config.py` / `core/blacklist.py`  
**Status:** 🆕 Planejado  
**Explicação simples:** na primeira vez, o usuário “ensina” o Docket quais arquivos são válidos e quais descartar — tudo salvo para os próximos usos.

---

**F09 — `aplicar_tag_whitelist(arquivo: Path, tag_prefix: str) -> Path`**  
Renomeia arquivo para `tag_prefix + nome_original` (se ainda não tiver).  
**Local:** `core/blacklist.py` · **Status:** 🆕 Planejado  
**Explicação simples:** marca um arquivo como **oficial** (para sempre ser priorizado).

---

**F10 — `aplicar_tag_blacklist(arquivo: Path) -> Path`**  
Renomeia arquivo para `BLACKLIST_TAG + nome_original` (se ainda não tiver).  
**Local:** `core/blacklist.py` · **Status:** 🆕 Planejado  
**Explicação simples:** marca um arquivo como **bloqueado** (nunca será copiado automaticamente).

---

## 3) Normalização / utilidades

**F11 — `_strip_accents(s: str) -> str`**  
Remove acentos via `unicodedata`.  
**Local:** `core/utils.py` · **Status:** ✅ Ok

---

**F12 — `_normalize_token(name: str) -> str`**  
Normaliza nomes (remove numeração inicial, pontos, underscores, hífens, espaços; minúsculas; sem acentos).  
**Local:** `core/utils.py` · **Status:** ✅ Ok

---

**F13 — `_listar_subdirs(p: Path) -> List[Path]`**  
Lista apenas diretórios ordenados.  
**Local:** `core/utils.py` · **Status:** ✅ Ok

---

**F14 — `_resolver_subpasta_flex(model_root: Path, rel_path: str) -> Optional[Path]`**  
Resolve subpasta por aproximação (exato → contém/contido), tolera singular/plural.  
**Local:** `core/utils.py` · **Status:** ✅ Ok  
**Uso:** localizar pastas de origem no cliente e pastas de destino na licitação.

---

## 4) Mapeamento (Cliente como fonte de documentos)

**F15 — `PADROES_CLIENTE: Dict[str, List[Tuple[str, List[str], List[str]]]]`**  
Mapa: **subpasta de destino** → lista de **(pasta_no_cliente, tags_prioritarias, keywords_fallback)**.  
Ex.:  
- `"1. HABILITACAO/1. HAB_JURIDICA"` →  
  - `("2. Empresa/01. CNPJ",        ["{TAG}CNPJ"],          ["CNPJ","Cadastro Nacional","comprovante","cartao"])`  
  - `("2. Empresa/05. Contrato_Social", ["{TAG}CONTRATO_SOCIAL"], ["Contrato Social","Consolidada","alteracao","ata"])`  
  - `("2. Empresa/02. Socios",     ["{TAG}SOCIO_ID"],      ["CNH","RG","CPF","identidade","administrador"])`  
  - `("2. Empresa/03. Alvara",     ["{TAG}ALVARA"],        ["alvara","funcionamento"])`  
- `"1. HABILITACAO/2. HAB_FISCAL"` →  
  - `("2. Empresa/07. Certidoes",  ["{TAG}RFB_PGFN","{TAG}SEFAZ","{TAG}MUNICIPAL","{TAG}FGTS","{TAG}INSS","{TAG}CNDT"], ["federal","pgfn","sefaz","municipal","iss","fgts","crf","inss","previdencia","cndt","trabalhista"])`  
- `"1. HABILITACAO/3. HAB_ECON_FINAN"` →  
  - `("2. Empresa/06. Balanco_Patrimonial", ["{TAG}BALANCO"], ["balanco","bp","demonstra"])`  
- `"1. HABILITACAO/4. QUALIFICACAO_TECNICA"` →  
  - `("3. Qualificacao_Tecnica/05. CREA_PJ", ["{TAG}CREA_PJ"], ["crea pj","registro"])`  
  - `("3. Qualificacao_Tecnica/06. CREA_PF", ["{TAG}CREA_PF"], ["crea pf","registro","profissional"])`  
  - `("3. Qualificacao_Tecnica/03. CAT",     ["{TAG}CAT"],     ["cat","certidao acervo","atestado"])`  
  - `("3. Qualificacao_Tecnica/07. ART_CONTRATOS", ["{TAG}ART"], ["art","rrt","contrato","execucao"])`  
  - `("3. Qualificacao_Tecnica/02. ACT",     ["{TAG}ACT"],     ["atestado","capacidade tecnica","act"])`  
> **Nota:** `{TAG}` é substituído em runtime pelo `tag_prefix` configurado (ex.: `DOCKET__`).

**Local:** `core/map_client.py` · **Status:** 🆕 Planejado  
**Explicação simples:** tabela que diz **de onde pegar** (no cliente) e **para onde enviar** (na licitação), com prioridades.

---

**F16 — `resolver_fontes_cliente(cliente_dir: Path, destino_rel: str, cfg: dict) -> List[Path]`**  
Para uma subpasta de destino, resolve as pastas fonte e normaliza caminhos, usando `PADROES_CLIENTE` + `_resolver_subpasta_flex`.  
**Local:** `core/map_client.py` · **Status:** 🆕 Planejado  
**Explicação simples:** localiza as pastas corretas no cliente que guardam cada documento.

---

**F17 — `selecionar_por_tag_ou_keywords(pasta: Path, tags: List[str], keywords: List[str], cfg: dict) -> Tuple[List[Path], bool]`**  
Seleção em 2 passos:  
1) Prioriza arquivos com **whitelist tag** (`tag_prefix`), ignorando qualquer arquivo com **blacklist tag** (`DOCKETBLK__`).  
2) Se nada encontrado, usa **keywords** (case/acentos-insensitive).  
Retorna `(arquivos, via_keywords: bool)`.  
**Local:** `core/map_client.py` · **Status:** 🆕 Planejado  
**Explicação simples:** escolhe os arquivos certos; se não houver tag, tenta pelas palavras-chave e **avisa** para revisar.

---

**F18 — `escolher_melhor_candidato(arquivos: List[Path]) -> Path`**  
Entre vários candidatos, escolhe o **mais recente** (data de modificação).  
**Local:** `core/map_client.py` · **Status:** 🆕 Planejado  
**Explicação simples:** quando há 2+ versões, pega a mais atual.

---

## 5) Operações de cópia, anexos e conflitos

**F19 — `_proximo_nome_livre(dir: Path, nome: str) -> Path`**  
Gera `arquivo_1.ext`, `arquivo_2.ext`… para política `duplicar`.  
**Local:** `core/copyops.py` · **Status:** ✅ Ok

---

**F20 — `copiar_documentos_cliente(cliente_dir: Path, destino: Path, subpastas: List[str], politica: str, cfg: dict, log: LogFn) -> None`**  
Para cada subpasta destino:  
- `resolver_fontes_cliente` → localizar pastas no cliente  
- `selecionar_por_tag_ou_keywords` → escolher arquivos  
- `escolher_melhor_candidato` se necessário  
- aplicar política de conflito na cópia  
- logar `[WARN]` quando **via keywords**  
**Local:** `core/copyops.py` · **Status:** 🆕 Planejado  
**Explicação simples:** copia os documentos oficiais da empresa para dentro da nova licitação.

---

**F21 — `anexar_arquivos(arquivos: List[Path], raiz_destino: Path, subpasta_destino_rel: str, politica: str, log: LogFn) -> None`**  
Copia anexos do usuário conforme política de conflito.  
**Local:** `core/copyops.py` · **Status:** ✅ Ok  
**Explicação simples:** permite anexar documentos adicionais escolhidos manualmente.

---

## 6) Keywords e Blacklist (gestão pelo usuário)

**F22 — `carregar_keywords(cfg: dict) -> Dict[str, List[str]]`**  
Devolve o dicionário de keywords por categoria.  
**Local:** `core/keywords.py` · **Status:** 🆕 Planejado  
**Explicação simples:** traz as palavras-chave que ajudam a achar documentos quando não há tag.

---

**F23 — `atualizar_keywords(cfg: dict, categoria: str, incluir: List[str], remover: List[str]) -> dict`**  
Atualiza keywords no `cfg` (adiciona/remove) e **persiste**.  
**Local:** `core/keywords.py` · **Status:** 🆕 Planejado  
**Explicação simples:** deixa o usuário ajustar as palavras-chave como preferir.

---

**F24 — `marcar_blacklist_por_arquivo(arquivo: Path) -> Path`**  
Aplica a **tag fixa de blacklist** (`DOCKETBLK__`) renomeando o arquivo.  
**Local:** `core/blacklist.py` · **Status:** 🆕 Planejado  
**Explicação simples:** garante que **aquele arquivo específico** nunca mais será coletado automaticamente.

---

**F25 — `esta_em_blacklist(nome: str) -> bool`**  
Retorna `True` se `nome` começar com `DOCKETBLK__`.  
**Local:** `core/blacklist.py` · **Status:** 🆕 Planejado  
**Explicação simples:** filtro rápido para excluir arquivos bloqueados.

---

## 7) Geração de Editáveis (Declarações/Propostas)

**F26 — `gerar_declaracoes(modelo_docx: Path, destino_dir: Path, dados: dict) -> Tuple[Path, Optional[Path]]`**  
Abre o `.docx` de declarações (pack com ~27), substitui placeholders (ex.: `#ORGÃO_COMPRADOR`, `#PROCESSO`, `#MODALIDADE`, `#NUMERO`, `#VALOR`, `#OBJETO`), salva `.docx` final e também exporta **PDF**.  
**Local:** `core/editaveis.py` · **Status:** 🆕 Planejado  
**Explicação simples:** preenche automaticamente as declarações com os dados da licitação e já gera o PDF.

---

**F27 — `gerar_proposta(modelo_docx: Path, destino_dir: Path, dados: dict) -> Path`**  
Abre o `.docx` de proposta, substitui os 6 placeholders e salva `.docx`.  
**Local:** `core/editaveis.py` · **Status:** 🆕 Planejado  
**Explicação simples:** cria a proposta personalizada da licitação (em Word, para revisão).

---

**F28 — `coletar_dados_editaveis(inputs_ui: Inputs) -> dict`**  
Extrai os campos opcionais preenchidos pelo usuário (órgão, modalidade, processo, número, valor, objeto).  
**Local:** `core/editaveis.py` · **Status:** 🆕 Planejado  
**Explicação simples:** pega da interface os dados que vão ser usados nos documentos.

---

**F29 — `aplicar_editaveis_na_criacao(cfg: dict, destino_licitacao: Path, dados: dict, log: LogFn) -> None`**  
Durante a **criação** da licitação: copia os modelos (ou usa do cliente), aplica placeholders e gera arquivos finais (Declarações: DOCX+PDF; Proposta: DOCX).  
**Local:** `core/editaveis.py` · **Status:** 🆕 Planejado  
**Explicação simples:** tudo pronto logo ao criar a licitação.

---

**F30 — `aplicar_editaveis_em_existente(cfg: dict, licitacao_dir: Path, dados: dict, log: LogFn) -> None`**  
Em uma **licitação já existente**: apenas gera/atualiza Declarações/Proposta dentro das pastas corretas, sem recriar estrutura.  
**Local:** `core/editaveis.py` · **Status:** 🆕 Planejado  
**Explicação simples:** permite gerar/atualizar os documentos a qualquer momento.

---

## 8) Logging, Resumo e Revisão

**F31 — `log(level: str, msg: str) -> None`**  
Registra `[OK]/[WARN]/[ERROR]` com timestamp na UI/arquivo.  
**Local:** `core/utils.py` · **Status:** ✅ Ok

---

**F32 — `ResumoExecucao` (dataclass)**  
Contadores: diretórios criados, arquivos copiados, duplicados, substituídos, anexos, **copiados via keywords**, ignorados por blacklist, erros.  
**Local:** `core/utils.py` · **Status:** 🆕 Planejado  
**Explicação simples:** soma tudo que aconteceu, para exibir no final.

---

**F33 — `finalizar_resumo(resumo: ResumoExecucao) -> str`**  
Gera linha final do resumo.  
Ex.: “Criados X dirs; copiados Y (D duplic., S subst.); via keywords Z (revisar); ignorados blacklist W; anexados N; erros E.”  
**Local:** `core/utils.py` · **Status:** 🆕 Planejado

---

**F34 — `abrir_tela_revisao_automaticamente(result: Execucao, cfg: dict)`**  
Após criar a licitação, **abre automaticamente** a tela “Revisar Documentos” mostrando:  
- lista de arquivos copiados **via keywords** (com opção de abrir/visualizar e **remover + enviar à blacklist**),  
- **resumo final** (contadores),  
- botões: “Confirmar e Fechar”, “Abrir pasta da licitação”.  
**Local:** `ui/revisao.py` · **Status:** 🆕 Planejado  
**Explicação simples:** garante revisão imediata dos itens “menos confiáveis” e dá o resumo completo.

---

## 9) Integração com a UI (PySide6)

**F35 — `on_criar_licitacao(inputs_ui: Inputs) -> None`**  
Fluxo principal:  
- detectar cliente e Participar  
- F02: localizar mês existente  
- criar pasta da licitação  
- F20: copiar documentos do cliente  
- F21: anexos (se houver)  
- F29: aplicar editáveis (se dados fornecidos)  
- F33: finalizar resumo  
- F34: abrir tela de revisão **automaticamente**  
**Local:** `ui/main_window.py` · **Status:** 🆕 Planejado  
**Explicação simples:** botão “Criar Licitação”.

---

**F36 — `on_gerar_editaveis_em_existente(licitacao_dir: Path, dados: dict)`**  
Fluxo para rodar apenas Declarações/Propostas em uma licitação **já criada**.  
**Local:** `ui/main_window.py` · **Status:** 🆕 Planejado  
**Explicação simples:** botão “Gerar documentos em licitação existente”.

---

**F37 — `on_open_wizard()`**  
Abre o Wizard de configuração (primeiro uso ou reconfigurar).  
**Local:** `ui/main_window.py` · **Status:** 🆕 Planejado

---

**F38 — `on_configuracoes()`**  
Tela de Configurações: editar `tag_prefix`, keywords, visualizar/gerenciar arquivos com `DOCKETBLK__`.  
**Local:** `ui/main_window.py` · **Status:** 🆕 Planejado

---

## 10) Regras funcionais (resumo)

- **Fonte padrão:** documentos do **Cliente** (pasta `2. Empresa` e `3. Qualificacao_Tecnica`).  
- **Template:** opcional (apenas se o usuário marcar aplicar modelos do cliente).  
- **Seleção de arquivos:**  
  1) **Whitelist por tag** (prefixo configurável, ex.: `DOCKET__`)  
  2) **Keywords** se não houver tag → loga `[WARN]` e envia à revisão  
  3) **Blacklist por arquivo** (tag fixa `DOCKETBLK__`) sempre exclui  
- **Mês:** **nunca** criar automaticamente (F02); exigir que exista.  
- **Editáveis:** placeholders nos `.docx`; declarações geram também PDF.  
- **Tela de Revisão:** **abre automaticamente** após criar; mostra itens via keywords + resumo; permite enviar arquivo à blacklist.  
- **Persistência:** tudo em `settings.json` (tag_prefix, keywords, caminhos, etc.).

---

## 11) Pendências rastreáveis

- [ ] F03/F04 — Detecção de cliente e Participar  
- [ ] F06–F10 — Configurações + Wizard (tags em massa)  
- [ ] F15–F21 — Seleção/cópia baseada em Cliente (tags/keywords/blacklist)  
- [ ] F22–F25 — Gestão de keywords e blacklist  
- [ ] F26–F30 — Editáveis (declarações/propostas) criação e existente  
- [ ] F32–F34 — Resumo e tela de revisão automática  
- [ ] F35–F38 — Handlers da UI (PySide6)

---

## 12) Changelog (documento)

- **v2.0 do Mapa** — Revisão completa para comercialização:  
  - Tag **whitelist configurável** e **blacklist fixa**  
  - Wizard com renomeio em massa (oficiais/blacklist)  
  - Keywords **editáveis** e persistentes  
  - Tela de Revisão **automática** com resumo  
  - Geração de **Editáveis** também em licitação **já existente**

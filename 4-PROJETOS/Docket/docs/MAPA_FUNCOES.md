# Mapa de Funções — Docket
> Índice técnico com IDs para referência rápida em discussões, issues e PRs.  
> Convencões de status: ✅ Ok · 🔧 Melhorar · 🆕 Planejado

---

## 0) Convenções gerais

- **Arquivos (sugestão de organização)**
  - `core/naming.py` — nomenclatura da licitação
  - `core/paths.py` — detecção de contexto e resolução de caminhos
  - `core/copyops.py` — cópias, conflitos e anexos
  - `core/map_client.py` — mapeamento de fontes do cliente e busca por keywords
  - `core/utils.py` — utilidades (normalização, logs helpers, contadores)
  - `settings.py` — salvar/carregar preferências (JSON)
  - `ui/` — camada PySide6 (a migrar)
- **Política de conflito:** `"duplicar" | "substituir" | "pular"`
- **Normalização:** remover numeração/pontos/acentos/hífens/underscores e minúsculas (tokenização).

---

## 1) Núcleo de nomenclatura e caminhos

**F01 — `montar_nome_licitacao(dia, mes_combo, id_lct, portal, gp, cidade_uf) -> str`**  
Gera o nome no padrão `DD-MM_ID-LCT_PORTAL[_GP]_Cidade-UF`.  
- `DD` = dia da disputa (01–31)  
- `MM` = mês numérico (do combo: `"03. MARCO"` → `"03"`)  
- `PORTAL` = sempre em maiúsculo (ex.: `BNC`, `LICITANET`)  
- `Cidade` = sempre iniciando em maiúscula e preposições minúsculas (`Lauro de Freitas`)  
- `UF` = sempre em maiúsculo (ex.: `-BA`, `-SP`)  
**Local:** `core/naming.py` · **Status:** 🔧 Melhorar (validar formato ID-LCT e dia)  
**Explicação simples:**  
Essa função monta o **nome da pasta da licitação** automaticamente, padronizando a escrita do dia, mês, portal e cidade, para que todos os nomes fiquem iguais e organizados.

**F02 — `resolver_pasta_mes_somente_existente(base_participar: Path, mes_combo: str) -> Optional[Path]`**  
Procura a pasta de **mês existente** em `1. Licitacao/1. Participar/`.  
- Normaliza variações (`2.FEVEREIRO` ↔ `2. FEVEREIRO`)  
- **Nunca cria** pasta nova: se não achar → retorna `None` e a UI deve avisar o usuário.  
**Local:** `core/paths.py` · **Status:** ✅ Ok  
**Explicação simples:**  
Essa função serve para **achar a pasta do mês já existente**. Se não encontrar, o sistema avisa que algo está errado em vez de criar uma nova pasta (evita bagunça).

**F03 — `caminho_participar() -> Path`**  
Retorna a pasta base de Participar (hoje: diretório do app).  
**Local:** `core/paths.py` · **Status:** 🔧 Melhorar (usar rede do cliente quando detectado)

**F04 — `caminho_licitacao_raiz() -> Path`**  
Sobe um nível (onde costuma existir `1. Licitacao`, `5. Modelos_Padrao`, etc.).  
**Local:** `core/paths.py` · **Status:** ✅ Ok

---

## 2) Detecção de contexto (cliente, modelos, template)

**F05 — `detectar_cliente(path_atual: Path) -> Optional[Path]`**  
Determina se estamos dentro de uma pasta de **cliente** (heurística: presença de `1. Licitacao` e `2. Empresa`).  
**Local:** `core/paths.py` · **Status:** 🆕 Planejado

**F06 — `detectar_participar_dir(cliente_dir: Path) -> Optional[Path]`**  
Encontra `1. Licitacao/1. Participar` dentro do cliente.  
**Local:** `core/paths.py` · **Status:** 🆕 Planejado

**F07 — `detectar_pasta_modelos() -> Optional[Path]`**  
Acha `4. Modelos_Padrao` ou `5. Modelos_Padrao` um nível acima.  
**Local:** `core/paths.py` · **Status:** ✅ Ok

**F08 — `detectar_pasta_template(modelos_dir: Path) -> Optional[Path]`**  
Acha subpasta `00_ID-LCT_…` dentro de Modelos (fallback: primeira subpasta).  
**Local:** `core/paths.py` · **Status:** ✅ Ok

---

## 3) Normalização / utilidades

**F09 — `_strip_accents(s: str) -> str`**  
Remove acentos via `unicodedata`.  
**Local:** `core/utils.py` · **Status:** ✅ Ok

**F10 — `_normalize_token(name: str) -> str`**  
Normaliza nomes (remove numeração inicial, pontos, underscores, hífens, espaços; minúsculas; sem acentos).  
**Local:** `core/utils.py` · **Status:** ✅ Ok

**F11 — `_listar_subdirs(p: Path) -> List[Path]`**  
Lista apenas diretórios ordenados.  
**Local:** `core/utils.py` · **Status:** ✅ Ok

**F12 — `_resolver_subpasta_flex(model_root: Path, rel_path: str) -> Optional[Path]`**  
Resolve subpasta por aproximação (exato → contém/contido), tolera singular/plural (ex.: `DECLARACAO/DECLARACOES`).  
**Local:** `core/utils.py` · **Status:** ✅ Ok  
**Uso:** cópia por TEMPLATE e busca por fontes do cliente.

---

## 4) Operações de cópia (TEMPLATE e CLIENTE)

**F13 — `_proximo_nome_livre(dir: Path, nome: str) -> Path`**  
Gera `arquivo_1.ext`, `arquivo_2.ext`… para evitar sobrescrita quando a política for `duplicar`.  
**Local:** `core/copyops.py` · **Status:** ✅ Ok  
**Explicação simples:**  
Quando já existe um arquivo com o mesmo nome, essa função cria uma versão nova numerada para não perder nada.

**F14 — `anexar_arquivos(arquivos: List[Path], raiz_destino: Path, subpasta_destino_rel: str, politica: str, log: LogFn) -> None`**  
Copia arquivos escolhidos pelo usuário para dentro da subpasta de destino, respeitando a política de conflito (`duplicar`, `substituir` ou `pular`).  
**Local:** `core/copyops.py` · **Status:** ✅ Ok  
**Explicação simples:**  
Permite anexar arquivos extras (como editais ou documentos específicos) direto para a pasta correta, sem substituir nada por engano.

**F15 — `anexar_arquivos(arquivos: List[Path], raiz_destino: Path, subpasta_destino_rel: str, politica: str, log: LogFn) -> None`**  
Copia anexos do usuário conforme política.  
**Local:** `core/copyops.py` · **Status:** ✅ Ok

**F16 — `copiar_padrao_cliente(cliente_dir: Path, destino: Path, subpastas: List[str], politica: str, log: LogFn) -> None`**  
Copia **documentos padrão do cliente** (ex.: CNPJ, Contrato Social, CAT…) mapeados por `PADROES_CLIENTE` (F17–F19).  
**Local:** `core/copyops.py` · **Status:** 🆕 Planejado

---

## 5) Mapeamento de fontes do cliente (documentos padrão)

**F17 — `PADROES_CLIENTE: Dict[str, List[Tuple[str, List[str]]]]`**  
Mapa: **subpasta de destino na licitação** → **fontes no cliente** + **keywords** para priorizar arquivos.  
**Local:** `core/map_client.py` · **Status:** 🆕 Planejado  
**Ex.:**
- `"1. HABILITACAO/1. HAB_JURIDICA"` →  
  `[("2. Empresa/01. CNPJ", ["CNPJ", "Cadastro Nacional"]), ("2. Empresa/05. Contrato_Social", ["Contrato Social","Consolidada"]), …]`

**F18 — `resolver_fontes_cliente(cliente_dir: Path, destino_rel: str) -> List[Path]`**  
Resolve pastas-fonte do cliente para uma **subpasta de destino** (usa `F12` em cada nível).  
**Local:** `core/map_client.py` · **Status:** 🆕 Planejado

**F19 — `selecionar_arquivos_por_keywords(pasta: Path, keywords: List[str]) -> List[Path]`**  
Seleciona arquivos preferindo os que batem keywords (case/acentos-insensitive). Se nada bater: retorna **todos** (com aviso).  
**Local:** `core/map_client.py` · **Status:** 🆕 Planejado

---

## 6) Preferências (salvar/carregar)

**F20 — `load_prefs() -> dict`**  
Carrega JSON com preferências (último modelo/template, política, subpastas marcadas, “abrir ao concluir”, etc.).  
**Local:** `settings.py` · **Status:** 🆕 Planejado

**F21 — `save_prefs(data: dict) -> None`**  
Salva JSON de preferências.  
**Local:** `settings.py` · **Status:** 🆕 Planejado

---

## 7) Logging e resumo

**F22 — `log(level: str, msg: str) -> None`**  
Interface para a UI registrar `[OK]/[WARN]/[ERROR]` com timestamp.  
**Local:** `core/utils.py` (ou adaptado pela UI) · **Status:** ✅ Ok (já existe análogo)

**F23 — `ResumoExecucao` (dataclass)**  
Contadores: diretórios criados, arquivos copiados/duplicados/substituídos, anexos, avisos, erros.  
**Local:** `core/utils.py` · **Status:** 🆕 Planejado

**F24 — `finalizar_resumo(resumo: ResumoExecucao) -> str`**  
Gera linha final:  
“Criados X dirs; copiados Y (D duplicados, S substituídos); anexados Z; avisos A; erros E.”  
**Local:** `core/utils.py` · **Status:** 🆕 Planejado

---

## 8) Integração com a UI (handlers/slots)

**F25 — `on_criar_licitacao(inputs_ui: Inputs) -> None`**  
Orquestra o fluxo: resolver mês → criar raiz → criar subpastas → copiar padrão **cliente** (opcional: template) → anexos → resumo → abrir pasta (se marcado).  
**Local:** `ui/main_window.py` (PySide6) · **Status:** 🆕 Planejado  
**Observação:** usa apenas funções do `core/`.

**F26 — `on_detectar_template()`**  
Reexecuta `F07` e `F08` e preenche a UI (com log/toast).  
**Local:** `ui/sections.py` · **Status:** ✅ Ok (já existe análogo)

**F27 — `on_add_anexos(paths)` / `on_clear_anexos()`**  
Gerencia lista de anexos (arrastar & soltar + diálogo).  
**Local:** `ui/sections.py` · **Status:** 🆕 Planejado

**F28 — `on_toggle_subpastas(preset: Literal["tudo","nada","padrao"])`**  
Marca/Desmarca/Volta ao preset.  
**Local:** `ui/sections.py` · **Status:** 🆕 Planejado

**F29 — `on_export_log(path)`**  
Salva console/log em `.txt`.  
**Local:** `ui/console.py` · **Status:** 🆕 Planejado

**F30 — `on_copy_preview_to_clipboard()`**  
Copia a “Prévia do nome” ao clique.  
**Local:** `ui/sections.py` · **Status:** 🆕 Planejado

---

## 9) Regras funcionais (resumo)

- **Fonte padrão**: documentos **do cliente** (se detectado).  
- **Template**: opcional, pode **sobrepor** ou **complementar**.  
- **Subpastas**: grupos (Habilitação / Proposta / Editáveis), presets “tudo/nada/padrão”.  
- **Conflitos**: `duplicar | substituir | pular`.  
- **Nomes**: normalização robusta (tokens).  
- **Erros/Avisos**: console com nível e contadores; resumo final.  
- **Preferências**: lembrar últimos caminhos e opções de uso.

---

## 10) Pendências rastreáveis

- [ ] F05/F06 — Detecção de cliente e Participar (contexto de rede)  
- [ ] F16–F19 — Padrões do cliente (mapeamento + seleção por keywords)  
- [ ] F20/F21 — Preferências (JSON)  
- [ ] F23/F24 — Resumo de execução (contadores)  
- [ ] F25–F30 — Slots da UI Qt (PySide6)

---

## 11) Changelog (documento)

- **v1.0 do Mapa** — Criação do índice inicial com 30 funções (IDs F01–F30), consolidando lógica atual e melhorias planejadas.

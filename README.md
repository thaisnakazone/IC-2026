# IC 2026 — Sobrevivência de empresas empregadoras: Brasil e OCDE

> 📊 **Acesse o dashboard:** [thaisnakazone.github.io/IC-2026](https://thaisnakazone.github.io/IC-2026/)

Repositório de dados, código e dashboard da iniciação científica **“Complexidade tributária e sobrevivência de empresas empregadoras: o Brasil em perspectiva comparada com países da OCDE utilizando ciência de dados”**, desenvolvida no Programa de Iniciação Científica 2026 da Fatec Sebrae. O estudo relaciona fatores do ambiente de negócios, com ênfase nos tributários, à sobrevivência das empresas empregadoras no Brasil e em países da OCDE.

## Equipe

- **Paulo Futagawa** — [@pfutagawa](https://github.com/pfutagawa)
- **Thaís Nakazone** — [@thaisnakazone](https://github.com/thaisnakazone)

**Orientadora:** Profa. Nathane de Castro<br>
**Curso:** Ciência de Dados para Negócios — Fatec Sebrae

## Pergunta de pesquisa

Quais fatores macroeconômicos, institucionais, financeiros, tecnológicos e tributários estão associados à sobrevivência em três anos das empresas empregadoras no Brasil e em países da Organização para a Cooperação e Desenvolvimento Econômico (OCDE)?

## O que o estudo faz

- **Desfecho:** taxa de sobrevivência das empresas empregadoras em 3 anos (e em 2 anos, no recorte de fonte única). OCDE para os países-membros; IBGE para o Brasil em 3 anos.
- **Fatores:** 22 indicadores macroeconômicos, financeiros, institucionais, tecnológicos e tributários, medidos antes do nascimento das coortes. A taxa real de juros não tem cobertura suficiente, de modo que 21 são testados.
- **Recortes:**
  - A1: coorte de 2017, 3 anos, com o Brasil pelo IBGE;
  - B: coorte de 2017, 2 anos, todos pela OCDE, com o Brasil;
  - A2: coortes de 2014 a 2016, antes da pandemia, sem o Brasil;
  - índices ajustados por setor e por porte, sem o Brasil;
  - painel país × coorte, com 176 observações de 30 países, sem o Brasil.
- **Resultado:** nenhuma associação robusta. Dos 126 testes, 3 têm p < 0,05 e nenhum resiste à correção de Benjamini–Hochberg. A posição do Brasil em relação à mediana da OCDE muda conforme a fonte (IBGE ou OCDE).

## O que o dashboard mostra

| Aba | Conteúdo |
|---|---|
| Comparação | Taxas de sobrevivência por país em cada recorte, com a posição do Brasil |
| Fatores | Relação de cada fator com a sobrevivência, a consistência do sinal entre recortes e o aviso sobre o conjunto de testes |
| Painel | Coeficientes das regressões com efeitos fixos de coorte (intervalo de confiança de 95%) |
| Brasil: IBGE × OCDE | Comparação das duas fontes para a coorte brasileira de 2017 |
| Método e cobertura | Fontes, definições, critérios, cobertura dos dados e limitações |

O dashboard existe em duas formas:

- `dashboard/index.html` com `dashboard/assets/`: versão para hospedagem (GitHub Pages).
- `dashboard/sobrevivencia_dashboard.html`: a mesma versão em arquivo único; abre com dois cliques, sem servidor.

O dashboard é estático (HTML, CSS e JavaScript), e o tema claro ou escuro acompanha o sistema. A única dependência externa é a fonte tipográfica (Google Fonts); sem internet, o navegador usa uma fonte do sistema.

## Dados

Os dados da OCDE e do Banco Mundial foram obtidos em 7 de outubro de 2026, de forma automatizada, nas APIs oficiais:

- **OCDE (SDMX):**
  - demografia de empresas empregadoras, com sobrevivência de 1 a 3 anos por país, ano, setor e porte (`DF_BD_EMP_S`);
  - estatísticas de receita tributária (`DF_RSGLOBAL`);
  - alíquotas do imposto de renda das empresas (`DF_CIT`).
- **Banco Mundial (API v2):** World Development Indicators, Worldwide Governance Indicators e Doing Business.

A sobrevivência brasileira em 3 anos, que a OCDE não publica, vem do **IBGE**: Demografia das Empresas e Estatísticas de Empreendedorismo 2022 (Tabela 2.1). Esses valores **não** vieram de API: foram transcritos da tabela publicada e estão em `data/raw/survival/ibge_employer_survival_brazil.csv`.

Os 22 fatores se dividem em cinco dimensões:

| Dimensão | Fatores |
|---|---|
| Macroeconômica | crescimento do PIB, inflação, PIB per capita, desemprego |
| Financeira | crédito ao setor privado, taxa real de juros, recuperação na insolvência |
| Institucional | qualidade regulatória, Estado de direito, efetividade do governo, tempo para abrir empresa |
| Tecnológica | usuários de internet, gasto em P&D |
| Tributária | carga total, composição da receita, receita e alíquota do IRPJ, carga sobre o lucro, horas e número de pagamentos para cumprir obrigações |

O dicionário completo está em `config/survival_v2_data_dictionary.csv`.

## Método, em resumo

- correlações de Pearson e Spearman em cada recorte;
- correção de Benjamini–Hochberg para múltiplos testes;
- sensibilidade com a exclusão de um país por vez;
- regressões com efeitos fixos de coorte e erros-padrão agrupados por país.

## Limitações

- Os indicadores do Doing Business referem-se a uma empresa hipotética padronizada, de porte médio, e a publicação foi descontinuada pelo Banco Mundial em 2021.
- Os recortes compartilham países e dados; não são confirmações independentes.
- O painel tem apenas efeitos fixos de coorte; compara países, como as correlações.
- Os resultados são associações observacionais entre países, não efeitos causais.

## Como reproduzir

Requer Python 3.10 ou superior.

```bash
python -m venv .venv
.venv\Scripts\activate                 # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt

python src/fetch_api_data.py           # OCDE SDMX + Banco Mundial → data/raw/api/
python src/build_survival_v2.py        # bases analíticas, correlações, painel e relatório
python src/build_dashboard_v2.py       # dashboard/assets/data.js e o arquivo único
python -m unittest tests/test_survival_v2.py -v
```

Para ver o dashboard localmente:

```bash
python -m http.server 8000
# abrir http://localhost:8000/dashboard/
```

As APIs não exigem chave. `fetch_api_data.py` baixa os dados de novo a cada execução; revisões feitas pelas instituições podem alterar os resultados. Os arquivos em `data/raw/api/` preservam a coleta de 07/10/2026, usada no relatório. Ao coletar de novo, atualize `DATA_COLLECTED` em `src/build_dashboard_v2.py`. Para reproduzir os números do relatório sem nova coleta, pule o primeiro script.

## Estrutura do repositório

```text
index.html                   redireciona para o dashboard
dashboard/                   site estático (index.html + assets/) e versão em arquivo único
src/fetch_api_data.py        coleta nas APIs oficiais
src/build_survival_v2.py     harmonização, recortes, correlações e modelos de painel
src/build_dashboard_v2.py    dados do dashboard e edição em arquivo único
tests/test_survival_v2.py    testes de integridade
data/raw/api/                respostas das APIs (sobrevivência, tributos, indicadores)
data/raw/survival/           sobrevivência do Brasil segundo o IBGE
data/processed/survival_v2/  fatos harmonizados, recortes analíticos e painel
analysis/survival_v2/        correlações por recorte, modelos, síntese e validação
config/                      dicionários de dados e fontes
docs/                        arquitetura do dashboard
```

## Fontes

- OCDE — Employer business demography, Global Revenue Statistics e Corporate Tax Statistics (SDMX): https://sdmx.oecd.org/public/rest/data/
- Banco Mundial — API v2 (WDI, WGI, Doing Business): https://api.worldbank.org/v2/
- IBGE — Demografia das Empresas e Estatísticas de Empreendedorismo 2022: https://www.ibge.gov.br/estatisticas/economicas/comercio/22649-demografia-das-empresas-e-estatisticas-de-empreendedorismo.html

## Histórico

Versões anteriores do projeto ficam no repositório apenas como registro e não são usadas no relatório final:

- **Piloto de sobrevivência** (`src/build_survival_pilot.py`, `tests/test_survival_pilot.py`, `data/*/survival/`, `analysis/survival/`, `dashboard/sobrevivencia_dashboard_piloto.html`, `MANIFESTO_PILOTO.md`): usava a tabela transcrita de um relatório da OCDE e escores de 2020–2023, posteriores às coortes.
- **Primeiro ciclo** (painel país-ano de dez países, 2013–2024, com densidade de novos negócios como desfecho): restou apenas `data/processed/painel_principal_2013_2024.csv`; os scripts desse ciclo não fazem parte deste pacote.

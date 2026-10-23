# IC 2026 — Sobrevivência de empresas empregadoras: Brasil × OCDE

> 📊 **Acesse o dashboard:** [thaisnakazone.github.io/IC-2026](https://thaisnakazone.github.io/IC-2026/)

Repositório de dados, código e dashboard da iniciação científica **“Complexidade tributária e sobrevivência de empresas empregadoras: o Brasil em perspectiva comparada com países da OCDE utilizando ciência de dados”**, desenvolvida no Programa de Iniciação Científica 2026 da Fatec Sebrae.

## Equipe

- **Paulo Futagawa** — [@pfutagawa](https://github.com/pfutagawa)
- **Thaís Nakazone** — [@thaisnakazone](https://github.com/thaisnakazone)

**Orientadora:** Profa. Nathane de Castro<br>
**Curso:** Ciência de Dados para Negócios — Fatec Sebrae

## Pergunta de pesquisa

Quais fatores macroeconômicos, institucionais, financeiros, tecnológicos e tributários estão associados à sobrevivência em três anos das empresas empregadoras no Brasil e em países da Organização para a Cooperação e Desenvolvimento Econômico (OCDE)?

## O que o dashboard mostra

| Aba | Conteúdo |
|---|---|
| Comparação | Taxas de sobrevivência por país em cinco recortes, com a posição do Brasil |
| Fatores | Relação de cada um dos 22 fatores com a sobrevivência e a consistência do sinal entre recortes |
| Painel | Coeficientes das regressões com efeitos fixos (intervalo de confiança de 95%) |
| Brasil: IBGE × OCDE | Comparação das duas fontes para a coorte brasileira de 2017 |
| Método e cobertura | Fontes, definições, critérios e cobertura dos dados |

O dashboard é uma página estática (HTML, CSS e JavaScript) e não precisa de servidor. O tema claro ou escuro acompanha o sistema.

## Dados

Os dados foram obtidos em 7 de outubro de 2026, de forma automatizada, nas APIs oficiais:

- **OCDE (SDMX):**
  - demografia de empresas empregadoras, com sobrevivência de 1 a 3 anos por país, ano, setor e porte (`DF_BD_EMP_S`);
  - estatísticas de receita tributária (`DF_RSGLOBAL`);
  - alíquotas do imposto de renda das empresas (`DF_CIT`).
- **Banco Mundial (API v2):** World Development Indicators, Worldwide Governance Indicators e Doing Business.
- **IBGE:** Demografia das Empresas e Estatísticas de Empreendedorismo 2022 (Tabela 2.1). É a fonte da sobrevivência brasileira em 3 anos, que a OCDE não publica.

Os 22 fatores se dividem em cinco dimensões e são sempre medidos **antes** do nascimento das coortes:

| Dimensão | Fatores |
|---|---|
| Macroeconômica | crescimento do PIB, inflação, PIB per capita, desemprego |
| Financeira | crédito ao setor privado, taxa real de juros, recuperação na insolvência |
| Institucional | qualidade regulatória, Estado de direito, efetividade do governo, tempo para abrir empresa |
| Tecnológica | usuários de internet, gasto em P&D |
| Tributária | carga total, composição da receita, receita e alíquota do IRPJ, carga sobre o lucro, horas e número de pagamentos para cumprir obrigações |

O dicionário completo está em `config/survival_v2_data_dictionary.csv`.

## Método, em resumo

- **Recortes:**
  - A1: coorte de 2017, sobrevivência em 3 anos, Brasil pelo IBGE;
  - A2: coortes de 2014 a 2016, antes da pandemia;
  - B: sobrevivência em 2 anos, todos os países pela OCDE;
  - índices ajustados por setor e por porte;
  - painel país × coorte com 176 observações de 30 países.
- **Estatística:**
  - correlações de Pearson e Spearman;
  - correção de Benjamini-Hochberg para múltiplos testes;
  - sensibilidade com a exclusão de um país por vez;
  - regressões com efeitos fixos de coorte e erros-padrão agrupados por país.
- **Interpretação:** os resultados são **associações observacionais entre países**, não efeitos causais.

## Como reproduzir

Requer Python 3.10 ou superior.

```bash
python -m venv .venv
.venv\Scripts\activate            # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt

python src/fetch_api_data.py      # 1. baixa os dados das APIs para data/raw/api/
python src/build_survival_v2.py   # 2. monta as bases, correlações, painel e relatório
python src/build_dashboard_v2.py  # 3. gera os dados do dashboard
python -m unittest tests/test_survival_v2.py -v   # 4. testes de integridade
```

Para ver o dashboard localmente:

```bash
python -m http.server 8000
# abrir http://localhost:8000/dashboard/
```

As APIs não exigem chave. Como as instituições revisam os dados periodicamente, uma nova extração pode trazer valores um pouco diferentes; `data/raw/api/` guarda a versão usada na pesquisa.

## Estrutura do repositório

```text
index.html             redireciona para o dashboard
dashboard/             dashboard publicado (index.html + assets/)
src/                   scripts de coleta, processamento e geração do dashboard
data/raw/              dados brutos das APIs e do IBGE
data/processed/        bases harmonizadas e recortes analíticos
analysis/survival_v2/  correlações, modelos, síntese da evidência e relatório técnico
config/                dicionários de dados e fontes
docs/                  arquitetura do dashboard
tests/                 testes automatizados
```

A pasta `src/` também guarda o script do piloto de agosto de 2026 (`build_survival_pilot.py`), mantido como registro histórico.

## Fontes

- OCDE — SDMX API: https://sdmx.oecd.org/public/rest/data/
- Banco Mundial — Indicators API v2: https://api.worldbank.org/v2/
- IBGE — Demografia das Empresas e Estatísticas de Empreendedorismo: https://www.ibge.gov.br/estatisticas/economicas/comercio/22649-demografia-das-empresas-e-estatisticas-de-empreendedorismo.html

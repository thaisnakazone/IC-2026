# IC 2026 — painel de tributação, ambiente empresarial e PMEs

Segundo ciclo técnico da iniciação científica **“Análise comparativa da
complexidade tributária e seus impactos na competitividade de pequenas e médias
empresas”**.

## Escopo desta versão

- Países: Brasil, México, Colômbia, Costa Rica, Portugal, Espanha, Reino Unido,
  Canadá, Estônia e Coreia do Sul.
- Período do painel principal: 2013–2024.
- Recorte histórico de complexidade tributária: 2013–2019.
- Unidade de observação: país-ano.
- Fontes: OECD SDMX API e World Bank API v2.
- Saídas: dados brutos normalizados, painel principal contemporâneo, recorte
  histórico, cobertura, validação automática, análise exploratória, modelagem
  de painel, gráficos e dicionários de dados em Excel.

## Estrutura

```text
config/              seleção de países, período e códigos dos indicadores
src/build_panel.py   extração, transformação, integração e validação
src/analyze_panel.py análise exploratória, tabelas e visualizações
src/model_panel.py   efeitos fixos, inferência e testes de sensibilidade
data/raw/            respostas normalizadas das APIs
data/processed/      painel e diagnósticos de qualidade
analysis/            relatório exploratório, tabelas e figuras
modeling/            resultados, diagnósticos e figuras dos modelos
docs/                notas metodológicas
outputs/             dicionário e painel em Excel
```

## Como reproduzir

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python src/build_panel.py
python src/analyze_panel.py
python src/model_panel.py
```

As APIs não exigem chave de autenticação. Os dados são obtidos novamente a cada
execução, por isso pequenas revisões feitas pelas instituições podem alterar os
resultados futuros. Os arquivos em `data/raw` preservam a versão obtida nesta
execução.

## Decisões metodológicas

1. O painel principal 2013–2024 utiliza carga e composição tributária, dinamismo
   empresarial e controles macroeconômicos. O Doing Business é mantido apenas
   no recorte histórico 2013–2019, consultado explicitamente com `source=1`.
2. A composição tributária é mantida nas seis categorias de primeiro nível da
   OCDE. “Tributos diretos”, “sobre trabalho” e “indiretos” são agrupamentos
   derivados, não categorias originais completas.
3. A densidade de novos negócios é uma aproximação do dinamismo empresarial e
   **não** equivale à taxa de sobrevivência de PMEs.
4. O painel permite investigar associações. Regressão observacional e
   clustering não demonstram causalidade.
5. Os anos de 2020 e 2021 são identificados como período excepcional; análises
   futuras devem usar efeitos de ano e testes de sensibilidade sem esses anos.
6. O B-READY fica fora do núcleo porque ainda não havia valor brasileiro
   utilizável na API nesta execução e sua metodologia não é continuação direta
   do Doing Business.
7. A modelagem principal usa o logaritmo da densidade de novos negócios,
   variáveis tributárias defasadas em um ano e efeitos fixos de país e ano. A
   inferência combina erros-padrão agrupados por país e wild cluster bootstrap.
8. Como há apenas dez países, a estabilidade entre especificações e o teste de
   exclusão de um país por vez têm prioridade sobre um valor-p isolado.

## Modelagem exploratória

O modelo M3 é a especificação-base: carga tributária, participação dos tributos
diretos e participação dos tributos sobre o trabalho, todas defasadas em um ano,
com controles macroeconômicos e efeitos fixos. M4–M9 alteram período, desfecho,
países e dinâmica para avaliar robustez. H1–H5 usam exclusivamente o recorte
histórico do Doing Business.

Os resultados completos estão em `modeling/relatorio_modelagem.md` e em
`outputs/a6848e8d6df4/IC_2026_resultados_modelagem.xlsx`. As estimativas devem ser
descritas como associações condicionais e exploratórias, não como impactos
causais sobre PMEs.

## Principais fontes

- OECD SDMX API — Global Revenue Statistics:
  https://sdmx.oecd.org/public/rest/v1/data/
- World Bank API v2:
  https://api.worldbank.org/v2/
- Business Ready:
  https://www.worldbank.org/en/businessready

## Piloto de sobrevivência empresarial

O projeto agora contém um produto mínimo de dashboard para o possível novo foco
da pesquisa. O corte principal compara a sobrevivência em três anos das empresas
empregadoras nascidas em 2017, observada em 2020, no Brasil e em 25 países da
OCDE. A taxa brasileira vem da Demografia das Empresas do IBGE; as taxas dos
demais países vêm da tabela oficial do *OECD Entrepreneurial Ecosystem
Diagnostics 2025*.

Para reconstruir a base e abrir o dashboard:

```bash
python src/build_survival_pilot.py
python -m http.server 8000
# abrir http://localhost:8000/dashboard/
```

O dashboard é estático e não depende de servidor de aplicação. Pode ser
publicado no GitHub Pages, Cloudflare Pages ou serviço equivalente. Os detalhes
do esquema de dados, critérios de comparabilidade e roteiro de expansão estão
em `docs/arquitetura_dashboard_sobrevivencia.md`.

## Etapa 2 — dados das APIs e fatores anteriores às coortes (outubro/2026)

Substitui a tabela transcrita do relatório da OCDE e os escores de 2020–2023 por
dados extraídos diretamente das APIs, com fatores explicativos anteriores às coortes.

```bash
pip install -r requirements.txt
python src/fetch_api_data.py                # OCDE SDMX + Banco Mundial → data/raw/api/
python src/build_survival_v2.py             # bases, correlações, painel e relatório
python -m unittest tests/test_survival_v2.py -v
```

- `data/raw/api/`: respostas das APIs (sobrevivência OCDE, receita tributária e IRPJ OCDE,
  22 indicadores do Banco Mundial/WGI/Doing Business).
- `data/processed/survival_v2/`: fatos harmonizados, cinco cortes analíticos e painel país × coorte.
- `analysis/survival_v2/`: correlações por desenho, modelos de painel, síntese de evidência,
  divergência IBGE × OCDE e `relatorio_etapa2.md`.
- `config/survival_v2_data_dictionary.csv`: dicionário dos fatores.

### Dashboard (etapa 2)

```bash
python src/build_dashboard_v2.py            # gera dashboard/assets/data.js e o arquivo único
```

- `dashboard/sobrevivencia_dashboard.html`: edição em arquivo único; abre direto no navegador.
- `dashboard/index.html` + `dashboard/assets/`: versão para hospedar (GitHub Pages etc.).
- Abas: comparação (5 recortes), fatores (dispersão + consistência entre recortes), painel
  (coeficientes com IC 95%), Brasil IBGE × OCDE e método & cobertura. Tema claro e escuro automáticos.
- `dashboard/sobrevivencia_dashboard_piloto.html` fica como registro histórico do piloto de agosto.

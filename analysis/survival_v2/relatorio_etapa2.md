# Etapa 2 — dados das APIs, fatores anteriores às coortes e robustez

*Gerado a partir de `src/build_survival_v2.py`. Dados extraídos em 07/10/2026.*

## O que mudou em relação ao piloto

| | Piloto (agosto) | Etapa 2 |
|---|---|---|
| Sobrevivência dos países da OCDE | Transcrita de uma tabela de relatório (um ano por país) | API da OCDE (`DF_BD_EMP_S`): 1 a 3 anos de idade, anos de referência 2008–2024, setor e porte |
| Fatores explicativos | 10 escores compostos de 2020–2023 (posteriores à coorte) | 22 indicadores oficiais de 2011–2016 (anteriores à coorte) |
| Brasil nos fatores | Ausente (sem escores da OCDE) | Presente em todos os 22 indicadores |
| Desenhos analíticos | 1 corte transversal | 5 cortes + painel país × coorte |
| Tributação | Fora das correlações | 9 indicadores de carga, composição e complexidade |

As 63.096 observações de sobrevivência, os 8.536 valores do Banco Mundial e os 2.808 valores tributários da OCDE foram conferidos por soma de controle entre a extração e a base gravada.

## Fatores (22, em cinco dimensões)

- **Macroeconômicos:** crescimento do PIB, inflação, PIB per capita (log) e desemprego.
- **Financeiros:** crédito privado (% PIB), taxa real de juros e recuperação na insolvência.
- **Institucionais:** qualidade regulatória, Estado de direito, efetividade do governo e tempo para abrir empresa.
- **Tecnológicos:** usuários de internet e gasto em P&D.
- **Tributários:**
  - carga total (% PIB);
  - composição da receita (renda, contribuições sociais, bens e serviços);
  - receita e alíquota do IRPJ;
  - carga total sobre o lucro;
  - horas para cumprir obrigações;
  - número de pagamentos.

A taxa real de juros fica fora das correlações porque tem menos de 15 países com dado.

## Posição do Brasil depende da fonte

| Desenho | Brasil | Mediana OCDE | Posição |
|---|---|---|---|
| A1 — 3 anos, coorte 2017 (Brasil pelo IBGE) | 49,4% | 54,6% | 18ª de 25 |
| B — 2 anos, coorte 2017 (todos pela OCDE) | 69,2% | 67,0% | 12ª de 27 |

**Achado metodológico importante.** Para a mesma coorte de 2017, a sobrevivência do Brasil em 1 ano coincide entre IBGE (76,2%) e OCDE (75,7%). Em 2 anos, porém, o IBGE informa 59,6% e a OCDE informa 69,2%: uma diferença de 9,6 p.p. A OCDE não publica a sobrevivência em 3 anos para o Brasil. Por isso, o 49,4% usado no ranking de 3 anos provavelmente segue um critério mais rigoroso que o aplicado aos demais países. O IBGE considera morta a empresa que encerra a atividade ou fica sem empregados por 24 meses. A conclusão "o Brasil está abaixo da mediana da OCDE" **não é robusta à troca de fonte** e precisa ser apresentada com essa ressalva. O próximo passo é verificar a definição usada no envio do IBGE para a OCDE.

## Correlações e modelos

Desenhos:
- **A1:** coorte 2017, com fatores de 2014–2016.
- **A2:** coortes 2014–2016 antes da pandemia, com fatores de 2011–2013.
- **B:** 2 anos, todos os países pela OCDE.
- **S:** índices ajustados por composição setorial e por porte.
- **Painel:** 176 observações país × coorte de 30 países, com fator igual à média dos 3 anos anteriores ao nascimento da coorte, efeitos fixos de coorte e erros agrupados por país.

**Nenhum fator atinge o critério de evidência robusta.** O critério exige mesmo sinal em todos os desenhos, p < 0,05 em pelo menos três deles e q-BH < 0,10 no painel ou em A1. Nenhum fator sobrevive à correção por múltiplos testes em nenhum desenho.

Padrões que merecem atenção (todos com o mesmo sinal nos seis desenhos):

| Fator | A1 r | A2 r | Painel (p.p. por DP) | Leitura |
|---|---|---|---|---|
| Horas para cumprir obrigações tributárias (log) | −0,21 | −0,38 (p = 0,04) | −3,5 (p = 0,03) | **Sugestiva**: mais horas de conformidade, menor sobrevivência |
| Qualidade regulatória | +0,25 | +0,39 (p = 0,04) | +3,0 (p = 0,15) | Mesmo sinal, sem significância |
| PIB per capita (log) | +0,28 | +0,37 (p = 0,05) | +2,7 (p = 0,09) | Mesmo sinal, sem significância |
| Tributos sobre bens e serviços (% da receita) | −0,29 | −0,26 | −2,3 (p = 0,14) | Mesmo sinal, sem significância |
| Inflação | −0,10 | −0,17 | −2,5 (p = 0,07) | Mesmo sinal, sem significância |

A carga tributária total (% PIB), a alíquota do IRPJ e o crédito privado **não** mostram associação consistente.

No modelo multivariado do painel (7 fatores, um por dimensão, 172 observações), a inflação (−2,6 p.p. por DP; p = 0,04) e as horas de conformidade (−3,8; p = 0,10) mantêm o sinal. O coeficiente negativo de usuários de internet reflete colinearidade com a qualidade regulatória (VIF de 3,3 e 4,0, respectivamente) e não deve ser interpretado.

As estimativas *within* (efeitos fixos de país) são instáveis: há poucas coortes por país e indicadores com tendência, como o PIB per capita, geram coeficientes implausíveis. Elas ficam registradas apenas como diagnóstico.

## Leitura para o relatório

1. A pergunta de pesquisa continua respondível, mas a resposta honesta neste momento é que **as associações entre fatores do ambiente e sobrevivência em três anos são fracas e pouco estáveis entre os países da OCDE**.
2. Na dimensão tributária, quem aparece é a **complexidade de conformidade** (horas), e não a carga. Isso dialoga diretamente com a pergunta original sobre complexidade tributária.
3. A comparação do Brasil exige ressalva metodológica explícita (IBGE × OCDE).

## Limitações

- O número de países é de 25 a 29 por corte, o que dá pouco poder estatístico para correlações moderadas.
- A série da OCDE tem quebras visíveis: valores 0 ou acima de 100 (523 observações descartadas) e quedas abruptas em 2020, como Hungria (19,7%) e Dinamarca (22,9%). O desenho A2 e o painel atenuam esse problema.
- Os indicadores do Doing Business se referem ao ano de coleta do relatório e foram descontinuados em 2021.
- Três países do piloto (Finlândia, Grécia e Islândia) não têm valor de 2020 na API, enquanto Israel e Coreia passam a ter. Nova Zelândia muda de 51,0% para 52,7% (revisão da série).
- Todas as estimativas são associações observacionais e não efeitos causais.

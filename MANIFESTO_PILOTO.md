# Conteúdo do pacote do piloto

- `dashboard/`: site estático pronto para hospedagem pública.
- `dashboard/sobrevivencia_dashboard_piloto.html`: edição em arquivo único, pronta para abrir.
- `src/build_survival_pilot.py`: harmonização, análise e geração dos dados do dashboard.
- `data/raw/survival/`: transcrição rastreável das tabelas oficiais do IBGE e da OCDE.
- `data/processed/survival/`: fatos harmonizados, corte comparável e matriz de cobertura.
- `analysis/survival/`: correlações, validação e relatório curto.
- `config/survival_sources.json`: URLs, conceitos e alertas metodológicos.
- `config/survival_data_dictionary.csv`: dicionário das variáveis centrais.
- `docs/arquitetura_dashboard_sobrevivencia.md`: arquitetura analítica e roteiro de expansão.
- `tests/test_survival_pilot.py`: cinco testes automatizados de integridade.

Execução:

```bash
python src/build_survival_pilot.py
python -m unittest tests/test_survival_pilot.py -v
python -m http.server 8000
```

Abrir `http://localhost:8000/dashboard/`.

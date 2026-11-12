# JobMatch AI 0.5 — novas fontes de vagas

## O que mudou
- Greenhouse e Lever continuam ativos.
- Ashby: consulta organizações configuradas em `ASHBY_BOARDS`.
- SmartRecruiters: consulta empresas configuradas em `SMARTRECRUITERS_COMPANIES`.
- Adzuna: busca opcional de vagas em Curitiba mediante credenciais.
- Filtro de títulos aceita mais expressões de início de carreira e municípios da região de Curitiba.
- Mantém score mínimo de 50%, análise de habilidades e status de candidatura.
- Não realiza candidaturas e não exige senhas de portais de emprego.

## Instalação
1. Faça backup da versão atual.
2. Copie os arquivos da versão 0.5 sobre o projeto existente, sem apagar `.git`.
3. No GitHub, vá em Settings > Secrets and variables > Actions > Variables.
4. Configure as variáveis como listas JSON, por exemplo `ASHBY_BOARDS=["empresa-confirmada"]` e `SMARTRECRUITERS_COMPANIES=["empresa-confirmada"]`. Use slugs reais verificados nas páginas de carreiras; não use os exemplos literalmente.
5. Para Adzuna, adicione `ADZUNA_APP_ID` e `ADZUNA_APP_KEY` em Actions > Secrets. Sem elas, a fonte é ignorada.
6. Execute `python3 -m py_compile backend/collector.py` e, dentro de `backend`, `python3 -m unittest discover -s tests -p 'test_collector_v05.py'`.
7. Faça commit e push, depois execute o workflow `Daily job collector` manualmente.
8. Confira os logs e as vagas no painel.

## Limitações e cuidados
- Não há integração com todos os portais de emprego. LinkedIn, Indeed, Gupy e CIEE não são coletados por scraping nesta versão.
- A compatibilidade é heurística; não é probabilidade de contratação.
- Sem organizações configuradas nas novas variáveis, elas não coletarão vagas.
- As APIs podem alterar seus formatos ou impor limites; valide com fontes reais antes de uso contínuo.
- A Adzuna busca em Curitiba, não é garantia de vagas remotas em todo o Brasil.
- Nenhuma migração SQL adicional é necessária além da v0.4.

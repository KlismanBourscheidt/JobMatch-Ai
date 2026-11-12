# JobMatch AI 0.4 — Instalação

Este pacote foi adaptado do **JobMatch_AI_GitHub_Starter.zip** e do `collector_jobmatch_v03.py` fornecidos anteriormente. O repositório remoto pode ter alterações posteriores: compare os arquivos antes de substituir, principalmente `frontend/src/main.jsx` e `backend/app/main.py`.

1. No Supabase SQL Editor, execute **database/migration_v04.sql**. Não execute novamente o schema inicial nem apague a tabela.
2. No GitHub, atualize **backend/collector.py**, **backend/app/main.py**, **frontend/src/main.jsx** e **frontend/src/style.css**. O pacote contém todos esses arquivos completos.
3. Mantenha os secrets existentes e as variáveis `GREENHOUSE_BOARDS` e `LEVER_BOARDS`. O workflow existente continua executando `python collector.py` na pasta `backend`.
4. Confirme que o Render fez deploy da API e que GitHub Pages publicou o frontend.
5. Execute o workflow manualmente e confira logs. Vagas existentes são preservadas; o status de candidatura não é atualizado pelo coletor.
6. No painel, clique em **Detalhes** de uma vaga para ver habilidades identificadas, não comprovadas e sugestões de estudo.

## Como funciona o score

- Filtro de entrada: título precisa indicar função de TI e nível de entrada; títulos seniores são rejeitados.
- Localização: Curitiba ou remoto explicitamente elegível para o Brasil.
- Score: 30 pontos pelo cargo + 20 pela localização + até 50 pela proporção de tecnologias mencionadas que constam no perfil.
- Mínimo exibido: 50%; destaque: 80% ou mais.
- **Limitação:** o algoritmo detecta tecnologias mencionadas, mas não distingue perfeitamente exigências obrigatórias, desejáveis ou texto institucional. Sem tecnologias detectadas, uma vaga válida recebe 50 pontos. Não é probabilidade de contratação.
- Perfil estático em `PROFILE` no `backend/collector.py`. Atualize apenas com habilidades comprovadas. Para uma versão futura, mover perfil para tabela separada.

## Segurança

A service role do Supabase fica somente no backend/Actions, nunca no frontend. O acesso a `/jobs` continua exigindo JWT Supabase e e-mail autorizado. A migração mantém RLS e não cria políticas públicas. O coletor não se candidata automaticamente.

## Teste rápido

`python -m py_compile backend/collector.py backend/app/main.py`

Para executar a coleta são necessários secrets e conexão de rede. Faça o deploy da migração SQL **antes** de executar o coletor atualizado.

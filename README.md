# JobMatch AI — sistema pessoal (React + FastAPI + Supabase)

MVP para publicar via **GitHub Pages (React)**, **Render (FastAPI)** e **Supabase (PostgreSQL + Auth)**.

**Importante:** nenhum deploy, conta, agendamento ou envio de currículo foi ativado. O coletor só lê vagas de boards Greenhouse cadastrados. Score ≥80 é um **ranking heurístico** e não a probabilidade de contratação. A pontuação é experimental e precisa de calibração. Não há candidaturas automáticas.

## 1. Supabase
1. Crie um projeto em https://supabase.com e execute `database/schema.sql` no SQL Editor.
2. Em Authentication, desative o cadastro público e crie manualmente seu usuário (e-mail e senha). Habilite confirmação de e-mail conforme necessário.
3. Em Authentication → Signing Keys, utilize uma chave **assimétrica ES256** e confira que os access tokens novos são ES256. O backend rejeita tokens HS256 por segurança.
4. Copie Project URL, **publishable/anon key** (para frontend) e **service_role secret** (somente servidor). Não coloque service_role em variáveis `VITE_` nem no frontend.

## 2. GitHub
1. Crie repositório `jobmatch-ai` e envie os arquivos. Exemplo:
   ```
   git init
   git add .
   git commit -m "feat: initial JobMatch AI web app"
   git branch -M main
   git remote add origin https://github.com/SEU_USUARIO/jobmatch-ai.git
   git push -u origin main
   ```
2. Em Settings → Secrets and variables → Actions → **Secrets**, configure:
   - `VITE_SUPABASE_URL`: URL do projeto Supabase
   - `VITE_SUPABASE_ANON_KEY`: chave pública anon
   - `VITE_API_URL`: URL HTTPS da API Render, sem barra final
   - `SUPABASE_URL`: URL do projeto Supabase
   - `SUPABASE_SERVICE_ROLE_KEY`: chave secreta de serviço (somente workflow/backend)
3. Em **Variables**, configure `GREENHOUSE_BOARDS` como array JSON de tokens reais de boards públicos Greenhouse, por exemplo `["empresa1","empresa2"]`. Não são nomes arbitrários: devem corresponder a boards existentes e relevantes.
4. Settings → Pages → Source: **GitHub Actions**. Execute workflow `Deploy React to GitHub Pages` manualmente na primeira vez.
5. URL esperada: `https://SEU_USUARIO.github.io/jobmatch-ai/`. GitHub Pages serve a interface pública; login protege os dados da API.

## 3. Render
1. Em https://render.com, crie Web Service usando seu repositório GitHub ou use `render.yaml` (Blueprint).
2. Configure env vars: `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `ALLOWED_EMAIL` (seu e-mail de login), `FRONTEND_ORIGIN` (`https://SEU_USUARIO.github.io`, **sem caminho**).
3. Verifique `https://SEU_SERVICO.onrender.com/health`. Adicione essa URL em `VITE_API_URL` no GitHub e faça novo deploy.
4. Render gratuito pode hibernar após inatividade, causando demora no primeiro acesso. Confira limites e condições atuais.

## 4. Coleta diária
- Workflow `.github/workflows/collector.yml` roda aproximadamente às **08:00 de Curitiba** (11:00 UTC), mas GitHub Actions pode atrasar/ignorar execuções agendadas e pode desabilitá-las em repositórios inativos.
- Pode disparar manualmente em Actions → Daily job collector → Run workflow.
- O coletor só armazena vagas com score ≥80; dados da empresa são identificados pelo token do board, que pode não ser nome comercial.
- Não há scraping, login automatizado em sites de emprego ou envio automático de candidaturas.
- A filtragem de remoto é conservadora e ainda pode exigir conferência humana. Não confie em score para requisitos eliminatórios.

## 5. Desenvolvimento local
```
cd frontend
npm install
cp .env.example .env
npm run dev
```
Em outro terminal:
```
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```
Para rodar frontend localmente, `FRONTEND_ORIGIN` no backend deve ser `http://localhost:5173`. Execute testes: `cd backend && python -m unittest discover -s tests`.

## Segurança
- Backend valida assinatura, issuer, audience e expiração do token Supabase e restringe o e-mail permitido.
- CORS restringe o domínio do frontend; CORS **não** substitui autenticação.
- Banco usa RLS sem políticas públicas e revoga acesso direto de usuários anon/authenticated.
- `service_role` contorna RLS: guarde a chave **apenas no Render e no GitHub Actions Secrets**.
- Não armazene currículo ou telefone em repositório público. Considere contas separadas para desenvolvimento e produção.
- Antes de disponibilizar a terceiros, implemente rate limits, observabilidade, testes de integração e gestão de contas.

## Próximos passos
Calibrar algoritmo com requisitos obrigatórios, cadastrar fontes reais, detalhar vagas, registrar decisões de candidatura, anexar currículo em armazenamento privado, integrar conectores autorizados e adicionar auditoria.

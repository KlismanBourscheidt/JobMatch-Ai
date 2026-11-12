
import React, { useEffect, useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { createClient } from '@supabase/supabase-js';

import {
  BriefcaseBusiness,
  Search,
  LogOut,
  RefreshCw,
  ExternalLink,
  ShieldCheck
} from 'lucide-react';

import './style.css';

// ==========================================
// CONFIGURAÇÕES
// ==========================================

const url = import.meta.env.VITE_SUPABASE_URL;
const key = import.meta.env.VITE_SUPABASE_ANON_KEY;

const api = (
  import.meta.env.VITE_API_URL || ''
).replace(/\/$/, '');

const configured = Boolean(url && key && api);

const supabase = url && key
  ? createClient(url, key)
  : null;

const MINIMUM_MATCH = 80;

// ==========================================
// APLICAÇÃO PRINCIPAL
// ==========================================

function App() {

  // Autenticação
  const [session, setSession] = useState(null);
  const [ready, setReady] = useState(false);

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  // Vagas
  const [jobs, setJobs] = useState([]);
  const [filter, setFilter] = useState('all');
  const [query, setQuery] = useState('');

  const [status, setStatus] = useState('');
  const [refreshing, setRefreshing] = useState(false);

  // ==========================================
  // RECUPERAR SESSÃO DO SUPABASE
  // ==========================================

  useEffect(() => {

    if (!supabase) {
      setReady(true);
      return;
    }

    let active = true;

    async function initializeSession() {

      try {

        const { data, error: authError } =
          await supabase.auth.getSession();

        if (authError) {
          throw authError;
        }

        if (active) {
          setSession(data.session);
        }

      } catch (err) {

        console.error(
          'Erro ao recuperar sessão:',
          err.message
        );

      } finally {

        if (active) {
          setReady(true);
        }

      }
    }

    initializeSession();

    const {
      data: { subscription }
    } = supabase.auth.onAuthStateChange(
      (_event, newSession) => {

        if (active) {
          setSession(newSession);
        }

      }
    );

    return () => {
      active = false;
      subscription.unsubscribe();
    };

  }, []);

  // ==========================================
  // CARREGAR VAGAS DA API FASTAPI
  // ==========================================

  async function load() {

    if (!supabase || !api) {
      return;
    }

    setRefreshing(true);
    setStatus('');

    try {

      // Recuperar sessão atual
      const {
        data: { session: currentSession },
        error: sessionError
      } = await supabase.auth.getSession();

      if (sessionError || !currentSession?.access_token) {

        throw new Error(
          'Sessão não encontrada. Faça login novamente.'
        );

      }

      // Consultar backend Python
      const response = await fetch(`${api}/jobs`, {

        method: 'GET',

        // Identifica redirecionamentos inesperados
        redirect: 'error',

        headers: {
          Authorization:
            `Bearer ${currentSession.access_token}`
        }

      });

      // Verificar resposta da API
      if (!response.ok) {

        const result = await response
          .json()
          .catch(() => null);

        if (response.status === 401) {

          throw new Error(
            result?.detail ||
            'Token recusado pelo backend.'
          );

        }

        if (response.status === 403) {

          throw new Error(
            'Sua conta não tem permissão para acessar as vagas.'
          );

        }

        throw new Error(
          result?.detail ||
          `API retornou ${response.status}`
        );

      }

      // Receber vagas
      const result = await response.json();

      setJobs(
        Array.isArray(result.jobs)
          ? result.jobs
          : []
      );

    } catch (err) {

      console.error(
        'Erro ao consultar vagas:',
        err
      );

      setStatus(
        `Falha ao carregar vagas: ${err.message}`
      );

    } finally {

      setRefreshing(false);

    }

  }

  // ==========================================
  // CARREGAR VAGAS APÓS LOGIN
  // ==========================================

  useEffect(() => {

    if (session?.access_token) {
      load();
    } else {
      setJobs([]);
    }

  }, [session?.access_token]);

  // ==========================================
  // LOGIN
  // ==========================================

  async function login(event) {

    event.preventDefault();

    if (!supabase) {
      return;
    }

    setLoading(true);
    setError('');

    try {

      const { error: authError } =
        await supabase.auth.signInWithPassword({
          email: email.trim(),
          password
        });

      if (authError) {
        throw authError;
      }

      setPassword('');

    } catch (err) {

      setError(
        'Não foi possível entrar. Verifique suas credenciais.'
      );

    } finally {

      setLoading(false);

    }

  }

  // ==========================================
  // LOGOUT
  // ==========================================

  async function logout() {

    if (!supabase) {
      return;
    }

    const { error: logoutError } =
      await supabase.auth.signOut();

    if (logoutError) {

      setStatus(
        'Não foi possível encerrar a sessão.'
      );

    }

  }

  // ==========================================
  // FILTROS
  // ==========================================

  const visible = useMemo(() => {

    return jobs.filter((job) => {

      const score = Number(job.score) || 0;

      const matchFilter =
        filter === 'all' ||
        (
          filter === 'match'
            ? score >= MINIMUM_MATCH
            : score < MINIMUM_MATCH
        );

      const searchText = [
        job.title,
        job.company,
        job.location
      ]
        .filter(Boolean)
        .join(' ')
        .toLocaleLowerCase('pt-BR');

      const searchMatch = searchText.includes(
        query.toLocaleLowerCase('pt-BR')
      );

      return matchFilter && searchMatch;

    });

  }, [jobs, filter, query]);

  // ==========================================
  // CONFIGURAÇÃO PENDENTE
  // ==========================================

  if (!configured) {

    return (
      <main className="auth">

        <div className="login">

          <h1>
            JobMatch <em>AI</em>
          </h1>

          <p>Configuração inicial pendente.</p>

          <p>
            Configure VITE_SUPABASE_URL,
            VITE_SUPABASE_ANON_KEY e VITE_API_URL
            no GitHub Actions.
          </p>

        </div>

      </main>
    );

  }

  // ==========================================
  // CARREGAMENTO
  // ==========================================

  if (!ready) {

    return (
      <main className="auth">
        <p>Carregando...</p>
      </main>
    );

  }

  // ==========================================
  // TELA DE LOGIN
  // ==========================================

  if (!session) {

    return (
      <main className="auth">

        <form className="login" onSubmit={login}>

          <div className="logo">
            ✦ JobMatch <em>AI</em>
          </div>

          <h1>Bem-vindo de volta</h1>

          <p>
            Entre para acessar suas oportunidades.
          </p>

          <label>
            E-mail

            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="email"
            />

          </label>

          <label>
            Senha

            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="current-password"
            />

          </label>

          {error && (
            <p className="error">
              {error}
            </p>
          )}

          <button disabled={loading}>

            {loading
              ? 'Entrando...'
              : 'Entrar no painel'}

          </button>

          <small>
            Cadastro público desativado.
            Conta criada manualmente no Supabase.
          </small>

        </form>

      </main>
    );

  }

  // ==========================================
  // DASHBOARD
  // ==========================================

  return (

    <div className="layout">

      {/* MENU LATERAL */}

      <aside>

        <div className="logo">
          ✦ JobMatch <em>AI</em>
        </div>

        <div className="sideitem active">

          <BriefcaseBusiness size={18} />

          Oportunidades

        </div>

        <div className="sidefoot">

          <ShieldCheck size={16} />

          Acesso privado

          <br />

          <small>
            {session.user.email}
          </small>

        </div>

      </aside>

      {/* CONTEÚDO PRINCIPAL */}

      <main>

        <header>

          <div>

            <div className="eyebrow">
              PAINEL PESSOAL
            </div>

            <h1>Suas oportunidades</h1>

            <p>
              Curitiba e remoto no Brasil ·
              Estágio e Desenvolvedor Júnior
            </p>

          </div>

          <button
            className="outline"
            onClick={logout}
          >

            <LogOut size={16} />

            Sair

          </button>

        </header>

        {/* INDICADORES */}

        <div className="stats">

          <div className="stat">

            <span>
              VAGAS ENCONTRADAS
            </span>

            <strong>
              {jobs.length}
            </strong>

          </div>

          <div className="stat">

            <span>
              COMPATIBILIDADE ≥ 80%
            </span>

            <strong>

              {jobs.filter(
                (job) =>
                  Number(job.score) >= MINIMUM_MATCH
              ).length}

            </strong>

          </div>

          <div className="stat">

            <span>
              CANDIDATURAS ENVIADAS
            </span>

            <strong>

              {jobs.filter(
                (job) => job.status === 'applied'
              ).length}

            </strong>

          </div>

        </div>

        {/* PAINEL DE VAGAS */}

        <section className="panel">

          <div className="sectionhead">

            <div>

              <h2>Vagas classificadas</h2>

              <p>
                O score indica aderência heurística,
                não chance de contratação.
              </p>

            </div>

            <button
              className="outline"
              disabled={refreshing}
              onClick={load}
            >

              <RefreshCw size={16} />

              {refreshing
                ? 'Atualizando...'
                : 'Atualizar'}

            </button>

          </div>

          {/* FILTROS */}

          <div className="filters">

            <div className="search">

              <Search size={18} />

              <input
                value={query}
                onChange={(e) =>
                  setQuery(e.target.value)
                }
                placeholder="Cargo, empresa ou cidade"
              />

            </div>

            <select
              value={filter}
              onChange={(e) =>
                setFilter(e.target.value)
              }
            >

              <option value="all">
                Todas
              </option>

              <option value="match">
                Match ≥ 80%
              </option>

              <option value="below">
                Abaixo de 80%
              </option>

            </select>

          </div>

          {/* ERROS */}

          {status && (

            <p className="error">
              {status}
            </p>

          )}

          {/* TABELA */}

          <div className="tablewrap">

            <table>

              <thead>

                <tr>
                  <th>VAGA</th>
                  <th>LOCAL</th>
                  <th>MATCH</th>
                  <th>STATUS</th>
                  <th>LINK</th>
                </tr>

              </thead>

              <tbody>

                {visible.map((job) => (

                  <tr key={job.id}>

                    <td>

                      <b>
                        {job.title}
                      </b>

                      <small>
                        {job.company}
                      </small>

                    </td>

                    <td>
                      {job.location || 'Não informado'}
                    </td>

                    <td>

                      <strong
                        className={
                          Number(job.score) >= MINIMUM_MATCH
                            ? 'good'
                            : 'muted'
                        }
                      >

                        {job.score}%

                      </strong>

                    </td>

                    <td>

                      <span className="tag">
                        {job.status || 'found'}
                      </span>

                    </td>

                    <td>

                      {/^https:\/\//i.test(job.url || '') && (

                        <a
                          href={job.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          aria-label="Abrir vaga"
                        >

                          <ExternalLink size={17} />

                        </a>

                      )}

                    </td>

                  </tr>

                ))}

              </tbody>

            </table>

            {!visible.length && (

              <div className="empty">

                Nenhuma vaga disponível com os
                filtros atuais. Configure as fontes
                e execute o coletor.

              </div>

            )}

          </div>

        </section>

        <footer>
          JobMatch AI · MVP pessoal ·
          Candidaturas automáticas desativadas
        </footer>

      </main>

    </div>

  );

}

// ==========================================
// INICIALIZAR REACT
// ==========================================

createRoot(
  document.getElementById('root')
).render(<App />);

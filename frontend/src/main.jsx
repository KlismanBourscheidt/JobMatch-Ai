import React, {useEffect,useMemo,useState} from 'react'
import {createRoot} from 'react-dom/client'
import {createClient} from '@supabase/supabase-js'
import {BriefcaseBusiness, Search, LogOut, RefreshCw, ExternalLink, ShieldCheck} from 'lucide-react'
import './style.css'
const url=import.meta.env.VITE_SUPABASE_URL
const key=import.meta.env.VITE_SUPABASE_ANON_KEY
const api=(import.meta.env.VITE_API_URL||'').replace(/\/$/,'')
const configured=Boolean(url&&key&&api)
const supabase=url&&key?createClient(url,key):null
function App(){
 const [session,setSession]=useState(null),[ready,setReady]=useState(false)
 const [email,setEmail]=useState(''),[password,setPassword]=useState(''),[error,setError]=useState(''),[loading,setLoading]=useState(false)
 const [jobs,setJobs]=useState([]),[filter,setFilter]=useState('all'),[query,setQuery]=useState('')
 const [status,setStatus]=useState(''),[refreshing,setRefreshing]=useState(false),[expanded,setExpanded]=useState(null)
 useEffect(() => {
   if (!supabase) { setReady(true); return; }
   let active = true;
   async function initialize() {
     try {
       const {data, error: authError} = await supabase.auth.getSession();
       if (authError) throw authError;
       if (active) setSession(data.session);
     } catch (err) {
       console.error('Erro ao recuperar sessão:', err);
     } finally {
       if (active) setReady(true);
     }
   }
   initialize();
   const {data: {subscription}} = supabase.auth.onAuthStateChange((_event, next) => {
     if (active) setSession(next);
   });
   return () => { active = false; subscription.unsubscribe(); };
 }, []);

 async function load() {
   if (!supabase || !api) return;
   setRefreshing(true);
   setStatus('');
   try {
     const {data: {session: currentSession}, error: sessionError} =
       await supabase.auth.getSession();
     if (sessionError || !currentSession?.access_token) {
       throw new Error('Sessão não encontrada. Faça login novamente.');
     }
     const response = await fetch(`${api}/jobs`, {
       method: 'GET',
       redirect: 'error',
       headers: {Authorization: `Bearer ${currentSession.access_token}`}
     });
     if (!response.ok) {
       const result = await response.json().catch(() => null);
       if (response.status === 403) {
         throw new Error('Sua conta não tem permissão para acessar as vagas.');
       }
       throw new Error(result?.detail || `API retornou ${response.status}`);
     }
     const result = await response.json();
     setJobs(Array.isArray(result.jobs) ? result.jobs : []);
   } catch (err) {
     console.error('Erro ao consultar vagas:', err);
     setStatus(`Falha ao carregar vagas: ${err.message}`);
   } finally {
     setRefreshing(false);
   }
 }
 useEffect(() => {
   if (session?.access_token) load();
   else { setJobs([]); setExpanded(null); }
 }, [session?.access_token]);

 async function login(e) {
   e.preventDefault();
   if (!supabase) return;
   setLoading(true);
   setError('');
   try {
     const {error: authError} = await supabase.auth.signInWithPassword({
       email: email.trim(), password
     });
     if (authError) throw authError;
     setPassword('');
   } catch (err) {
     setError('Não foi possível entrar. Verifique suas credenciais.');
   } finally {
     setLoading(false);
   }
 }
 async function logout() {
   if (!supabase) return;
   const {error: logoutError} = await supabase.auth.signOut();
   if (logoutError) setStatus('Não foi possível encerrar a sessão.');
 }
 const visible=useMemo(()=>jobs.filter(j=>Number(j.score)>=50&&(filter==='all'||(filter==='match'?Number(j.score)>=80:Number(j.score)<80))&&`${j.title} ${j.company} ${j.location}`.toLowerCase().includes(query.toLowerCase())),[jobs,filter,query])
 if(!configured)return <main className="auth"><div className="login"><h1>JobMatch <em>AI</em></h1><p>Configuração inicial pendente.</p><p>Defina VITE_SUPABASE_URL, VITE_SUPABASE_ANON_KEY e VITE_API_URL no build do frontend. Veja README.md.</p></div></main>
 if(!ready)return <main className="auth"><p>Carregando...</p></main>
 if(!session)return <main className="auth"><form className="login" onSubmit={login}><div className="logo">✦ JobMatch <em>AI</em></div><h1>Bem-vindo de volta</h1><p>Entre para acessar suas oportunidades.</p><label>E-mail<input type="email" value={email} onChange={e=>setEmail(e.target.value)} required autoComplete="email"/></label><label>Senha<input type="password" value={password} onChange={e=>setPassword(e.target.value)} required autoComplete="current-password"/></label>{error&&<p className="error">{error}</p>}<button disabled={loading}>{loading?'Entrando...':'Entrar no painel'}</button><small>Cadastro público desativado. Conta criada manualmente no Supabase.</small></form></main>
 return <div className="layout"><aside><div className="logo">✦ JobMatch <em>AI</em></div><div className="sideitem active"><BriefcaseBusiness size={18}/> Oportunidades</div><div className="sidefoot"><ShieldCheck size={16}/> Acesso privado<br/><small>{session.user.email}</small></div></aside><main><header><div><div className="eyebrow">PAINEL PESSOAL</div><h1>Suas oportunidades</h1><p>Curitiba e remoto no Brasil · Oportunidades a partir de 50%</p></div><button className="outline" onClick={logout}><LogOut size={16}/> Sair</button></header><div className="stats"><div className="stat"><span>VAGAS ENCONTRADAS</span><strong>{jobs.length}</strong></div><div className="stat"><span>COMPATIBILIDADE ≥ 80%</span><strong>{jobs.filter(j=>Number(j.score)>=80).length}</strong></div><div className="stat"><span>CANDIDATURAS ENVIADAS</span><strong>{jobs.filter(j=>j.status==='applied').length}</strong></div></div><section className="panel"><div className="sectionhead"><div><h2>Vagas classificadas</h2><p>O score indica aderência heurística, não chance de contratação.</p></div><button className="outline" disabled={refreshing} onClick={()=>load()}><RefreshCw size={16}/> {refreshing?'Atualizando...':'Atualizar'}</button></div><div className="filters"><div className="search"><Search size={18}/><input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Cargo, empresa ou cidade"/></div><select value={filter} onChange={e=>setFilter(e.target.value)}><option value="all">Todas</option><option value="match">Match ≥ 80%</option><option value="below">Abaixo de 80%</option></select></div>{status&&<p className="error">{status}</p>}<div className="tablewrap"><table><thead><tr><th>VAGA</th><th>LOCAL</th><th>MATCH</th><th>STATUS</th><th>ANÁLISE</th><th>LINK</th></tr></thead><tbody>{visible.map(j=><React.Fragment key={j.id}><tr><td><b>{j.title}</b><small>{j.company}</small></td><td>{j.location||'Não informado'}</td><td><strong className={Number(j.score)>=80?'good':'muted'}>{j.score}%</strong></td><td><span className="tag">{j.status||'found'}</span></td><td><button className="outline" onClick={()=>setExpanded(expanded===j.id?null:j.id)}>{expanded===j.id?"Ocultar":"Detalhes"}</button></td><td>{/^https:\/\//i.test(j.url || '') && <a href={j.url} target="_blank" rel="noopener noreferrer" aria-label="Abrir vaga"><ExternalLink size={17}/></a>}</td></tr>{expanded===j.id&&<tr><td colSpan={6}><div className="match-details"><h3>Por que {j.score}%?</h3><p>Estimativa heurística baseada no cargo, localização e tecnologias mencionadas. Não representa chance de contratação.</p><div className="skill-columns"><div><h4>✓ Habilidades identificadas</h4>{(j.matched_skills||[]).length?<p>{j.matched_skills.join(', ')}</p>:<p>Nenhuma identificada na descrição.</p>}</div><div><h4>△ Requisitos não comprovados</h4>{(j.missing_skills||[]).length?<p>{j.missing_skills.join(', ')}</p>:<p>Nenhum identificado.</p>}</div></div><h4>Próximos estudos sugeridos</h4><ul>{(j.study_recommendations||[]).map((tip,i)=><li key={i}>{tip}</li>)}</ul><small>Itens não comprovados não significam falta de conhecimento. Confira sempre os requisitos completos na vaga original.</small></div></td></tr>}</React.Fragment>)}</tbody></table>{!visible.length&&<div className="empty">Nenhuma vaga disponível com os filtros atuais. Configure as fontes e execute o coletor.</div>}</div></section><footer>JobMatch AI · MVP pessoal · Candidaturas automáticas desativadas</footer></main></div>
}
createRoot(document.getElementById('root')).render(<App/>)

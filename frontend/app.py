"""Operlynt enterprise operations dashboard backed by the FastAPI service."""
from __future__ import annotations
import os
import json
from html import escape
import requests
import pandas as pd
import plotly.express as px
import streamlit as st
from frontend.api_client import APIError, OperlyntAPI

st.set_page_config(page_title="Operlynt | Operations Workspace",page_icon="◈",layout="wide",initial_sidebar_state="expanded")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@500;600;700;800&display=swap');
:root {--ink:#172334;--muted:#738096;--line:#e7ebf1;--canvas:#f4f6f9;--panel:#fff;--violet:#5e69d8;--violet-soft:#eef0ff;--teal:#38a99a;--amber:#e9a945;--rose:#e87986;}
html, body, [class*="css"] {font-family:'DM Sans',sans-serif;color:var(--ink);}
[data-testid="stAppViewContainer"] {background:var(--canvas);}
[data-testid="stHeader"] {background:rgba(244,246,249,.84);}
.block-container {padding:1.35rem 2rem 2.4rem;max-width:1700px;}
h1,h2,h3,h4 {font-family:'Manrope','DM Sans',sans-serif;letter-spacing:-.035em;color:var(--ink);}
h1 {font-size:2rem!important;font-weight:800!important;margin:0!important;}
h2 {font-weight:750!important;}
p, label {color:#39485c;}
.ops-brand {font-family:'Manrope',sans-serif;font-size:1.32rem;font-weight:800;letter-spacing:-.055em;color:#202a3b;margin:0;}
.ops-subtitle {color:var(--muted);margin-top:.22rem;font-size:.78rem;line-height:1.45;}
.status-pill {display:inline-flex;align-items:center;gap:.38rem;border-radius:999px;padding:6px 10px;background:#e8f6f1;color:#24836f;font-size:.73rem;font-weight:700;}
.page-heading {margin:0 0 1.15rem;}
.page-eyebrow {color:#8590a3;font-size:.67rem;text-transform:uppercase;letter-spacing:.15em;font-weight:700;margin:0 0 .42rem;}
.page-title-row {display:flex;align-items:center;gap:.75rem;flex-wrap:wrap;}
.page-subtitle {color:var(--muted);font-size:.91rem;margin:.4rem 0 0;}
.workspace-topbar {background:rgba(255,255,255,.78);border:1px solid var(--line);border-radius:18px;padding:.65rem 1rem;margin-bottom:1.35rem;box-shadow:0 6px 24px rgba(24,39,75,.035);}
.topbar-label {font-size:.68rem;color:#8490a2;text-transform:uppercase;letter-spacing:.11em;font-weight:700;margin:0 0 .18rem;}
.topbar-title {font:700 1rem 'Manrope',sans-serif;color:#26354a;margin:0;}
.section-label {font-size:.68rem;color:#8792a3;letter-spacing:.12em;text-transform:uppercase;font-weight:800;margin:0 0 .55rem;}
.card-title {font:700 1rem 'Manrope',sans-serif;color:#25354a;margin:0;}
.card-caption {font-size:.76rem;color:#8290a2;margin:.18rem 0 0;}
.dashboard-card {background:white;border:1px solid var(--line);border-radius:17px;padding:1rem 1.1rem;box-shadow:0 7px 24px rgba(27,43,65,.035);}
.task-row {display:flex;gap:.65rem;align-items:flex-start;padding:.74rem .1rem;border-bottom:1px solid #eff1f5;}
.task-row:last-child {border-bottom:0;padding-bottom:.1rem;}
.task-dot {width:30px;height:30px;border-radius:10px;display:flex;align-items:center;justify-content:center;background:#f0f2ff;color:#5e69d8;font-size:.9rem;flex:none;}
.task-name {font-size:.79rem;font-weight:700;color:#29384b;margin:0;}
.task-detail {font-size:.69rem;color:#8b95a5;margin:.12rem 0 0;line-height:1.4;}
.task-state {margin-left:auto;border-radius:20px;padding:4px 7px;background:#f4f6f9;color:#738096;font-size:.59rem;font-weight:700;white-space:nowrap;}
.task-state.alert {background:#fff1e7;color:#bd723a;}
.activity-row {display:flex;gap:.62rem;align-items:flex-start;padding:.68rem 0;border-bottom:1px solid #eff1f5;}
.activity-avatar {width:29px;height:29px;border-radius:50%;background:#e9edff;color:#5966c8;display:flex;align-items:center;justify-content:center;font-weight:800;font-size:.65rem;flex:none;}
.activity-title {font-size:.73rem;font-weight:700;color:#344256;margin:0;}
.activity-detail {font-size:.66rem;color:#8a95a4;margin:.12rem 0 0;line-height:1.4;}
.ops-muted {color:var(--muted);font-size:.84rem;}
[data-testid="stMetric"] {background:#fff;border:1px solid var(--line);padding:15px 17px;border-radius:15px;box-shadow:0 5px 20px rgba(24,39,75,.035);}
[data-testid="stMetricLabel"] {color:#8390a1;font-size:.75rem;font-weight:600;}
[data-testid="stMetricValue"] {color:#25354a;font-family:'Manrope',sans-serif;font-size:1.65rem;font-weight:800;}
[data-testid="stMetricDelta"] {font-size:.68rem;}
[data-testid="stSidebar"] {background:#fbfcfe;border-right:1px solid #e6eaf0;}
[data-testid="stSidebar"] > div:first-child {padding-top:1.2rem;}
[data-testid="stSidebar"] [data-testid="stRadio"] > label {display:none;}
[data-testid="stSidebar"] [role="radiogroup"] {gap:5px;}
[data-testid="stSidebar"] [role="radiogroup"] label {border-radius:11px;padding:.32rem .5rem;transition:.15s;}
[data-testid="stSidebar"] [role="radiogroup"] label:hover {background:#f0f2f8;}
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {background:#eef0ff;color:#4e5bcc;font-weight:700;}
[data-testid="stSidebar"] [role="radiogroup"] label p {font-size:.81rem;}
[data-testid="stButton"] button {border-radius:10px;font-weight:700;}
[data-testid="stBaseButton-primary"], [data-testid="stFormSubmitButton"] button[kind="primary"] {background:var(--violet)!important;border-color:var(--violet)!important;color:#fff!important;}
[data-testid="stBaseButton-primary"]:hover, [data-testid="stFormSubmitButton"] button[kind="primary"]:hover {background:#4d58c8!important;border-color:#4d58c8!important;}
[data-testid="stTextInput"] input,[data-testid="stTextArea"] textarea,[data-testid="stSelectbox"] [data-baseweb="select"] > div {border-radius:10px;border-color:#dfe4ec;}
[data-testid="stTabs"] [data-baseweb="tab-list"] {gap:.35rem;border-bottom:1px solid var(--line);}
[data-testid="stTabs"] [data-baseweb="tab"] {border-radius:10px 10px 0 0;font-weight:650;color:#718096;}
[data-testid="stTabs"] [aria-selected="true"] {color:#5462cf;border-bottom-color:#626ed7;}
[data-testid="stDataFrame"] {border:1px solid var(--line);border-radius:13px;overflow:hidden;}
[data-testid="stChatMessage"] {background:white;border:1px solid var(--line);border-radius:14px;}
.login-shell {background:linear-gradient(135deg,#f4efff 0%,#f7f8fc 55%,#eaf1ff 100%);border-radius:26px;padding:1rem;}
.login-card {background:rgba(255,255,255,.96);border:1px solid rgba(224,228,238,.9);border-radius:22px;padding:1.5rem;box-shadow:0 20px 60px rgba(58,50,95,.1);}
.login-kicker {font-size:.68rem;text-transform:uppercase;letter-spacing:.16em;color:#7e86a0;font-weight:800;}
.login-heading {font:800 1.9rem 'Manrope',sans-serif;letter-spacing:-.06em;color:#202d43;margin:.5rem 0 .25rem;}
.login-copy {font-size:.84rem;color:#828da0;margin:0 0 1.1rem;}
.login-hero {background:linear-gradient(145deg,#f6f2ff,#eef2ff 70%,#f8f5ff);border:1px solid #e9e5f5;border-radius:21px;padding:1.1rem;min-height:450px;display:flex;flex-direction:column;justify-content:space-between;overflow:hidden;}
.hero-caption {font:700 1.28rem 'Manrope',sans-serif;letter-spacing:-.04em;color:#34425b;margin:.3rem 0;}
.hero-small {font-size:.78rem;color:#7a879b;margin:0;}
@media(max-width:900px){.block-container{padding:.9rem 1rem 1.5rem}.login-hero{min-height:300px}.page-title-row{align-items:flex-start}}
@media(max-width:700px){[data-testid="stHorizontalBlock"]:has(.login-hero){flex-direction:column;gap:1rem}.login-heading{font-size:1.55rem}.login-hero{min-height:260px}.login-hero svg{max-height:225px!important}}
/* Workspace refresh: polished dark analytics surfaces, clear hierarchy, touch-friendly controls. */
:root {--ink:#f5f6ff;--muted:#a3a8c0;--line:#292943;--canvas:#0c0c1a;--panel:#151528;--violet:#746cff;--violet-soft:#242341;}
[data-testid="stAppViewContainer"], [data-testid="stMain"] {background:#0c0c1a;color:#f5f6ff;}
[data-testid="stHeader"] {background:#0c0c1a;}
.block-container {max-width:1600px;padding:3.4rem 2.2rem 1.2rem;}
h1,h2,h3,h4,p,label {color:#f0f1fa;}
h1 {font-size:2.25rem!important;}
.ops-brand {font-size:1.2rem;color:#fff;white-space:nowrap;}
.ops-subtitle,.page-subtitle,.card-caption,.ops-muted {color:#9b9db6;}
.workspace-topbar {background:#101022;border:1px solid #25253b;border-radius:18px;padding:.7rem 1rem;margin-bottom:1.25rem;box-shadow:0 10px 32px #05050e66;}
.topbar-label,.section-label,.page-eyebrow {color:#898da9;}
.topbar-title,.card-title {color:#f4f4fc;}
.dashboard-card,[data-testid="stMetric"],div[data-testid="stVerticalBlockBorderWrapper"] {background:#151528;border:1px solid #292943;border-radius:17px;box-shadow:0 12px 32px #05050e40;}
div[data-testid="stVerticalBlockBorderWrapper"] > div {border-color:#292943!important;border-radius:17px;}
[data-testid="stMetric"] {padding:1rem 1.15rem;min-height:105px;}
[data-testid="stMetricLabel"] {color:#a0a3bd;}
[data-testid="stMetricValue"] {color:#fff;font-size:1.9rem;}
[data-testid="stMetricDelta"] {font-size:.72rem;}
.task-row,.activity-row {border-color:#282840;}
.task-name,.activity-title {color:#e6e7f2;}
.task-detail,.activity-detail {color:#999bb4;}
.task-dot {background:#262345;color:#9e98ff;}
.task-state {background:#24243b;color:#c4c5d9;}
.task-state.alert {background:#392536;color:#ffabb5;}
.activity-avatar {background:#292744;color:#b2adff;}
[data-testid="stBaseButton-primary"], [data-testid="stFormSubmitButton"] button[kind="primary"] {background:#7067f0!important;border-color:#7067f0!important;color:#fff!important;}
[data-testid="stButton"] button,[data-testid="stFormSubmitButton"] button {min-height:42px;border-radius:11px;font-weight:700;}
[data-testid="stButton"] button:not([kind="primary"]),[data-testid="stFormSubmitButton"] button:not([kind="primary"]){background:#1b1b31;color:#e7e7f4;border-color:#35354f;}
[data-testid="stTextInput"] input,[data-testid="stTextArea"] textarea,[data-testid="stSelectbox"] [data-baseweb="select"] > div {background:#111122;color:#fff;border:1px solid #34344e;border-radius:11px;min-height:44px;}
[data-testid="stTextInput"] input::placeholder,[data-testid="stTextArea"] textarea::placeholder {color:#aeb2c9!important;opacity:1!important;}
[data-testid="stTextInput"] input:focus,[data-testid="stTextArea"] textarea:focus {border-color:#8179ff!important;box-shadow:0 0 0 1px #8179ff!important;}
[data-testid="stPopoverButton"] {background:#1b1b31!important;color:#f1f0ff!important;border:1px solid #454563!important;border-radius:10px!important;}
[data-testid="stPopoverButton"] * {color:#f1f0ff!important;opacity:1!important;}
[data-testid="stTabs"] [data-baseweb="tab-list"] {border-color:#2b2b45;}
[data-testid="stTabs"] [data-baseweb="tab"] {color:#aaacc3;}
[data-testid="stTabs"] [aria-selected="true"] {color:#a7a1ff;border-color:#8179ff;}
[data-testid="stDataFrame"] {border:1px solid #2b2b45;border-radius:13px;}
[data-testid="stChatMessage"] {background:#151528;border-color:#292943;}
[data-testid="stSidebar"] {display:none;}
.login-heading {color:#202d43;}
.login-hero {box-shadow:0 20px 65px #4c3a7b20;}
.app-navbar {display:flex;align-items:center;gap:1rem;background:#101022;border:1px solid #25253b;border-radius:16px;padding:.55rem .9rem;margin:.2rem 0 1.2rem;}
.app-footer {border-top:1px solid #292943;margin-top:2.4rem;padding:1rem .2rem .4rem;color:#8f91ab;font-size:.75rem;}
.app-footer a {color:#aaa5ff;text-decoration:none;margin-right:1rem;}
.nav-tagline {font-size:.58rem;color:#8f91ac;letter-spacing:.08em;margin:.1rem 0 0;white-space:nowrap;}
.account-chip {display:flex;align-items:center;gap:.45rem;white-space:nowrap;}
.account-chip b,.account-chip small {display:block;color:#e7e7f2;font-size:.69rem;}
.account-chip small {color:#8f91ac;font-size:.61rem;margin-top:.12rem;}
.workspace-divider {height:1px;background:linear-gradient(90deg,#272741,transparent);margin:.5rem 0 1.2rem;}
.auth-brand {max-width:1160px;margin:.8rem auto 1.3rem;}
.auth-switch-copy {text-align:center;color:#9698b0;font-size:.75rem;margin:.85rem 0 .25rem;}
.auth-secure {margin-top:1rem;padding-top:.8rem;border-top:1px solid #292943;color:#9698b0;font-size:.69rem;}
.auth-visual {background:radial-gradient(ellipse at 75% 20%,#27204b 0%,#17172d 48%,#111121 100%);border-color:#2b294a;}
.auth-visual .login-kicker {color:#aaa4ff;}
.auth-visual .hero-caption {color:#f2efff;font-size:1.8rem;}
.auth-visual .hero-small {color:#a5a6c0;}
.preview-board {background:#101020;border:1px solid #35324f;border-radius:17px;padding:1rem;box-shadow:0 20px 42px #05050c77;}
.preview-board-head {display:flex;justify-content:space-between;color:#e9e8f7;font-weight:700;font-size:.82rem;}
.preview-live {color:#75d6ba;font-size:.62rem;letter-spacing:.12em;}
.preview-stats {display:grid;grid-template-columns:repeat(3,1fr);gap:.55rem;margin:1rem 0;}
.preview-stats div {background:#19192d;border:1px solid #282841;border-radius:11px;padding:.7rem;}
.preview-stats small,.preview-stats b,.preview-stats em {display:block;}
.preview-stats small {color:#888ba8;font-size:.55rem;letter-spacing:.09em;}
.preview-stats b {color:#fff;font-size:1.1rem;margin:.25rem 0;}
.preview-stats em {font-style:normal;color:#72d1ae;font-size:.62rem;}
.preview-chart {height:105px;display:flex;align-items:end;gap:.5rem;padding:.8rem .25rem .2rem;border-bottom:1px solid #32314c;background:repeating-linear-gradient(to bottom,transparent 0,transparent 25px,#26263d 26px);}
.preview-chart span {flex:1;border-radius:5px 5px 0 0;background:linear-gradient(180deg,#8b7fff,#544bd0);opacity:.9;}
.preview-foot {display:flex;gap:1rem;flex-wrap:wrap;padding-top:.75rem;color:#a0a1b8;font-size:.62rem;}
.preview-foot i {display:inline-block;width:7px;height:7px;border-radius:50%;background:#8378ff;margin-right:.25rem;}
[data-testid="stAppViewContainer"] .js-plotly-plot .plotly .bg {fill:transparent!important;}
.app-footer {color:#888ba5;}
[data-testid="stRadio"] > label {display:none;}
[data-testid="stRadio"] [role="radiogroup"] {display:flex;flex-direction:row;flex-wrap:nowrap;overflow-x:auto;overflow-y:hidden;gap:.2rem;scrollbar-width:thin;scrollbar-color:#555477 #151528;}
[data-testid="stRadio"] [role="radiogroup"] label {flex:0 0 auto;white-space:nowrap;padding:.48rem .58rem;border-radius:10px;color:#e4e4f2!important;opacity:1!important;}
[data-testid="stRadio"] [role="radiogroup"] label p,[data-testid="stRadio"] [role="radiogroup"] label span,[data-testid="stRadio"] [role="radiogroup"] label div {color:inherit!important;font-size:.78rem;font-weight:650;opacity:1!important;}
[data-testid="stRadio"] [role="radiogroup"] label:has(input:checked) {background:#39365f;color:#fff;box-shadow:inset 0 0 0 1px #716bd0;}
[data-testid="stRadio"] [role="radiogroup"] label:hover {background:#292942;color:#fff;}
@media(max-width:900px){.block-container{padding:2.8rem .9rem 1rem}.app-navbar{align-items:flex-start;flex-direction:column}.app-navbar [data-testid="stRadio"] [role="radiogroup"]{max-width:100%;}.login-hero{min-height:300px}}
</style>
""",unsafe_allow_html=True)

DEFAULT_API=os.getenv("OPERLYNT_API",os.getenv("OPSPILOT_API","http://127.0.0.1:8000"))
if "api_base" not in st.session_state:st.session_state.api_base=DEFAULT_API
if "token" not in st.session_state:st.session_state.token=""
if "user" not in st.session_state:st.session_state.user=None
if "thread_id" not in st.session_state:st.session_state.thread_id=""
if "http_session" not in st.session_state:st.session_state.http_session=requests.Session()
if "auth_view" not in st.session_state:st.session_state.auth_view="signin"

PAGES=["Overview Dashboard","E-commerce Intelligence","IT Operations Intelligence","AI Agent Chat",
       "RAG Document Intelligence","Agent Execution Monitoring","Human Approval Center","Ticket Management","Settings"]

def client()->OperlyntAPI:
    return OperlyntAPI(st.session_state.api_base,st.session_state.token or None,timeout=20,session=st.session_state.http_session)

def call(fn,*args,**kwargs):
    try:return fn(*args,**kwargs)
    except APIError as exc:
        if exc.status_code==401:
            st.session_state.token="";st.session_state.user=None
            st.warning("Your sign-in has expired. Sign in again to continue.")
        else:st.error(str(exc))
        return None

def empty(message:str):st.info(message)

def frame(title:str,subtitle:str|None=None):
    safe_title=escape(title)
    safe_subtitle=escape(subtitle or "")
    st.markdown(f"<div class='page-heading'><p class='page-eyebrow'>Operlynt <span style='padding:0 .3rem;color:#bbc3d0'>/</span> Workspace</p><div class='page-title-row'><h1>{safe_title}</h1></div><p class='page-subtitle'>{safe_subtitle}</p></div>",unsafe_allow_html=True)

def chart(data:list[dict],x:str,y:str,title:str,kind="bar",color=None):
    if not data:empty("No records are available for this chart yet.");return
    df=pd.DataFrame(data)
    if x not in df or y not in df:empty("The backend did not return chart data for this view.");return
    if kind=="line":fig=px.line(df,x=x,y=y,color=color,markers=True,title=title)
    elif kind=="pie":fig=px.pie(df,names=x,values=y,hole=.55,title=title)
    else:fig=px.bar(df,x=x,y=y,color=color,title=title)
    colors=["#626ed7","#39a99b","#edb44f","#e87986","#9b84df","#79b8ca"]
    fig.update_layout(template="plotly_dark",margin=dict(l=8,r=8,t=42,b=8),paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",font=dict(family="DM Sans, sans-serif",color="#a9abc1",size=11),legend_title_text="",title_font=dict(family="Manrope, sans-serif",size=14,color="#f0efff"),colorway=colors,showlegend=(kind=="pie"))
    fig.update_xaxes(showgrid=False,linecolor="#33334c",tickfont=dict(color="#9699b2",size=10))
    fig.update_yaxes(gridcolor="#28283f",zerolinecolor="#28283f",tickfont=dict(color="#9699b2",size=10))
    if kind=="pie":fig.update_traces(hole=.64,marker=dict(colors=colors,line=dict(color="#fff",width=4)),textposition="inside",textfont=dict(color="#fff"))
    elif kind=="line":fig.update_traces(line=dict(width=2.5),marker=dict(size=6))
    else:fig.update_traces(marker_line_width=0,opacity=.9)
    st.plotly_chart(fig,use_container_width=True,theme=None)

def multi_line_chart(data:list[dict],x:str,ys:list[str],title:str):
    if not data:empty("No records are available for this chart yet.");return
    df=pd.DataFrame(data)
    if x not in df or not any(col in df for col in ys):empty("The backend did not return chart data for this view.");return
    columns=[col for col in ys if col in df]
    melted=df.melt(id_vars=[x],value_vars=columns,var_name="measure",value_name="value")
    fig=px.line(melted,x=x,y="value",color="measure",markers=True,title=title)
    fig.update_layout(template="plotly_dark",margin=dict(l=8,r=8,t=42,b=8),paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",font=dict(family="DM Sans, sans-serif",color="#a9abc1",size=11),legend_title_text="",title_font=dict(family="Manrope, sans-serif",size=14,color="#f0efff"),colorway=["#8278ff","#39c3ac","#f0b95f"])
    fig.update_xaxes(showgrid=False,linecolor="#33334c",tickfont=dict(color="#9699b2",size=10))
    fig.update_yaxes(gridcolor="#28283f",zerolinecolor="#28283f",tickfont=dict(color="#9699b2",size=10))
    fig.update_traces(line=dict(width=2.6),marker=dict(size=5))
    st.plotly_chart(fig,use_container_width=True,theme=None)

def show_workflow(result:dict):
    answer=result.get("answer") or result.get("final_response")
    if answer:st.markdown("#### Operlynt response");st.write(answer)
    if result.get("thread_id"):
        st.session_state.thread_id=result["thread_id"]
        st.caption(f"Workflow {result['thread_id']} · {result.get('persistence_backend','backend state')}")
    agents=result.get("agents",[])
    if agents:
        st.markdown("#### Execution steps")
        st.write(" → ".join(str(agent).replace("_"," ").title() for agent in agents))
    agent_results=result.get("agent_results",{})
    if agent_results:
        with st.expander("Agent evidence and tool activity"):
            for name,value in agent_results.items():
                st.markdown(f"**{name.replace('_',' ').title()}**")
                if isinstance(value,dict):
                    used=value.get("mcp_tools_used") or value.get("tools_used")
                    if used:st.caption("Tools: "+", ".join(used))
                st.json(value)
    sources=result.get("sources") or result.get("retrieved_documents") or []
    if sources:
        with st.expander(f"Sources and evidence ({len(sources)})"):
            for source in sources:
                if isinstance(source,dict):st.write(source.get("citation") or source.get("document") or source.get("document_name") or "Source",source)
                else:st.write(source)
    recommendations=result.get("recommendations") or []
    if recommendations:
        st.markdown("#### Recommendations")
        for item in recommendations:
            st.write(item.get("recommendation",item) if isinstance(item,dict) else item)
    proposed=result.get("proposed_actions") or []
    interrupt=result.get("approval_interrupt")
    if proposed or interrupt:
        st.warning("This workflow has a proposed action awaiting human review.")
        st.json(proposed or (interrupt.get("action") if isinstance(interrupt,dict) else interrupt))
        st.caption("Review this action in Human Approval Center. The app does not execute it directly.")
    if result.get("errors"):
        with st.expander("Workflow errors",expanded=True):st.json(result["errors"])

def login_page():
    st.markdown("<div class='auth-brand'><p class='ops-brand'>&#9672; Operlynt</p><p class='ops-subtitle'>BUSINESS OPERATIONS INTELLIGENCE</p></div>",unsafe_allow_html=True)
    left,right=st.columns([.95,1.25],gap="large",vertical_alignment="center")
    with left:
        with st.container(border=True):
            signing_up=st.session_state.auth_view=="signup"
            title="Create your account" if signing_up else "Sign in to your workspace"
            kicker="Get started" if signing_up else "Welcome back"
            copy="Create an analyst account to explore your operations." if signing_up else "Your business operations, insights, and team decisions in one place."
            st.markdown(f"<p class='login-kicker'>{kicker}</p><h2 class='login-heading'>{title}</h2><p class='login-copy'>{copy}</p>",unsafe_allow_html=True)
            if signing_up:
                with st.form("register_form"):
                    new_username=st.text_input("Username",placeholder="Choose a username")
                    new_password=st.text_input("Password (12+ characters)",type="password",placeholder="Create a strong password")
                    register=st.form_submit_button("Create account",type="primary",use_container_width=True)
                if register:
                    try:
                        OperlyntAPI(st.session_state.api_base).post("/api/auth/register",{"username":new_username,"password":new_password})
                        st.success("Account created. You can now sign in.")
                        st.session_state.auth_view="signin"
                    except APIError as exc:st.error(str(exc))
                if st.button("Already have an account? Sign in",use_container_width=True,key="show_signin"):
                    st.session_state.auth_view="signin";st.rerun()
            else:
                with st.form("login_form"):
                    username=st.text_input("Username",placeholder="Enter your username")
                    password=st.text_input("Password",type="password",placeholder="Enter your password")
                    submit=st.form_submit_button("Sign in",type="primary",use_container_width=True)
                if submit:
                    with st.spinner("Signing in..."):
                        try:
                            payload=OperlyntAPI.login(st.session_state.api_base,username,password)
                            st.session_state.token=payload["access_token"]
                            profile=OperlyntAPI(st.session_state.api_base,payload["access_token"]).get("/api/auth/me")
                            st.session_state.user=profile;st.rerun()
                        except APIError as exc:st.error(str(exc))
                st.markdown("<p class='auth-switch-copy'>New to Operlynt?</p>",unsafe_allow_html=True)
                if st.button("Create an account",use_container_width=True,key="show_register"):
                    st.session_state.auth_view="signup";st.rerun()
            st.markdown("<div class='auth-secure'>Secure sign-in &middot; Role-based workspace access</div>",unsafe_allow_html=True)
    with right:
        st.markdown("""
        <div class="login-hero auth-visual">
          <div><p class="login-kicker">OPERATIONS CONTROL CENTER</p><p class="hero-caption">See the signals.<br>Move with confidence.</p><p class="hero-small">Bring business performance, service health, and AI-assisted decisions together.</p></div>
          <div class="preview-board">
            <div class="preview-board-head"><span>Workspace overview</span><span class="preview-live">LIVE</span></div>
            <div class="preview-stats"><div><small>ORDERS</small><b>2,480</b><em>+12.8%</em></div><div><small>OPEN TICKETS</small><b>18</b><em>4 critical</em></div><div><small>AI INSIGHTS</small><b>24</b><em>this week</em></div></div>
            <div class="preview-chart"><span style="height:28%"></span><span style="height:42%"></span><span style="height:35%"></span><span style="height:54%"></span><span style="height:48%"></span><span style="height:73%"></span><span style="height:62%"></span><span style="height:88%"></span><span style="height:70%"></span><span style="height:96%"></span><span style="height:78%"></span><span style="height:100%"></span></div>
            <div class="preview-foot"><span><i></i> Business analytics</span><span><i></i> AI workflows</span><span><i></i> Human approvals</span></div>
          </div>
        </div>
        """,unsafe_allow_html=True)

if not st.session_state.token:
    login_page()
    st.markdown("<div class='app-footer'>? 2026 Operlynt ? <a href='#about'>About</a><a href='#privacy'>Privacy</a><a href='#terms'>Terms</a></div>",unsafe_allow_html=True)
    st.stop()

if not st.session_state.user:
    profile=call(client().get,"/api/auth/me")
    if profile:st.session_state.user=profile
    else:st.stop()

user=st.session_state.user or {}
api=client()

def render_topbar():
    with st.container():
        brand,nav,account,signout=st.columns([1.25,6.3,1.25,.85],vertical_alignment="center")
        with brand:
            st.markdown("<p class='ops-brand'>&#9672; Operlynt</p><p class='nav-tagline'>OPERATIONS INTELLIGENCE</p>",unsafe_allow_html=True)
        with nav:
            page=st.radio("Workspace sections",PAGES,horizontal=True,format_func=lambda value:{"Overview Dashboard":"Overview","E-commerce Intelligence":"Commerce","IT Operations Intelligence":"IT Ops","AI Agent Chat":"AI Chat","RAG Document Intelligence":"Documents","Agent Execution Monitoring":"Agents","Human Approval Center":"Approvals","Ticket Management":"Tickets","Settings":"Settings"}[value],label_visibility="collapsed",key="workspace_page")
        with account:
            st.markdown(f"<div class='account-chip'><span class='activity-avatar'>{escape(user.get('username','U')[:1].upper())}</span><span><b>{escape(user.get('username','User'))}</b><small>{escape(user.get('role','user').title())}</small></span></div>",unsafe_allow_html=True)
        with signout:
            if st.button("Sign out",key="signout_top",use_container_width=True):
                st.session_state.token="";st.session_state.user=None;st.rerun()
    st.markdown("<div class='workspace-divider'></div>",unsafe_allow_html=True)
    return page

def render_footer():
    st.markdown("<div class='app-footer'><span>&#169; 2026 Operlynt &middot; Built for clearer operations</span></div>",unsafe_allow_html=True)
    about,privacy,terms,space=st.columns([1,1,1,7])
    with about:
        with st.popover("About"):
            st.write("Operlynt brings operational analytics, AI workflows, and human review into one workspace.")
    with privacy:
        with st.popover("Privacy"):
            st.write("Use organization-approved data only. Credentials and access tokens are handled by the backend and are not displayed here.")
    with terms:
        with st.popover("Terms"):
            st.write("This workspace is an operational decision support tool. Review proposed actions and source evidence before acting.")

def load_metrics():
    e=call(api.get,"/api/analytics/ecommerce");it=call(api.get,"/api/analytics/it")
    return e,it

def render_overview():
    frame("Project Dashboard","Manage and track business performance, customer signals, and operational health.")
    with st.spinner("Loading operational metrics..."):e,it=load_metrics()
    if not e or not it:return
    pending=[]
    if user.get("role") in {"admin","manager"}:
        rows=call(api.get,"/api/approvals");pending=[a for a in (rows or []) if a.get("status")=="pending"]
    activity=call(api.get,"/api/agents/activity") or []
    top=st.columns(4)
    metrics=[("Orders tracked",e.get("orders",0),"E-commerce"),("Return rate",f"{e.get('return_rate',0)}%","Customer experience"),("Open tickets",it.get("open_tickets",0),"IT operations"),("Pending approvals",len(pending) if user.get("role") in {"admin","manager"} else "—","Human review")]
    for col,(label,value,hint) in zip(top,metrics):
        with col:
            st.metric(label,value,help=hint)

    left,center,right=st.columns([1.03,1.72,1.08],gap="medium")
    with left:
        with st.container(border=True):
            st.markdown("<p class='section-label'>My tasks</p><p class='card-title'>Priority watchlist</p><p class='card-caption'>Items surfaced from current operations</p>",unsafe_allow_html=True)
            tasks=[
                ("↗","Return performance",f"{e.get('returns',0)} returns across {e.get('orders',0)} orders","Review" if e.get("return_rate",0)>=15 else "On track",e.get("return_rate",0)>=15),
                ("!","Critical incidents",f"{it.get('critical_incidents',0)} active incidents","Priority" if it.get("critical_incidents",0) else "Clear",it.get("critical_incidents",0)>0),
                ("✓","Approval queue",f"{len(pending)} actions await review" if user.get("role") in {"admin","manager"} else "Manager review required","Review" if pending else "Clear",bool(pending)),
                ("▣","Customer feedback",f"{e.get('complaints',0)} complaints recorded","Monitor",bool(e.get("complaints",0))),
            ]
            for icon,name,detail,state,alert in tasks:
                st.markdown(f"<div class='task-row'><span class='task-dot'>{icon}</span><div><p class='task-name'>{escape(name)}</p><p class='task-detail'>{escape(detail)}</p></div><span class='task-state {'alert' if alert else ''}'>{escape(state)}</span></div>",unsafe_allow_html=True)
    with center:
        with st.container(border=True):
            st.markdown("<p class='section-label'>Business pulse</p><p class='card-title'>Customer and service trends</p><p class='card-caption'>Operational signals from the connected data</p>",unsafe_allow_html=True)
            chart(e.get("complaint_trends",[]),"month","complaints","Customer complaint trend",kind="line")
            mini=st.columns(2)
            with mini[0]:st.metric("Customer complaints",e.get("complaints",0))
            with mini[1]:st.metric("Critical incidents",it.get("critical_incidents",0))
        with st.container(border=True):
            st.markdown("<p class='section-label'>E-commerce</p><p class='card-title'>Product return overview</p>",unsafe_allow_html=True)
            chart(e.get("product_return_distribution",[])[:10],"product","return_rate","Return rate by product")
    with right:
        with st.container(border=True):
            st.markdown("<p class='section-label'>IT operations</p><p class='card-title'>Open tickets</p>",unsafe_allow_html=True)
            st.metric("Unresolved",it.get("open_tickets",0),delta=f"{it.get('critical_open_tickets',0)} critical",delta_color="inverse")
            severity=it.get("ticket_severity",[])
            if severity:chart(severity,"severity","count","Ticket severity",kind="pie")
            categories=it.get("categories",[])
            if categories:
                st.markdown("<p class='section-label'>Top categories</p>",unsafe_allow_html=True)
                for category in categories[:3]:
                    st.markdown(f"<div class='activity-row'><span class='task-dot'>▣</span><div><p class='activity-title'>{escape(str(category.get('category','Other')).title())}</p><p class='activity-detail'>{escape(str(category.get('count',0)))} tickets</p></div></div>",unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown("<p class='section-label'>Workspace</p><p class='card-title'>Recent activity</p>",unsafe_allow_html=True)
            if activity:
                for item in activity[:3]:
                    label=item.get("agent") or item.get("tool") or "Workflow"
                    detail=item.get("approval_decision") or item.get("tool") or "Workflow event"
                    st.markdown(f"<div class='activity-row'><span class='activity-avatar'>{escape(str(label)[:1].upper())}</span><div><p class='activity-title'>{escape(str(label).replace('_',' ').title())}</p><p class='activity-detail'>{escape(str(detail).replace('_',' ').title())}</p></div></div>",unsafe_allow_html=True)
            else:
                st.markdown("<p class='card-caption' style='padding:.75rem 0'>Your team’s workflow activity will appear here.</p>",unsafe_allow_html=True)
    left,right=st.columns(2,gap="medium")
    with left:
        with st.container(border=True):multi_line_chart(it.get("ticket_trends",[]),"month",["created","currently_resolved"],"Ticket and resolution trend")
    with right:
        with st.container(border=True):chart(it.get("categories",[]),"category","count","Ticket volume by category")
    if e.get("orders",0)==0:empty("No order records are available yet.")

def render_ecommerce():
    frame("E-commerce Intelligence","Explore products, customer feedback, returns, sellers, and inventory exposure.")
    metrics=call(api.get,"/api/analytics/ecommerce")
    if not metrics:return
    cols=st.columns(4)
    for col,(label,value) in zip(cols,[("Orders",metrics.get("orders",0)),("Returns",metrics.get("returns",0)),("Return rate",f"{metrics.get('return_rate',0)}%"),("Low stock products",metrics.get("low_inventory",0))]):col.metric(label,value)
    tab1,tab2,tab3=st.tabs(["Products and returns","Complaints","Sellers and inventory"])
    with tab1:
        search=st.text_input("Search products",placeholder="Enter product name")
        data=call(api.get,"/api/analytics/products",params={"q":search,"limit":100})
        if data and data.get("products"):
            df=pd.DataFrame(data["products"]);st.dataframe(df,use_container_width=True,hide_index=True)
            chart(sorted(data["products"],key=lambda x:x.get("return_rate",0),reverse=True)[:12],"name","return_rate","Products with highest return rate")
        else:empty("No products match this search.")
    with tab2:
        search=st.text_input("Search complaint text",key="complaint_search",placeholder="refund, damaged, late delivery...")
        data=call(api.get,"/api/analytics/complaints",params={"q":search,"limit":100})
        if data and data.get("complaints"):
            df=pd.DataFrame(data["complaints"]);st.dataframe(df,use_container_width=True,hide_index=True)
            chart(metrics.get("top_complaints",[]),"category","count","Complaint categories")
        else:empty("No complaints match this search.")
    with tab3:
        st.markdown("#### Seller performance")
        sellers=metrics.get("seller_performance",[])
        if sellers:st.dataframe(pd.DataFrame(sellers).sort_values(["return_rate","rating"],ascending=[False,True]),use_container_width=True,hide_index=True)
        else:empty("Seller performance data is unavailable.")
        st.markdown("#### Inventory risk")
        risks=metrics.get("inventory_risks",[])
        if risks:st.dataframe(pd.DataFrame(risks),use_container_width=True,hide_index=True)
        else:st.success("No products are currently below their reorder points.")
    st.divider();st.markdown("#### Ask the E-commerce Agent")
    question=st.text_input("Investigation question",placeholder="Which products have the highest return rates?")
    if st.button("Investigate e-commerce",type="primary",key="ecom_investigate"):
        if not question.strip():st.warning("Enter a question to investigate.")
        else:
            with st.spinner("Analyzing backend evidence and documents..."):
                result=call(api.post,"/api/ecommerce/investigate",{"query":question,"domain":"ecommerce"},timeout=300)
            if result:show_workflow(result)

def render_it():
    frame("IT Operations Intelligence","Prioritize incidents and investigate ticket patterns using operational records.")
    metrics=call(api.get,"/api/analytics/it")
    if not metrics:return
    cols=st.columns(4)
    for col,(label,value) in zip(cols,[("Open tickets",metrics.get("open_tickets",0)),("Critical incidents",metrics.get("critical_incidents",0)),("Critical open tickets",metrics.get("critical_open_tickets",0)),("Ticket categories",len(metrics.get("categories",[])))]):col.metric(label,value)
    left,right=st.columns(2)
    with left:chart(metrics.get("ticket_severity",[]),"severity","count","Ticket severity distribution",kind="pie")
    with right:multi_line_chart(metrics.get("ticket_trends",[]),"month",["created","currently_resolved"],"Ticket and resolution trend")
    if metrics.get("critical_open_tickets",0):st.error(f"{metrics['critical_open_tickets']} critical tickets are unresolved. Review them in Ticket Management.")
    st.markdown("#### Ticket categories")
    chart(metrics.get("categories",[]),"category","count","Current ticket categories")
    st.divider();st.markdown("#### Investigate IT operations")
    question=st.text_input("Investigation question",placeholder="Find recurring database connection problems")
    if st.button("Investigate IT",type="primary"):
        if not question.strip():st.warning("Enter a question to investigate.")
        else:
            with st.spinner("Searching IT tickets and runbooks..."):
                result=call(api.post,"/api/it/investigate",{"query":question,"domain":"it"},timeout=300)
            if result:show_workflow(result)

def render_chat():
    frame("AI Agent Chat","Ask Operlynt to investigate. The backend coordinates agents and returns observable actions and evidence.")
    domain=st.selectbox("Business domain",["ecommerce","it"],format_func=lambda x:"E-commerce" if x=="ecommerce" else "IT Operations")
    if "chat_messages" not in st.session_state:st.session_state.chat_messages=[]
    for message in st.session_state.chat_messages:
        with st.chat_message(message["role"]):
            if message.get("content"):st.markdown(message["content"])
            if message.get("result"):show_workflow(message["result"])
    prompt=st.chat_input("Ask about returns, complaints, tickets, incidents, or policies")
    if prompt:
        st.session_state.chat_messages.append({"role":"user","content":prompt})
        with st.chat_message("user"):st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Coordinating Operlynt agents..."):
                payload={"query":prompt,"domain":domain}
                if st.session_state.thread_id:payload["thread_id"]=st.session_state.thread_id
                result=call(api.post,"/api/chat",payload,timeout=300)
            if result:
                st.session_state.chat_messages.append({"role":"assistant","content":result.get("answer", ""),"result":result})
                show_workflow(result)

def render_rag():
    frame("RAG Document Intelligence","Upload policy/runbook files and ask questions grounded in indexed documents.")
    left,right=st.columns([1,1.4])
    with left:
        st.markdown("#### Upload a document")
        uploaded=st.file_uploader("PDF or TXT · up to 10 MB",type=["pdf","txt"])
        category=st.selectbox("Document category",["ecommerce_policy","it_documentation","historical_incidents","general"])
        if st.button("Upload and index",disabled=uploaded is None,type="primary"):
            with st.spinner("Uploading and indexing document..."):
                result=call(api.upload,"/api/rag/upload",uploaded,{"category":category},timeout=300)
            if result:st.success(f"Indexed {result.get('document_name',uploaded.name)} ({result.get('chunks',0)} chunks).")
    with right:
        st.markdown("#### Ask the document library")
        question=st.text_area("Question",placeholder="What is the return window for defective products?")
        domain=st.selectbox("Collection",["All documents","E-commerce policy","IT documentation","Historical incidents"],key="rag_domain")
        domain_value={"All documents":None,"E-commerce policy":"ecommerce","IT documentation":"it","Historical incidents":"historical_incidents"}[domain]
        if st.button("Ask documents",type="primary",key="ask_rag"):
            if not question.strip():st.warning("Enter a document question.")
            else:
                with st.spinner("Retrieving documents and preparing an answer..."):
                    result=call(api.post,"/api/rag/ask",{"question":question,"domain":domain_value,"top_k":4},timeout=300)
                if result:
                    st.markdown("#### Answer");st.write(result.get("answer","No answer returned."))
                    sources=result.get("sources",[])
                    if sources:
                        st.markdown("#### Retrieved sources")
                        for source in sources:st.write(source)
                    else:empty("No supporting sources were returned for this question.")
    st.divider();st.markdown("#### Indexed documents")
    docs=call(api.get,"/api/rag/documents")
    if docs and docs.get("documents"):st.dataframe(pd.DataFrame(docs["documents"]),use_container_width=True,hide_index=True)
    else:empty("No documents are indexed. Upload a policy or runbook to begin.")

def render_monitoring():
    frame("Agent Execution Monitoring","Audit events and execution results recorded by FastAPI.")
    rows=call(api.get,"/api/agents/activity")
    if not rows:empty("No activity has been recorded for this account yet.");return
    df=pd.DataFrame(rows)
    if "created_at" in df:df=df.sort_values("created_at",ascending=False)
    if "execution_result" in df:
        def _result_fields(value):
            try:return json.loads(value) if isinstance(value,str) else value or {}
            except (ValueError,TypeError):return {}
        parsed=df["execution_result"].map(_result_fields)
        df["duration_ms"]=parsed.map(lambda x:x.get("duration_ms") if isinstance(x,dict) else None)
        def _summary(value):
            if not isinstance(value,dict):return ""
            errors=value.get("errors",[])
            if errors:return ", ".join(str(item.get("agent",item.get("error","error"))) if isinstance(item,dict) else str(item) for item in errors)
            return value.get("status","")
        df["execution_summary"]=parsed.map(_summary)
        def _status(row):
            decision=row.get("approval_decision","")
            result=_result_fields(row.get("execution_result"))
            if decision in {"approved","rejected"}:return decision.title()
            if decision=="pending":return "Awaiting approval"
            if isinstance(result,dict) and result.get("errors"):return "Completed with errors"
            return "Completed"
        df["execution_status"]=df.apply(_status,axis=1)
    st.dataframe(df,use_container_width=True,hide_index=True)
    st.markdown("#### Inspect a workflow")
    workflow_ids=[x for x in df.get("workflow_id",pd.Series(dtype=str)).dropna().astype(str).tolist() if x and not x.startswith("approval:")]
    if workflow_ids:
        selected=st.selectbox("Workflow ID",list(dict.fromkeys(workflow_ids)))
        if st.button("Load workflow state"):
            detail=call(api.get,f"/api/workflows/{selected}/status")
            if detail:
                state=detail.get("state",{})
                st.markdown("**Final output**")
                st.write(state.get("final_response") or state.get("answer") or "No final output is stored for this workflow.")
                st.markdown("**Agent steps and tool calls**")
                st.json({"agents":state.get("agents",[]),"agent_results":state.get("agent_results",{}),"errors":state.get("errors",[])})
    st.markdown("#### Inspect an approval execution")
    execution_id=st.number_input("Approval / execution ID",min_value=1,step=1)
    if st.button("Load execution",key="load_execution"):
        result=call(api.get,f"/api/agents/executions/{int(execution_id)}")
        if result:st.json(result)
    st.caption("Workflow and execution details are sourced from API audit events and persisted backend state.")

def render_approvals():
    frame("Human Approval Center","Review pending operational changes before the Execution Agent can run them.")
    if user.get("role") not in {"admin","manager"}:st.warning("Manager or Admin access is required to review approvals.");return
    approvals=call(api.get,"/api/approvals")
    if approvals is None:return
    pending=[a for a in approvals if a.get("status")=="pending"]
    st.metric("Pending actions",len(pending))
    if not pending:empty("There are no pending actions.");return
    for item in pending:
        payload=item.get("payload") or {}
        with st.container(border=True):
            left,right=st.columns([4,1])
            with left:
                st.markdown(f"#### Approval #{item['id']} · {item.get('action','').replace('_',' ').title()}")
                st.write(item.get("request","Action requested by workflow"))
                st.caption(f"Requested {item.get('created_at','')} · Requesting agent: {payload.get('agent','workflow execution')}")
                st.json(payload)
            with right:
                risk="High" if payload.get("severity")=="critical" or "escalat" in item.get("action","") else "Review"
                st.metric("Risk",risk)
                if st.button("Approve",key=f"approve_{item['id']}",type="primary"):
                    with st.spinner("Approving and executing through the backend..."):
                        response=call(api.post,f"/api/approvals/{item['id']}/approve",{})
                    if response:st.success(f"Approval resolved: {response.get('status')}");st.rerun()
                if st.button("Reject",key=f"reject_{item['id']}"):
                    response=call(api.post,f"/api/approvals/{item['id']}/reject",{})
                    if response:st.success("Action rejected. No operation was executed.");st.rerun()

def render_tickets():
    frame("Ticket Management","Search, prioritize, and inspect live operational tickets.")
    rows=call(api.get,"/api/tickets")
    if rows is None:return
    df=pd.DataFrame(rows)
    if df.empty:empty("There are no tickets in the backend.")
    else:
        a,b,c=st.columns([2,1,1]);query=a.text_input("Search tickets",placeholder="Title or category");severity=b.selectbox("Priority",["All","critical","high","medium","low"]);status=c.selectbox("Status",["All","open","in_progress","resolved"])
        filtered=df.copy()
        if query:filtered=filtered[filtered.apply(lambda row:query.lower() in " ".join(map(str,row.values)).lower(),axis=1)]
        if severity!="All":filtered=filtered[filtered["severity"]==severity]
        if status!="All":filtered=filtered[filtered["status"]==status]
        st.dataframe(filtered,use_container_width=True,hide_index=True)
        if not filtered.empty:
            ticket_id=st.selectbox("Ticket details",filtered["id"].tolist())
            detail=call(api.get,f"/api/tickets/{ticket_id}")
            if detail:
                with st.expander("Selected ticket",expanded=True):st.json(detail)
                activity=call(api.get,"/api/agents/activity") or []
                events=[ev for ev in activity if str(ticket_id) in str(ev.get("action","")) or str(ticket_id) in str(ev.get("execution_result",""))]
                st.markdown("#### Ticket audit history")
                if events:st.dataframe(pd.DataFrame(events),use_container_width=True,hide_index=True)
                else:empty("No status change history is recorded for this ticket yet.")
    if user.get("role") in {"admin","manager"}:
        with st.expander("Request a new ticket (requires approval)"):
            with st.form("ticket_request"):
                title=st.text_input("Title");description=st.text_area("Description");category=st.text_input("Category",value="other");severity=st.selectbox("Severity",["low","medium","high","critical"])
                submit=st.form_submit_button("Submit for approval")
            if submit:
                response=call(api.post,"/api/tickets",{"title":title,"description":description,"category":category,"severity":severity})
                if response:st.success(f"Approval #{response['approval_id']} created.")

def render_settings():
    frame("Settings","Manage your account session and verify connected services.")
    st.write({"username":user.get("username"),"role":user.get("role"),"session":"JWT bearer","token_expiry":"Backend-enforced"})
    st.caption("Service connection is managed by the deployment configuration.")
    if st.button("Test backend connection"):
        with st.spinner("Checking service health..."):
            health=call(api.get,"/health")
            me=call(api.get,"/api/auth/me")
        if health and me:st.success(f"Connected. Service status: {health.get('status')} · Signed in as {me.get('username')} ({me.get('role')}).")
    st.info("The JWT is held in Streamlit session state and is not written to a file.")

PAGES_RENDERERS={"Overview Dashboard":render_overview,"E-commerce Intelligence":render_ecommerce,
    "IT Operations Intelligence":render_it,"AI Agent Chat":render_chat,"RAG Document Intelligence":render_rag,
    "Agent Execution Monitoring":render_monitoring,"Human Approval Center":render_approvals,
    "Ticket Management":render_tickets,"Settings":render_settings}
page=render_topbar()
try:
    with st.spinner("Loading workspace..."):
        PAGES_RENDERERS[page]()
    render_footer()
except Exception as exc:
    st.error("The workspace could not load this view.")
    st.caption(str(exc)[:300])

import streamlit as st
from streamlit_gsheets import GSheetsConnection
import yfinance as yf
import pandas as pd

# Configuração de Layout
st.set_page_config(page_title="Investidor Blindado v4.0", layout="wide")

# --- CONEXÃO E BLINDAGEM ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data():
    try:
        data = conn.read(ttl="0") 
        if data is None or data.empty:
            return pd.DataFrame(columns=['ticker', 'preco_compra', 'quantidade', 'categoria'])
        # Blindagem: Garante que colunas críticas sejam strings
        data['ticker'] = data['ticker'].astype(str)
        return data
    except:
        return pd.DataFrame(columns=['ticker', 'preco_compra', 'quantidade', 'categoria'])

def normalize_ticker(t):
    t = str(t).upper().strip()
    if not t: return "UNKNOWN"
    return t if t.endswith('.SA') else f"{t}.SA"

df = get_data()

# --- MENU LATERAL (NAVEGAÇÃO) ---
st.sidebar.title("📌 Menu Principal")
menu = st.sidebar.radio(
    "Selecione uma função:",
    ["🆕 Novo Aporte", "📊 Meu Dashboard", "🔎 Detalhes por Ativo", "📈 Sugestões de Alocação"]
)

# --- LÓGICA DE TELAS ---

if menu == "🆕 Novo Aporte":
    st.header("📝 Registrar Nova Compra")
    st.info("Insira os dados abaixo. O sistema categoriza e formata o Ticker automaticamente.")
    
    with st.form("form_aporte"):
        t_input = st.text_input("Ticker (Ex: VALE3)")
        p_input = st.number_input("Preço de Compra (R$)", min_value=0.0, step=0.01)
        q_input = st.number_input("Quantidade", min_value=1, step=1)
        
        if st.form_submit_button("💾 Salvar na Planilha"):
            ticker_ready = normalize_ticker(t_input)
            cat = "FII" if "11" in ticker_ready else "Ações"
            
            new_entry = pd.DataFrame([{
                "ticker": ticker_ready,
                "preco_compra": p_input,
                "quantidade": q_input,
                "categoria": cat
            }])
            
            updated_df = pd.concat([df, new_entry], ignore_index=True)
            conn.update(data=updated_df)
            st.success(f"Sucesso! {ticker_ready} adicionado à base de dados.")
            st.rerun()

elif menu == "📊 Meu Dashboard":
    st.header("📊 Visão Geral da Carteira")
    
    if not df.empty:
        # Consolidação Blindada
        resumo = df.groupby('ticker').agg({
            'preco_compra': 'mean',
            'quantidade': 'sum',
            'categoria': 'first'
        }).reset_index()
        
        # Puxar Preços Reais
        with st.spinner('Atualizando B3...'):
            resumo['Preço Atual'] = resumo['ticker'].apply(lambda x: yf.Ticker(x).fast_info.get('last_price', 0.0))
        
        resumo['Patrimônio'] = resumo['Preço Atual'] * resumo['quantidade']
        resumo['Lucro/Prejuízo'] = (resumo['Preço Atual'] - resumo['preco_compra']) * resumo['quantidade']
        
        col1, col2 = st.columns(2)
        col1.metric("Patrimônio Total", f"R$ {resumo['Patrimônio'].sum():,.2f}")
        col2.metric("Lucro Acumulado", f"R$ {resumo['Lucro/Prejuízo'].sum():,.2f}")
        
        st.subheader("📋 Meus Ativos")
        st.dataframe(resumo[['ticker', 'categoria', 'quantidade', 'preco_compra', 'Preço Atual', 'Patrimônio']], use_container_width=True)
    else:
        st.warning("Nenhum dado encontrado. Vá ao menu 'Novo Aporte'.")

elif menu == "🔎 Detalhes por Ativo":
    st.header("🔎 Análise Individual")
    
    if not df.empty:
        tickers = df['ticker'].unique()
        escolha = st.selectbox("Selecione o ativo para detalhar:", tickers)
        
        item = df[df['ticker'] == escolha]
        # Cálculo de preço médio ponderado para o item escolhido
        p_medio = (item['preco_compra'] * item['quantidade']).sum() / item['quantidade'].sum()
        qtd_total = item['quantidade'].sum()
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Preço Médio", f"R$ {p_medio:.2f}")
        c2.metric("Total de Cotas", int(qtd_total))
        c3.write(f"**Categoria:** {item['categoria'].iloc[0]}")
        
        st.divider()
        st.write("### Histórico de Compras deste papel")
        st.table(item[['preco_compra', 'quantidade']])
    else:
        st.info("Carteira vazia.")

elif menu == "📈 Sugestões de Alocação":
    st.header("🎯 Inteligência de Rebalanceamento")
    
    if not df.empty:
        resumo = df.groupby('ticker').agg({'preco_compra': 'mean', 'quantidade': 'sum'}).reset_index()
        resumo['Preço Atual'] = resumo['ticker'].apply(lambda x: yf.Ticker(x).fast_info.get('last_price', 0.0))
        resumo['Patrimônio'] = resumo['Preço Atual'] * resumo['quantidade']
        
        # Gráfico
        st.subheader("Distribuição Atual")
        st.bar_chart(resumo.set_index('ticker')['Patrimônio'])
        
        # Lógica de Sugestão
        total = resumo['Patrimônio'].sum()
        meta = 1 / len(resumo)
        
        st.subheader("💡 O que fazer agora?")
        for _, row in resumo.iterrows():
            pos_atual = row['Patrimônio'] / total
            if pos_atual < meta:
                st.success(f"✅ **APORTAR EM {row['ticker']}**: Está abaixo da sua média ideal. Foco aqui para equilibrar.")
            else:
                st.warning(f"⚠️ **AGUARDAR {row['ticker']}**: Já representa uma parte grande da carteira.")
    else:
        st.info("Adicione ativos para ver as sugestões.")
import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime

# --- CONFIGURAÇÃO DE ACESSO (SUBSTITUA PELO SEU ID) ---
# Dica: No Streamlit Cloud, use st.secrets para maior segurança
SHEET_ID = "COLE_AQUI_O_ID_DA_SUA_PLANILHA"
SHEET_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv"

def normalize_data(raw_data):
    """Blindagem: Garante dicionário, IDs como String e tratamento de nulos."""
    if not isinstance(raw_data, dict):
        raw_data = {}
    
    normalized = {
        'ticker': str(raw_data.get('ticker', 'UNKNOWN')).upper().strip(),
        'preco': float(raw_data.get('preco', 0.0)),
        'qtd': int(raw_data.get('qtd', 0)),
        'data': str(raw_data.get('data', datetime.now().strftime('%Y-%m-%d')))
    }
    
    if not normalized['ticker'].endswith('.SA') and normalized['ticker'] != 'UNKNOWN':
        normalized['ticker'] += '.SA'
    
    return normalized

def load_data_from_sheets():
    try:
        # Lê a planilha via URL de exportação CSV
        return pd.read_csv(SHEET_URL)
    except Exception:
        return pd.DataFrame(columns=['ticker', 'preco_compra', 'quantidade', 'data', 'categoria'])

def get_live_data(ticker):
    """Busca dados reais da B3 com tratamento de erros."""
    try:
        paper = yf.Ticker(ticker)
        info = paper.info
        current_price = info.get('regularMarketPrice') or info.get('currentPrice') or 0.0
        dividendos = paper.dividends.sum() if not paper.dividends.empty else 0.0
        return float(current_price), float(dividendos)
    except:
        return 0.0, 0.0

# --- INTERFACE ---
st.set_page_config(page_title="Investidor Blindado v2.0", layout="wide")
st.title("🚀 Web App de Investimentos (Dados Permanentes)")

# Sidebar
st.sidebar.header("Novo Aporte")
with st.sidebar.form("input_form"):
    t_input = st.text_input("Ticker (ex: ITUB4)")
    p_input = st.number_input("Preço de Compra", min_value=0.01)
    q_input = st.number_input("Quantidade", min_value=1)
    d_input = st.date_input("Data da Compra")
    submit = st.form_submit_button("Salvar na Nuvem")

if submit:
    clean = normalize_data({'ticker': t_input, 'preco': p_input, 'qtd': q_input, 'data': d_input})
    categoria = "FII" if "11" in clean['ticker'] else "Ações"
    
    # IMPORTANTE: Para escrever no Google Sheets via Web App de forma simples, 
    # o ideal é usar a biblioteca 'gspread'. 
    # Para este exemplo manter a simplicidade, ele exibirá o link para você colar o dado
    # ou podemos implementar o gspread se você tiver a chave JSON do Google.
    st.sidebar.warning("Integração de escrita requer chave de API (Gspread).")
    st.sidebar.write(f"Dado formatado: `{clean['ticker']}, {clean['preco']}, {clean['qtd']}, {categoria}`")

# --- PROCESSAMENTO ---
df = load_data_from_sheets()

if not df.empty:
    # Lógica de agrupamento e cálculos (idêntica à anterior)
    carteira = df.groupby('ticker').agg({
        'preco_compra': 'mean',
        'quantidade': 'sum',
        'categoria': 'first'
    }).reset_index()

    # Preços em tempo real
    with st.spinner('Atualizando cotações da B3...'):
        carteira[['Preço Atual', 'Dividendos']] = carteira['ticker'].apply(
            lambda x: pd.Series(get_live_data(x))
        )
    
    carteira['Patrimônio'] = carteira['Preço Atual'] * carteira['quantidade']
    carteira['ROI'] = (carteira['Preço Atual'] - carteira['preco_compra']) * carteira['quantidade']

    # Tabs
    tab1, tab2 = st.tabs(["Dashboard", "Alocação Sugerida"])
    
    with tab1:
        st.metric("Patrimônio Total", f"R$ {carteira['Patrimônio'].sum():,.2f}")
        st.dataframe(carteira, use_container_width=True)
        
    with tab2:
        st.subheader("Análise de Rebalanceamento")
        total = carteira['Patrimônio'].sum()
        ideal = 1 / len(carteira)
        
        for i, row in carteira.iterrows():
            perc_atual = row['Patrimônio'] / total
            dif = (ideal - perc_atual) * 100
            if dif > 0:
                st.success(f"**{row['ticker']}**: Aportar para atingir meta (Faltam {dif:.1f}%)")
            else:
                st.error(f"**{row['ticker']}**: Acima da meta (Excesso de {-dif:.1f}%)")
else:
    st.info("Aguardando dados da Planilha Google...")
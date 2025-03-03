import streamlit as st
import pandas as pd
import plotly.express as px

# Configuração de página
st.set_page_config(page_title="Dashboard Contábil", layout="wide")

# Função para converter DataFrame para CSV
def convert_df(df):
    return df.to_csv(index=False).encode('utf-8')

# Função para formatar valores em real brasileiro
def formata_valor_brasil(valor):
    if pd.isnull(valor):
        return ""
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# ---------------------------
# Melhorias no CSS para Dark Mode Suave
# ---------------------------
st.markdown("""
    <style>
    body {
        background-color: #1E1E1E;
        color: #FFFFFF;
        font-family: 'Arial', sans-serif;
    }
    
    .stSidebar {
        background-color: #252526;
        color: #FFFFFF;
    }

    div[data-baseweb="datepicker"], div[data-baseweb="input"] {
        background-color: #2D2D2D !important;
        color: #FFFFFF !important;
        border: 1px solid #FFFFFF !important;
        border-radius: 8px !important;
        padding: 8px !important;
    }

    div[data-baseweb="datepicker"]:hover, div[data-baseweb="input"]:hover {
        border-color: #FFD700 !important;
    }
    </style>
""", unsafe_allow_html=True)

# ------------------------------------
# Barra lateral para Upload de Arquivo
# ------------------------------------
st.sidebar.title("⚙️ Configurações")

uploaded_file = st.sidebar.file_uploader("📥 Importar arquivo Excel", type=["xlsx"])

if uploaded_file is not None:
    with st.spinner("Carregando arquivo..."):
        df = pd.read_excel(uploaded_file)
        st.session_state['df'] = df
    st.sidebar.success("Arquivo carregado com sucesso.")
elif 'df' in st.session_state:
    df = st.session_state['df']
else:
    df = None
    st.sidebar.warning("Por favor, faça o upload de um arquivo Excel para começar.")

# ------------------------------------
# Execução do Dashboard se houver dados
# ------------------------------------
if df is not None:
    df['Data'] = pd.to_datetime(df['Data'], dayfirst=True, errors='coerce')
    df['Valor'] = pd.to_numeric(df['Valor'], errors='coerce')

    min_date, max_date = df['Data'].min(), df['Data'].max()
    selected_dates = st.sidebar.date_input("📅 Intervalo de Datas:", [min_date, max_date])
    
    if isinstance(selected_dates, list) and len(selected_dates) == 2:
        start_date, end_date = selected_dates
        df = df[(df['Data'] >= pd.to_datetime(start_date)) & (df['Data'] <= pd.to_datetime(end_date))]

    if 'GrupoDeConta' in df.columns:
        grupo_selecionado = st.sidebar.selectbox("🗂️ Grupo de Conta:", ["Todos"] + list(df['GrupoDeConta'].dropna().unique()))
        if grupo_selecionado != "Todos":
            df = df[df['GrupoDeConta'] == grupo_selecionado]

    filtro_conta = st.sidebar.text_input("🔍 Conta Contábil:")
    if filtro_conta:
        df = df[df['ContaContabil'].str.contains(filtro_conta, case=False, na=False)]

    st.title("📊 Dashboard Contábil")
    st.markdown("---")

    total_entradas = df[df['Valor'] > 0]['Valor'].sum()
    total_saidas = df[df['Valor'] < 0]['Valor'].sum()
    saldo = total_entradas + total_saidas

    col1, col2, col3 = st.columns(3)
    col1.metric("💰 Entradas", formata_valor_brasil(total_entradas), delta=total_entradas)
    col2.metric("📉 Saídas", formata_valor_brasil(abs(total_saidas)), delta=-abs(total_saidas))
    col3.metric("📊 Saldo", formata_valor_brasil(saldo))

    st.subheader("🔎 Análise de Valores por Conta")
    df_positivo = df[df['Valor'] > 0].groupby('ContaContabil')['Valor'].sum().reset_index()
    
    if not df_positivo.empty:
        fig = px.bar(df_positivo, x="ContaContabil", y="Valor", 
                     title="Entradas por Conta Contábil", template="plotly_dark",
                     color_discrete_sequence=["#FFD700"], height=400)
        fig.update_layout(font=dict(size=14, color="#FFFFFF"))
        fig.update_yaxes(tickprefix="R$ ", tickformat=",.2f")
        st.plotly_chart(fig, use_container_width=True)
    
    st.subheader("📉 Saídas por Conta")
    df_negativo = df[df['Valor'] < 0]
    
    if not df_negativo.empty:
        df_negativo_agrupado = df_negativo.groupby('ContaContabil')['Valor'].sum().abs().reset_index()
        fig2 = px.bar(df_negativo_agrupado, x="ContaContabil", y="Valor", 
                      title="Saídas por Conta Contábil", template="plotly_dark",
                      color_discrete_sequence=["#FF6347"], height=400)
        fig2.update_layout(font=dict(size=14, color="#FFFFFF"))
        fig2.update_yaxes(tickprefix="R$ ", tickformat=",.2f")
        st.plotly_chart(fig2, use_container_width=True)

    st.subheader("💾 Exportar Dados")
    csv_data = convert_df(df)
    st.download_button(label="📥 Baixar Dados CSV", data=csv_data,
                       file_name="dados_exportados.csv", mime="text/csv")
else:
    st.info("⚠️ Nenhum arquivo carregado ainda.")

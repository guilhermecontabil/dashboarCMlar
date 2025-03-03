import streamlit as st
import pandas as pd
import plotly.express as px

# Configuração da página
st.set_page_config(page_title="Dashboard Contábil", layout="wide")

def convert_df(df):
    return df.to_csv(index=False).encode('utf-8')

def formata_valor_brasil(valor):
    if pd.isnull(valor):
        return ""
    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# CSS Global para a dashboard (fundo dark, texto branco, etc.)
st.markdown("""
    <style>
    /* ================================
       CSS Global
       ================================ */
    html, body, [data-testid="stAppViewContainer"] {
        background-color: #1e1e1e !important;
        color: #FFFFFF !important;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    /* Garante texto branco para todos os elementos, salvo onde for sobrescrito */
    html, body, [data-testid="stAppViewContainer"] * {
        color: #FFFFFF !important;
    }
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #232323 !important;
    }
    [data-testid="stSidebar"] .css-1d391kg {
        color: #FFFFFF !important;
        font-weight: bold !important;
    }
    /* Inputs e Date Input */
    input, .stTextInput, .stDateInput {
        background-color: #2d2d2d !important;
        border: 1px solid #FFFFFF !important;
        color: #FFFFFF !important;
    }
    input::placeholder {
        color: #BBBBBB !important;
    }
    div[data-baseweb="datepicker"] {
        background-color: #2d2d2d !important;
        color: #FFFFFF !important;
        border: 1px solid #FFFFFF !important;
        border-radius: 5px !important;
        padding: 5px;
    }
    div[data-baseweb="datepicker"] input {
        background-color: #2d2d2d !important;
        color: #FFFFFF !important;
        border: 1px solid #FFFFFF !important;
    }
    /* Botões e Métricas */
    .stButton > button {
        background-color: #FFFFFF !important;
        color: #000000 !important;
        border-radius: 8px !important;
        font-weight: bold !important;
        border: none !important;
        transition: transform 0.2s;
    }
    .stButton > button:hover {
        transform: scale(1.03);
    }
    .stMetric-label, .stMetric-value {
        font-weight: bold !important;
    }
    .stMetric-value {
        font-size: 1.5rem !important;
    }
    hr {
        border: 1px solid #FFFFFF;
    }
    
    /* Notificações (st.warning, st.info, etc.) */
    div[data-testid="stNotificationItem"] {
        background-color: #000000 !important;
        color: #FFFFFF !important;
        border: 1px solid #FFFFFF !important;
        border-radius: 5px !important;
        padding: 10px !important;
    }
    </style>
""", unsafe_allow_html=True)

# CSS específico para o file uploader: altera o texto para verde neon (#00FF7F)
# Esse bloco é injetado depois do CSS global para sobrepor o estilo global somente na área do file uploader.
st.markdown("""
    <style>
    /* Força o texto do file uploader para verde neon */
    [data-testid="stFileUploader"] * {
        color: #00FF7F !important;
    }
    [data-testid="stFileUploadDropzone"] * {
        color: #00FF7F !important;
    }
    [data-testid="stFileUploadLabel"] * {
        color: #00FF7F !important;
    }
    [data-testid="stFileUploadInstructions"] * {
        color: #00FF7F !important;
    }
    </style>
""", unsafe_allow_html=True)

# ------------------------------------
# BARRA LATERAL: UPLOAD DE ARQUIVO E FILTROS
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
# EXECUÇÃO DO DASHBOARD (SE HOUVER DF)
# ------------------------------------
if df is not None:
    df['Data'] = pd.to_datetime(df['Data'], dayfirst=True, errors='coerce')
    df['Valor'] = pd.to_numeric(df['Valor'], errors='coerce')
    
    # Filtros na barra lateral
    min_date = df['Data'].min()
    max_date = df['Data'].max()
    selected_dates = st.sidebar.date_input("Selecione o intervalo de datas:", [min_date, max_date])
    if isinstance(selected_dates, list) and len(selected_dates) == 2:
        start_date, end_date = selected_dates
        df = df[(df['Data'] >= pd.to_datetime(start_date)) & (df['Data'] <= pd.to_datetime(end_date))]
    
    if 'GrupoDeConta' in df.columns:
        grupos_unicos = df['GrupoDeConta'].dropna().unique()
        grupo_selecionado = st.sidebar.selectbox("🗂️ Filtrar por Grupo de Conta:", ["Todos"] + list(grupos_unicos))
        if grupo_selecionado != "Todos":
            df = df[df['GrupoDeConta'] == grupo_selecionado]
    
    filtro_conta = st.sidebar.text_input("🔍 Filtrar Conta Contábil:")
    if filtro_conta:
        df = df[df['ContaContabil'].str.contains(filtro_conta, case=False, na=False)]
    
    # Cabeçalho e Métricas
    st.title("Dashboard Contábil")
    st.markdown("---")
    
    total_entradas = df[df['Valor'] > 0]['Valor'].sum()
    total_saidas = df[df['Valor'] < 0]['Valor'].sum()
    saldo = total_entradas + total_saidas
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Entradas (R$)", formata_valor_brasil(total_entradas))
    col2.metric("Saídas (R$)", formata_valor_brasil(abs(total_saidas)))
    col3.metric("Saldo (R$)", formata_valor_brasil(saldo))
    
    # Abas da dashboard
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Resumo", "📄 Dados", "📈 Gráficos", "💾 Exportação"])
    
    # Aba Resumo
    with tab1:
        st.markdown("<h2 style='color:#00FF7F;'>Resumo por Conta Contábil</h2>", unsafe_allow_html=True)
        df['Mês/Ano'] = df['Data'].dt.to_period('M').astype(str)
        resumo = df.groupby(['ContaContabil', 'Mês/Ano'])['Valor'].sum().reset_index()
        resumo_pivot = resumo.pivot(index='ContaContabil', columns='Mês/Ano', values='Valor').fillna(0)
        resumo_pivot['Total'] = resumo_pivot.sum(axis=1)
        resumo_pivot.sort_values(by='Total', ascending=False, inplace=True)
        resumo_pivot_styled = (
            resumo_pivot
            .style
            .set_table_styles([
                {'selector': 'thead tr th',
                 'props': [('background-color', '#2d2d2d'),
                           ('color', '#00FF7F'),
                           ('font-weight', 'bold')]},
                {'selector': 'tbody tr th',
                 'props': [('background-color', '#2d2d2d'),
                           ('color', '#00FF7F'),
                           ('font-weight', 'bold')]},
                {'selector': 'tbody tr td',
                 'props': [('background-color', '#2d2d2d'),
                           ('color', '#FFFFFF')]}
            ])
            .format(lambda x: formata_valor_brasil(x))
        )
        st.table(resumo_pivot_styled)
    
    # Aba Dados
    with tab2:
        st.markdown("<h2 style='color:#00FF7F;'>Dados Importados</h2>", unsafe_allow_html=True)
        df_sorted = df.sort_values(by='Valor', ascending=False)
        df_sorted_styled = (
            df_sorted
            .style
            .set_table_styles([
                {'selector': 'thead tr th',
                 'props': [('background-color', '#2d2d2d'),
                           ('color', '#00FF7F'),
                           ('font-weight', 'bold')]},
                {'selector': 'tbody tr th',
                 'props': [('background-color', '#2d2d2d'),
                           ('color', '#00FF7F'),
                           ('font-weight', 'bold')]},
                {'selector': 'tbody tr td',
                 'props': [('background-color', '#2d2d2d'),
                           ('color', '#FFFFFF')]}
            ])
            .format({'Valor': lambda x: formata_valor_brasil(x)})
        )
        st.table(df_sorted_styled)
    
    # Aba Gráficos
    with tab3:
        st.subheader("Entradas (Valores Positivos)")
        df_positivo = df[df['Valor'] > 0]
        if not df_positivo.empty:
            df_positivo_agrupado = df_positivo.groupby('ContaContabil')['Valor'].sum().reset_index()
            fig = px.bar(df_positivo_agrupado, x="ContaContabil", y="Valor", 
                         title="Entradas por Conta Contábil", template="plotly_dark")
            fig.update_layout(font=dict(color="#FFFFFF", family="Segoe UI", size=12))
            fig.update_yaxes(tickprefix="R$ ", tickformat=",.2f")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.write("Nenhuma entrada para exibir.")
    
        st.subheader("Saídas (Valores Negativos)")
        df_negativo = df[df['Valor'] < 0]
        if not df_negativo.empty:
            df_negativo_agrupado = df_negativo.groupby('ContaContabil')['Valor'].sum().abs().reset_index()
            top_5 = df_negativo_agrupado.nlargest(5, 'Valor')
            fig2 = px.bar(top_5, y="ContaContabil", x="Valor", orientation='h',
                          title="Top 5 Categorias de Saídas", template="plotly_dark",
                          color_discrete_sequence=["#ff1493"])
            fig2.update_layout(font=dict(color="#FFFFFF", family="Segoe UI", size=12))
            fig2.update_xaxes(tickprefix="R$ ", tickformat=",.2f")
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.write("Nenhuma saída para exibir.")
    
        st.subheader("Entradas x Saídas (por Mês/Ano)")
        df_entradas_mensal = df[df['Valor'] > 0].groupby('Mês/Ano')['Valor'].sum().reset_index()
        df_saidas_mensal = df[df['Valor'] < 0].groupby('Mês/Ano')['Valor'].sum().reset_index()
        df_saidas_mensal['Valor'] = df_saidas_mensal['Valor'].abs()
        df_entradas_mensal['Tipo'] = 'Entradas'
        df_saidas_mensal['Tipo'] = 'Saídas'
        df_dre = pd.concat([df_entradas_mensal, df_saidas_mensal], axis=0)
        if not df_dre.empty:
            fig3 = px.bar(df_dre, x="Mês/Ano", y="Valor", color="Tipo", barmode="group",
                          title="Entradas x Saídas (por Mês/Ano)", template="plotly_dark")
            fig3.update_yaxes(tickprefix="R$ ", tickformat=",.2f")
            fig3.update_layout(font=dict(color="#FFFFFF", family="Segoe UI", size=12))
            st.plotly_chart(fig3, use_container_width=True)
        else:
            st.write("Dados insuficientes para exibir o gráfico de Entradas x Saídas.")
    
        st.subheader("Comparação: (Receita Vendas ML + SH) vs (Impostos - DAS Simples Nacional)")
        df_receitas = df[df['ContaContabil'].isin(['Receita Vendas ML', 'Receita Vendas SH'])]
        df_receitas_mensal = df_receitas.groupby('Mês/Ano')['Valor'].sum().reset_index()
        df_receitas_mensal.rename(columns={'Valor': 'Receitas'}, inplace=True)
        df_impostos = df[df['ContaContabil'] == 'Impostos - DAS Simples Nacional'].copy()
        df_impostos['Valor'] = df_impostos['Valor'].abs()
        df_impostos_mensal = df_impostos.groupby('Mês/Ano')['Valor'].sum().reset_index()
        df_impostos_mensal.rename(columns={'Valor': 'Impostos'}, inplace=True)
        df_comparacao = pd.merge(df_receitas_mensal, df_impostos_mensal, on='Mês/Ano', how='outer').fillna(0)
        if not df_comparacao.empty:
            df_comp_melt = df_comparacao.melt(id_vars="Mês/Ano", value_vars=["Receitas", "Impostos"],
                                              var_name="Tipo", value_name="Valor")
            fig4 = px.bar(df_comp_melt, x="Mês/Ano", y="Valor", color="Tipo", barmode="group",
                          title="(Receita Vendas ML + SH) vs (Impostos - DAS Simples Nacional)", template="plotly_dark")
            fig4.update_yaxes(tickprefix="R$ ", tickformat=",.2f")
            fig4.update_layout(font=dict(color="#FFFFFF", family="Segoe UI", size=12))
            st.plotly_chart(fig4, use_container_width=True)
        else:
            st.write("Dados insuficientes para a comparação.")
    
    # Aba Exportação
    with tab4:
        st.subheader("Exportar Resumo")
        resumo2 = df.groupby(['ContaContabil', 'Mês/Ano'])['Valor'].sum().reset_index()
        resumo_pivot2 = resumo2.pivot(index='ContaContabil', columns='Mês/Ano', values='Valor').fillna(0)
        resumo_pivot2['Total'] = resumo_pivot2.sum(axis=1)
        resumo_pivot2.sort_values(by='Total', ascending=False, inplace=True)
        csv_data = convert_df(resumo_pivot2)
        st.download_button(label="💾 Exportar Resumo para CSV", data=csv_data,
                           file_name="Resumo_ContaContabil.csv", mime="text/csv")
else:
    st.warning("Por favor, faça o upload de um arquivo Excel para começar.")

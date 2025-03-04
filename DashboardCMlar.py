import streamlit as st
import pandas as pd
import plotly.express as px

# ------------------------------------
# 1) CONFIGURAÇÕES E ESTILO
# ------------------------------------
st.set_page_config(page_title="Dashboard Contábil", layout="wide")

def convert_df(df):
    return df.to_csv(index=False).encode('utf-8')

def formata_valor_brasil(valor):
    if pd.isnull(valor):
        return ""
    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# CSS Global: Muda a cor do texto para terracota (#E2725B), mantendo o fundo atual
st.markdown("""
    <style>
    /* Define que todo o texto da aplicação ficará em terracota */
    html, body, [data-testid="stAppViewContainer"] * {
        color: #E2725B !important;
    }
    /* Mantém o fundo atual e define a fonte */
    html, body, [data-testid="stAppViewContainer"], .main, .block-container {
        background-color: #2C3E50 !important;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    /* Títulos em terracota */
    h1, h2, h3, h4, h5, h6 {
        color: #E2725B !important;
    }
    /* Métricas */
    .stMetric-label {
        font-weight: bold !important;
        color: #E2725B !important;
    }
    .stMetric-value {
        font-size: 1.5rem !important;
        color: #E2725B !important;
    }
    /* Botões: texto em terracota, fundo permanece */
    .stButton > button {
        background-color: #1ABC9C !important;
        color: #E2725B !important;
        border-radius: 8px !important;
        font-weight: bold !important;
        border: none !important;
        transition: transform 0.2s, box-shadow 0.2s;
        box-shadow: 0 4px 6px rgba(0,0,0,0.2);
    }
    .stButton > button:hover {
        transform: scale(1.05);
        box-shadow: 0 6px 8px rgba(0,0,0,0.3);
    }
    /* Sidebar: texto em terracota */
    [data-testid="stSidebar"] {
        background-color: #34495E !important;
    }
    [data-testid="stSidebar"] .css-1d391kg {
        color: #E2725B !important;
        font-weight: bold !important;
    }
    /* Inputs e sliders: texto em terracota */
    input, .st-bj, .st-at, .stTextInput, .stDateInput {
        background-color: #3A4F63 !important;
        border: 1px solid #1ABC9C !important;
        color: #E2725B !important;
    }
    /* File uploader: fundo branco e texto em terracota */
    [data-testid="stFileUploadDropzone"] {
        background-color: #FFFFFF !important;
        border: 1px dashed #1ABC9C !important;
        border-radius: 6px !important;
    }
    [data-testid="stFileUploadDropzone"] * {
        color: #E2725B !important;
        font-weight: 500;
    }
    /* Separador */
    hr {
        border: 1px solid #1ABC9C;
    }
    /* Footer */
    .custom-footer {
        position: fixed;
        bottom: 10px;
        width: 100%;
        text-align: center;
        color: #7F8C8D;
        font-size: 0.8rem;
    }
    </style>
""", unsafe_allow_html=True)

# ------------------------------------
# 2) BARRA LATERAL: UPLOAD E FILTROS
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
# 3) EXECUÇÃO DO DASHBOARD (SE HOUVER DF)
# ------------------------------------
if df is not None:
    # Conversões de tipo
    df['Data'] = pd.to_datetime(df['Data'], dayfirst=True, errors='coerce')
    df['Valor'] = pd.to_numeric(df['Valor'], errors='coerce')
    
    # FILTROS: Intervalo de datas
    min_date = df['Data'].min()
    max_date = df['Data'].max()
    selected_dates = st.sidebar.date_input("Selecione o intervalo de datas:", [min_date, max_date])
    if isinstance(selected_dates, list) and len(selected_dates) == 2:
        start_date, end_date = selected_dates
        df = df[(df['Data'] >= pd.to_datetime(start_date)) & (df['Data'] <= pd.to_datetime(end_date))]
    
    # Filtro: Grupo de Conta
    if 'GrupoDeConta' in df.columns:
        grupos_unicos = df['GrupoDeConta'].dropna().unique()
        grupo_selecionado = st.sidebar.selectbox("🗂️ Filtrar por Grupo de Conta:", ["Todos"] + list(grupos_unicos))
        if grupo_selecionado != "Todos":
            df = df[df['GrupoDeConta'] == grupo_selecionado]
    
    # Filtro: Conta Contábil
    filtro_conta = st.sidebar.text_input("🔍 Filtrar Conta Contábil:")
    if filtro_conta:
        df = df[df['ContaContabil'].str.contains(filtro_conta, case=False, na=False)]
    
    # CABEÇALHO E MÉTRICAS
    st.title("Dashboard Contábil")
    st.markdown("<hr>", unsafe_allow_html=True)
    
    total_entradas = df[df['Valor'] > 0]['Valor'].sum()
    total_saidas = df[df['Valor'] < 0]['Valor'].sum()
    saldo = total_entradas + total_saidas
    total_compras_revenda = df[df['ContaContabil'] == 'Compras de Mercadoria para Revenda']['Valor'].sum()
    total_das = df[df['ContaContabil'] == 'Impostos - DAS Simples Nacional']['Valor'].sum()
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Entradas (R$) 💵", formata_valor_brasil(total_entradas))
    col2.metric("Saídas (R$) 💸", formata_valor_brasil(abs(total_saidas)))
    col3.metric("Saldo (R$) 💰", formata_valor_brasil(saldo))
    
    col4, col5 = st.columns(2)
    col4.metric("Compras de Mercadoria 🛒", formata_valor_brasil(total_compras_revenda))
    col5.metric("Impostos (DAS) 🧾", formata_valor_brasil(total_das))
    
    # ------------------------------------
    # 4) ABAS DO DASHBOARD
    # ------------------------------------
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Resumo", "📄 Dados", "📈 Gráficos", "💾 Exportação"])
    
    # ABA 1: Resumo
    with tab1:
        st.markdown("<h2>Resumo por Conta Contábil</h2>", unsafe_allow_html=True)
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
                 'props': [('background-color', '#2C3E50'),
                           ('color', '#E2725B'),
                           ('font-weight', 'bold')]},
                {'selector': 'tbody tr th',
                 'props': [('background-color', '#2C3E50'),
                           ('color', '#E2725B'),
                           ('font-weight', 'bold')]},
                {'selector': 'tbody tr td',
                 'props': [('background-color', '#2C3E50'),
                           ('color', '#E2725B')]}
            ])
            .format(lambda x: formata_valor_brasil(x))
        )
        st.table(resumo_pivot_styled)
    
    # ABA 2: Dados
    with tab2:
        st.markdown("<h2>Dados Importados</h2>", unsafe_allow_html=True)
        df_sorted = df.sort_values(by='Valor', ascending=False)
        df_sorted_styled = (
            df_sorted
            .style
            .set_table_styles([
                {'selector': 'thead tr th',
                 'props': [('background-color', '#2C3E50'),
                           ('color', '#E2725B'),
                           ('font-weight', 'bold')]},
                {'selector': 'tbody tr th',
                 'props': [('background-color', '#2C3E50'),
                           ('color', '#E2725B'),
                           ('font-weight', 'bold')]},
                {'selector': 'tbody tr td',
                 'props': [('background-color', '#2C3E50'),
                           ('color', '#E2725B')]}
            ])
            .format({'Valor': lambda x: formata_valor_brasil(x)})
        )
        st.table(df_sorted_styled)
    
    # ABA 3: Gráficos
    with tab3:
        st.subheader("Entradas (Valores Positivos)")
        df_positivo = df[df['Valor'] > 0]
        df_positivo_agrupado = df_positivo.groupby('ContaContabil')['Valor'].sum().reset_index()
        if not df_positivo_agrupado.empty:
            fig_entradas = px.bar(
                df_positivo_agrupado,
                x='ContaContabil',
                y='Valor',
                color='ContaContabil',
                title='Entradas por Conta Contábil',
                labels={'Valor': 'Valor (R$)'},
                template='plotly_dark',
                color_discrete_sequence=px.colors.qualitative.Vivid
            )
            fig_entradas.update_layout(
                xaxis_tickangle=-45,
                showlegend=False,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#E2725B')
            )
            fig_entradas.update_yaxes(tickprefix="R$ ", tickformat=",.2f")
            st.plotly_chart(fig_entradas, use_container_width=True)
        else:
            st.write("Não há valores positivos para exibir.")
    
        st.subheader("Saídas (Valores Negativos)")
        df_negativo = df[df['Valor'] < 0]
        df_negativo_agrupado = df_negativo.groupby('ContaContabil')['Valor'].sum().abs().reset_index()
        if not df_negativo_agrupado.empty:
            top_5_saidas = df_negativo_agrupado.nlargest(5, 'Valor')
            fig_saidas = px.bar(
                top_5_saidas,
                y='ContaContabil',
                x='Valor',
                orientation='h',
                title='Top 5 Categorias de Saídas',
                labels={'Valor': 'Valor (R$)', 'ContaContabil': 'Conta Contábil'},
                template='plotly_dark',
                color_discrete_sequence=['#E74C3C']
            )
            fig_saidas.update_layout(
                yaxis={'categoryorder': 'total ascending'},
                showlegend=False,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#E2725B')
            )
            fig_saidas.update_xaxes(tickprefix="R$ ", tickformat=",.2f")
            st.plotly_chart(fig_saidas, use_container_width=True)
        else:
            st.write("Não há valores negativos para exibir.")
    
        st.subheader("Entradas x Saídas (por Mês/Ano)")
        df_entradas_mensal = df[df['Valor'] > 0].groupby('Mês/Ano')['Valor'].sum().reset_index()
        df_saidas_mensal = df[df['Valor'] < 0].groupby('Mês/Ano')['Valor'].sum().reset_index()
        df_saidas_mensal['Valor'] = df_saidas_mensal['Valor'].abs()
        df_entradas_mensal['Tipo'] = 'Entradas'
        df_saidas_mensal['Tipo'] = 'Saídas'
        df_dre = pd.concat([df_entradas_mensal, df_saidas_mensal], axis=0)
        if not df_dre.empty:
            fig_dre = px.bar(
                df_dre,
                x='Mês/Ano',
                y='Valor',
                color='Tipo',
                barmode='group',
                title='Entradas x Saídas (por Mês/Ano)',
                labels={'Valor': 'Valor (R$)'},
                template='plotly_dark'
            )
            fig_dre.update_yaxes(tickprefix="R$ ", tickformat=",.2f")
            fig_dre.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#E2725B')
            )
            st.plotly_chart(fig_dre, use_container_width=True)
        else:
            st.write("Não há dados suficientes para exibir o gráfico de Entradas x Saídas.")
    
        st.subheader("Comparação: (Receita Vendas ML + SH) x (Impostos - DAS Simples Nacional)")
        df_receitas = df[df['ContaContabil'].isin(['Receita Vendas ML', 'Receita Vendas SH'])]
        df_receitas_mensal = df_receitas.groupby('Mês/Ano')['Valor'].sum().reset_index()
        df_receitas_mensal.rename(columns={'Valor': 'Receitas'}, inplace=True)
        df_impostos = df[df['ContaContabil'] == 'Impostos - DAS Simples Nacional'].copy()
        df_impostos['Valor'] = df_impostos['Valor'].abs()
        df_impostos_mensal = df_impostos.groupby('Mês/Ano')['Valor'].sum().reset_index()
        df_impostos_mensal.rename(columns={'Valor': 'Impostos'}, inplace=True)
        df_comparacao = pd.merge(df_receitas_mensal, df_impostos_mensal, on='Mês/Ano', how='outer').fillna(0)
        if not df_comparacao.empty:
            df_comparacao_melt = df_comparacao.melt(
                id_vars='Mês/Ano',
                value_vars=['Receitas','Impostos'],
                var_name='Tipo',
                value_name='Valor'
            )
            fig_comp = px.bar(
                df_comparacao_melt,
                x='Mês/Ano',
                y='Valor',
                color='Tipo',
                barmode='group',
                title='(Receita Vendas ML + SH) vs (Impostos - DAS Simples Nacional)',
                labels={'Valor': 'Valor (R$)'},
                template='plotly_dark'
            )
            fig_comp.update_yaxes(tickprefix="R$ ", tickformat=",.2f")
            fig_comp.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#E2725B')
            )
            st.plotly_chart(fig_comp, use_container_width=True)
        else:
            st.write("Não há dados para gerar a comparação entre Receitas e Impostos (DAS).")
    
    # ABA 4: Exportação
    with tab4:
        st.subheader("Exportar Resumo")
        resumo2 = df.groupby(['ContaContabil', 'Mês/Ano'])['Valor'].sum().reset_index()
        resumo_pivot2 = resumo2.pivot(index='ContaContabil', columns='Mês/Ano', values='Valor').fillna(0)
        resumo_pivot2['Total'] = resumo_pivot2.sum(axis=1)
        resumo_pivot2.sort_values(by='Total', ascending=False, inplace=True)
        csv_data = convert_df(resumo_pivot2)
        st.download_button(
            label="💾 Exportar Resumo para CSV",
            data=csv_data,
            file_name='Resumo_ContaContabil.csv',
            mime='text/csv'
        )
else:
    st.warning("Por favor, faça o upload de um arquivo Excel para começar.")

# ------------------------------------
# FOOTER PERSONALIZADO
# ------------------------------------
st.markdown('<div class="custom-footer">Dashboard desenvolvido por [Seu Nome] - 2025</div>', unsafe_allow_html=True)

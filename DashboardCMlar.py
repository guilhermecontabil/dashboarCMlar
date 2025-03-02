import streamlit as st
import pandas as pd
import plotly.express as px

# ------------------------------------
# 1) CONFIGURAÇÕES E TEMA DARK
# ------------------------------------
st.set_page_config(page_title="Dashboard Contábil", layout="wide")

def convert_df(df):
    return df.to_csv(index=False).encode('utf-8')

def formata_valor_brasil(valor):
    """
    Converte um número float em string no formato:
    1.234,56 (ponto para milhar, vírgula para decimal)
    """
    if pd.isnull(valor):
        return ""
    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# CSS para forçar fundo escuro em toda a página e manter elementos em neon
st.markdown("""
    <style>
    /* Fundo geral em dark */
    html, body, [data-testid="stAppViewContainer"], .main, .block-container {
        background-color: #1a1a1a !important;
        color: #ffffff !important;
    }

    /* Estilo dos títulos */
    h1, h2, h3, h4, h5, h6 {
        color: #39ff14;
    }

    /* Estilo das métricas (cartões) */
    .stMetric-label {
        color: #39ff14;
    }
    .stMetric-value {
        color: #39ff14;
    }

    /* Estilo dos botões */
    .stButton>button {
        background-color: #39ff14;
        color: #000000;
    }

    /* Estilo da barra lateral */
    .sidebar .sidebar-content {
        background-color: #1a1a1a;
    }

    /* Separador */
    hr {
        border: 1px solid #39ff14;
    }
    </style>
""", unsafe_allow_html=True)

# ------------------------------------
# 2) BARRA LATERAL: UPLOAD DE ARQUIVO
# ------------------------------------
st.sidebar.title("⚙️ Configurações")

uploaded_file = st.sidebar.file_uploader("📥 Importar arquivo Excel", type=["xlsx"])

if uploaded_file is not None:
    df = pd.read_excel(uploaded_file)
    st.session_state['df'] = df
    st.sidebar.success("Arquivo carregado com sucesso.")
elif 'df' in st.session_state:
    df = st.session_state['df']
else:
    df = None
    st.sidebar.warning("Por favor, faça o upload de um arquivo Excel para começar.")

# ------------------------------------
# 3) SÓ PROSSEGUE SE HOUVER ARQUIVO
# ------------------------------------
if df is not None:
    # 3.1) Conversões de tipo
    df['Data'] = pd.to_datetime(df['Data'], dayfirst=True, errors='coerce')
    df['Valor'] = pd.to_numeric(df['Valor'], errors='coerce')

    # --------------------------------
    # 3.2) FILTROS NA BARRA LATERAL
    # --------------------------------
    # a) Filtro de datas
    min_date = df['Data'].min()
    max_date = df['Data'].max()
    selected_dates = st.sidebar.date_input("Selecione o intervalo de datas:", [min_date, max_date])
    if isinstance(selected_dates, list) and len(selected_dates) == 2:
        start_date, end_date = selected_dates
        df = df[(df['Data'] >= pd.to_datetime(start_date)) & (df['Data'] <= pd.to_datetime(end_date))]

    # b) Filtro por GrupoDeConta (opcional)
    if 'GrupoDeConta' in df.columns:
        grupos_unicos = df['GrupoDeConta'].dropna().unique()
        grupo_selecionado = st.sidebar.selectbox("🗂️ Filtrar por Grupo de Conta:", ["Todos"] + list(grupos_unicos))
        if grupo_selecionado != "Todos":
            df = df[df['GrupoDeConta'] == grupo_selecionado]
    else:
        st.sidebar.info("Coluna 'GrupoDeConta' não encontrada. Filtro desabilitado.")

    # c) Filtro por ContaContabil (texto)
    filtro_conta = st.sidebar.text_input("🔍 Filtrar Conta Contábil:")
    if filtro_conta:
        df = df[df['ContaContabil'].str.contains(filtro_conta, case=False, na=False)]

    # --------------------------------
    # 4) CABEÇALHO E MÉTRICAS
    # --------------------------------
    st.title("💹 Dashboard Contábil")
    st.markdown("<hr>", unsafe_allow_html=True)

    # Entradas (valores > 0)
    total_entradas = df[df['Valor'] > 0]['Valor'].sum()
    # Saídas (valores < 0)
    total_saidas = df[df['Valor'] < 0]['Valor'].sum()
    # Saldo
    saldo = total_entradas + total_saidas

    # Dois novos cartões:
    # - Compras de Mercadoria para Revenda
    total_compras_revenda = df[df['ContaContabil'] == 'Compras de Mercadoria para Revenda']['Valor'].sum()
    # - Impostos - DAS Simples Nacional
    total_das = df[df['ContaContabil'] == 'Impostos - DAS Simples Nacional']['Valor'].sum()

    # Exibir métricas em duas linhas (3 colunas na primeira linha, 2 colunas na segunda)
    # Linha 1
    col1, col2, col3 = st.columns(3)
    col1.metric("Entradas (R$)", formata_valor_brasil(total_entradas))
    col2.metric("Saídas (R$)", formata_valor_brasil(abs(total_saidas)))  # Exibe saída como positivo
    col3.metric("Saldo (R$)", formata_valor_brasil(saldo))

    # Linha 2
    col4, col5 = st.columns(2)
    # Caso queira exibir “Compras” e “Impostos” sempre como valor positivo, use abs().
    col4.metric("Compras de Mercadoria para Revenda", formata_valor_brasil(total_compras_revenda))
    col5.metric("Impostos - DAS Simples Nacional", formata_valor_brasil(total_das))

    # --------------------------------
    # 5) CRIAÇÃO DAS ABAS
    # --------------------------------
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Resumo", "📄 Dados", "📈 Gráficos", "💾 Exportação"])

    # ----------------------------
    # 5.1) ABA: RESUMO
    # ----------------------------
    with tab1:
        st.subheader("Resumo por Conta Contábil")

        df['Mês/Ano'] = df['Data'].dt.to_period('M').astype(str)
        resumo = df.groupby(['ContaContabil', 'Mês/Ano'])['Valor'].sum().reset_index()
        resumo_pivot = resumo.pivot(index='ContaContabil', columns='Mês/Ano', values='Valor').fillna(0)

        # Adiciona coluna Total e ordena decrescentemente
        resumo_pivot['Total'] = resumo_pivot.sum(axis=1)
        resumo_pivot.sort_values(by='Total', ascending=False, inplace=True)

        st.dataframe(
            resumo_pivot.style
            .format(lambda x: formata_valor_brasil(x))
            .set_properties(**{'background-color': '#1a1a1a', 'color': '#ffffff'})
        )

    # ----------------------------
    # 5.2) ABA: DADOS
    # ----------------------------
    with tab2:
        st.subheader("Dados Importados")

        # Ordena por Valor desc, assim valores positivos (maiores) ficam no topo
        df_sorted = df.sort_values(by='Valor', ascending=False)

        st.dataframe(
            df_sorted.style
            .format({'Valor': lambda x: formata_valor_brasil(x)})
            .set_properties(**{'background-color': '#1a1a1a', 'color': '#ffffff'})
        )

    # ----------------------------
    # 5.3) ABA: GRÁFICOS
    # ----------------------------
    with tab3:
        # a) Entradas (valores > 0)
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
                color_discrete_sequence=px.colors.qualitative.Prism
            )
            fig_entradas.update_layout(
                xaxis_tickangle=-45,
                showlegend=False,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#39ff14')
            )
            fig_entradas.update_yaxes(tickprefix="R$ ", tickformat=",.2f")
            st.plotly_chart(fig_entradas, use_container_width=True)
        else:
            st.write("Não há valores positivos para exibir.")

        # b) Saídas (valores < 0)
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
                color_discrete_sequence=['#ff1493']
            )
            fig_saidas.update_layout(
                yaxis={'categoryorder': 'total ascending'},
                showlegend=False,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#39ff14')
            )
            fig_saidas.update_xaxes(tickprefix="R$ ", tickformat=",.2f")
            st.plotly_chart(fig_saidas, use_container_width=True)
        else:
            st.write("Não há valores negativos para exibir.")

        # c) Entradas x Saídas (por Mês/Ano)
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
                font=dict(color='#39ff14')
            )
            st.plotly_chart(fig_dre, use_container_width=True)
        else:
            st.write("Não há dados suficientes para exibir o gráfico de Entradas x Saídas.")

        # d) Comparação: (Receita Vendas ML + SH) vs (Impostos - DAS Simples Nacional)
        st.subheader("Comparação: (Receita Vendas ML + SH) x (Impostos - DAS Simples Nacional)")

        df_receitas = df[df['ContaContabil'].isin(['Receita Vendas ML', 'Receita Vendas SH'])]
        df_receitas_mensal = df_receitas.groupby('Mês/Ano')['Valor'].sum().reset_index()
        df_receitas_mensal.rename(columns={'Valor': 'Receitas'}, inplace=True)

        df_impostos = df[df['ContaContabil'] == 'Impostos - DAS Simples Nacional'].copy()
        # Converte valores para positivo, para exibir acima do eixo
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
                font=dict(color='#39ff14')
            )
            st.plotly_chart(fig_comp, use_container_width=True)
        else:
            st.write("Não há dados para gerar a comparação entre Receitas e Impostos (DAS).")

    # ----------------------------
    # 5.4) ABA: EXPORTAÇÃO
    # ----------------------------
    with tab4:
        st.subheader("Exportar Resumo")
        df['Mês/Ano'] = df['Data'].dt.to_period('M').astype(str)
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

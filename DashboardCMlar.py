import streamlit as st
import pandas as pd
import plotly.express as px
import re

st.set_page_config(page_title="Dashboard Contábil", layout="wide")

def convert_df(df):
    return df.to_csv(index=False).encode('utf-8')

# CSS (opcional)
st.markdown("""
    <style>
    h1, h2, h3, h4, h5, h6 { color: #39ff14; }
    .st-text, .st-dataframe { color: #ffffff; }
    .stMetric-label { color: #39ff14; }
    .stMetric-value { color: #39ff14; }
    .stButton>button { background-color: #39ff14; color: #000000; }
    .sidebar .sidebar-content { background-color: #1a1a1a; }
    hr { border: 1px solid #39ff14; }
    </style>
""", unsafe_allow_html=True)

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

if df is not None:
    # 1) Ver quais colunas o pandas reconhece
    st.write("Colunas encontradas no arquivo:", df.columns.tolist())

    # 2) Mapeamento de nomes “limpos” para nomes padronizados
    col_map = {
        'codcontacontabil': 'CodContaContabil',
        'contacontabil': 'ContaContabil',
        'grupodeconta': 'GrupoDeConta',
        'data': 'Data',
        'valor': 'Valor',
        'tipo': 'Tipo',
        'codcontautilizada': 'CodContaUtilizada'
    }

    # 3) Gerar dicionário de renome com base no que for encontrado
    rename_dict = {}
    for original_col in df.columns:
        # Remove espaços, sublinhados e deixa tudo em minúsculo
        col_clean = re.sub(r'[\s_]+', '', original_col).lower()
        if col_clean in col_map:
            rename_dict[original_col] = col_map[col_clean]

    # 4) Renomear as colunas que foram reconhecidas
    df.rename(columns=rename_dict, inplace=True)

    # Agora, assumimos que as colunas estão padronizadas
    # Converter Data e Valor
    if 'Data' in df.columns:
        df['Data'] = pd.to_datetime(df['Data'], dayfirst=True, errors='coerce')
    if 'Valor' in df.columns:
        df['Valor'] = pd.to_numeric(df['Valor'], errors='coerce')

    # --- FILTROS NA BARRA LATERAL ---
    # Filtro de datas
    if 'Data' in df.columns:
        min_date = df['Data'].min()
        max_date = df['Data'].max()
        selected_dates = st.sidebar.date_input("Selecione o intervalo de datas:", [min_date, max_date])
        if isinstance(selected_dates, list) and len(selected_dates) == 2:
            start_date, end_date = selected_dates
            df = df[(df['Data'] >= pd.to_datetime(start_date)) & (df['Data'] <= pd.to_datetime(end_date))]

    # Filtro por GrupoDeConta
    if 'GrupoDeConta' in df.columns:
        grupos_unicos = df['GrupoDeConta'].dropna().unique()
        grupo_selecionado = st.sidebar.selectbox("🗂️ Filtrar por Grupo de Conta:", ["Todos"] + list(grupos_unicos))
        if grupo_selecionado != "Todos":
            df = df[df['GrupoDeConta'] == grupo_selecionado]
    else:
        st.sidebar.info("Coluna 'GrupoDeConta' não encontrada. Filtro desabilitado.")

    # Filtro por ContaContabil
    if 'ContaContabil' in df.columns:
        filtro_conta = st.sidebar.text_input("🔍 Filtrar Conta Contábil:")
        if filtro_conta:
            df = df[df['ContaContabil'].str.contains(filtro_conta, case=False, na=False)]
    else:
        st.sidebar.info("Coluna 'ContaContabil' não encontrada.")

    # --- DASHBOARD ---
    st.title("💹 Dashboard Contábil")
    st.markdown("<hr>", unsafe_allow_html=True)

    # Cálculo de métricas
    if 'Valor' in df.columns:
        total_entradas = df[df['Valor'] > 0]['Valor'].sum()
        total_saidas = df[df['Valor'] < 0]['Valor'].sum()
        saldo = total_entradas + total_saidas

        col1, col2, col3 = st.columns(3)
        col1.metric("Entradas (R$)", f"{total_entradas:,.2f}")
        col2.metric("Saídas (R$)", f"{abs(total_saidas):,.2f}")
        col3.metric("Saldo (R$)", f"{saldo:,.2f}")
    else:
        st.warning("Coluna 'Valor' não encontrada. Não é possível calcular métricas.")

    tab1, tab2, tab3, tab4 = st.tabs(["📊 Resumo", "📄 Dados", "📈 Gráficos", "💾 Exportação"])

    # Resumo
    with tab1:
        st.subheader("Resumo por Conta Contábil")
        if {'ContaContabil', 'Data', 'Valor'}.issubset(df.columns):
            df['Mês/Ano'] = df['Data'].dt.to_period('M').astype(str)
            resumo = df.groupby(['ContaContabil', 'Mês/Ano'])['Valor'].sum().reset_index()
            resumo_pivot = resumo.pivot(index='ContaContabil', columns='Mês/Ano', values='Valor').fillna(0)
            resumo_pivot['Total'] = resumo_pivot.sum(axis=1)
            st.dataframe(
                resumo_pivot.style
                .format(lambda x: f"R$ {x:,.2f}")
                .set_properties(**{'background-color': '#1a1a1a', 'color': '#ffffff'})
            )
        else:
            st.write("Colunas necessárias (ContaContabil, Data, Valor) não estão disponíveis.")

    # Dados
    with tab2:
        st.subheader("Dados Importados")
        st.dataframe(df.style.set_properties(**{'background-color': '#1a1a1a', 'color': '#ffffff'}))

    # Gráficos
    with tab3:
        if 'Valor' in df.columns and 'ContaContabil' in df.columns:
            # Entradas
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
                    template='plotly_dark'
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

            # Saídas
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

            # Entradas x Saídas mensal
            st.subheader("Entradas x Saídas (por Mês/Ano)")
            if 'Mês/Ano' in df.columns:
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
                    st.write("Não há dados suficientes para exibir Entradas x Saídas.")
            else:
                st.write("Coluna 'Mês/Ano' não encontrada. Não é possível gerar o gráfico de Entradas x Saídas.")
        else:
            st.write("Colunas 'ContaContabil' e/ou 'Valor' não encontradas. Não é possível gerar gráficos.")

    # Exportação
    with tab4:
        st.subheader("Exportar Resumo")
        if 'ContaContabil' in df.columns and 'Mês/Ano' in df.columns and 'Valor' in df.columns:
            resumo = df.groupby(['ContaContabil', 'Mês/Ano'])['Valor'].sum().reset_index()
            resumo_pivot = resumo.pivot(index='ContaContabil', columns='Mês/Ano', values='Valor').fillna(0)
            resumo_pivot['Total'] = resumo_pivot.sum(axis=1)
            csv_data = convert_df(resumo_pivot)
            st.download_button(
                label="💾 Exportar Resumo para CSV",
                data=csv_data,
                file_name='Resumo_ContaContabil.csv',
                mime='text/csv'
            )
        else:
            st.write("Não foi possível criar o resumo para exportação. Verifique as colunas necessárias.")
else:
    st.warning("Por favor, faça o upload de um arquivo Excel para começar.")

import streamlit as st
import pandas as pd
import plotly.express as px

# Configuração inicial da página do Streamlit
st.set_page_config(page_title="Dashboard Contábil", layout="wide")

# Função para converter DataFrame em CSV (para exportação)
def convert_df(df):
    return df.to_csv(index=False).encode('utf-8')

# --- Estilos CSS Personalizados ---
st.markdown("""
    <style>
    /* Estilo dos títulos */
    h1, h2, h3, h4, h5, h6 {
        color: #39ff14;
    }
    /* Estilo dos textos e dataframes */
    .st-text, .st-dataframe {
        color: #ffffff;
    }
    /* Estilo das métricas */
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

# --- Barra Lateral ---
st.sidebar.title("⚙️ Configurações")

# Upload do arquivo Excel
uploaded_file = st.sidebar.file_uploader("📥 Importar arquivo Excel", type=["xlsx"])

# Carregando o DataFrame na sessão, se houver arquivo
if uploaded_file is not None:
    df = pd.read_excel(uploaded_file)
    st.sidebar.success("Arquivo carregado com sucesso.")
    st.session_state['df'] = df
elif 'df' in st.session_state:
    df = st.session_state['df']
else:
    st.sidebar.warning("Por favor, faça o upload de um arquivo Excel para começar.")
    df = None

# Só executa a dashboard se o DataFrame existir
if df is not None:
    # Verifique como o pandas reconhece as colunas
    # st.write("Colunas encontradas no arquivo:", df.columns)

    # --- TRATAMENTO DE DADOS ---
    # Converter 'Data' para datetime e 'Valor' para numérico
    df['Data'] = pd.to_datetime(df['Data'], dayfirst=True, errors='coerce')
    df['Valor'] = pd.to_numeric(df['Valor'], errors='coerce')

    # --- FILTROS NA BARRA LATERAL ---
    # 1) Filtro de intervalo de datas
    min_date = df['Data'].min()
    max_date = df['Data'].max()
    selected_dates = st.sidebar.date_input("Selecione o intervalo de datas:", [min_date, max_date])
    if isinstance(selected_dates, list) and len(selected_dates) == 2:
        start_date, end_date = selected_dates
        df = df[(df['Data'] >= pd.to_datetime(start_date)) & (df['Data'] <= pd.to_datetime(end_date))]

    # 2) Filtro por GrupoDeConta (apenas se a coluna existir)
    if 'GrupoDeConta' in df.columns:
        grupos_unicos = df['GrupoDeConta'].dropna().unique()
        grupo_selecionado = st.sidebar.selectbox("🗂️ Filtrar por Grupo de Conta:", ["Todos"] + list(grupos_unicos))
        if grupo_selecionado != "Todos":
            df = df[df['GrupoDeConta'] == grupo_selecionado]
    else:
        st.sidebar.info("Coluna 'GrupoDeConta' não encontrada. Filtro de Grupo de Conta desabilitado.")

    # 3) Filtro por ContaContabil (campo de texto)
    if 'ContaContabil' in df.columns:
        filtro_conta = st.sidebar.text_input("🔍 Filtrar Conta Contábil:")
        if filtro_conta:
            df = df[df['ContaContabil'].str.contains(filtro_conta, case=False, na=False)]
    else:
        st.sidebar.info("Coluna 'ContaContabil' não encontrada. Filtro de Conta Contábil desabilitado.")

    # --- CABEÇALHO ---
    st.title("💹 Dashboard Contábil")
    st.markdown("Visualize e analise os dados de forma clara e objetiva.")
    st.markdown("<hr>", unsafe_allow_html=True)

    # --- CÁLCULO DE MÉTRICAS PRINCIPAIS ---
    # Entradas (valores positivos)
    total_entradas = df[df['Valor'] > 0]['Valor'].sum()
    # Saídas (valores negativos)
    total_saidas = df[df['Valor'] < 0]['Valor'].sum()
    total_saidas_abs = abs(total_saidas)  # para exibir valor positivo
    # Saldo
    saldo = total_entradas + total_saidas

    # Exibir métricas no cabeçalho
    col1, col2, col3 = st.columns(3)
    col1.metric("Entradas (R$)", f"{total_entradas:,.2f}")
    col2.metric("Saídas (R$)", f"{total_saidas_abs:,.2f}")
    col3.metric("Saldo (R$)", f"{saldo:,.2f}")

    # --- CRIAÇÃO DAS ABAS ---
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Resumo", "📄 Dados", "📈 Gráficos", "💾 Exportação"])

    # --- ABA 1: RESUMO ---
    with tab1:
        st.subheader("Resumo por Conta Contábil")
        # Checar se "ContaContabil" e "Data" existem para fazer o pivot
        if 'ContaContabil' in df.columns and 'Data' in df.columns:
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
            st.write("Colunas 'ContaContabil' e/ou 'Data' não encontradas. Não é possível exibir o resumo.")

    # --- ABA 2: DADOS ---
    with tab2:
        st.subheader("Dados Importados")
        st.dataframe(
            df.style
            .format({'Valor': lambda x: f"R$ {x:,.2f}"})
            .set_properties(**{'background-color': '#1a1a1a', 'color': '#ffffff'})
        )

    # --- ABA 3: GRÁFICOS ---
    with tab3:
        # GRÁFICO DE ENTRADAS (VALORES POSITIVOS)
        st.subheader("Entradas (Valores Positivos)")
        df_positivo = df[df['Valor'] > 0]
        if 'ContaContabil' in df_positivo.columns:
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
        else:
            st.write("Coluna 'ContaContabil' não encontrada. Não é possível gerar o gráfico de Entradas.")

        # GRÁFICO DE SAÍDAS (VALORES NEGATIVOS)
        st.subheader("Saídas (Valores Negativos)")
        df_negativo = df[df['Valor'] < 0]
        if 'ContaContabil' in df_negativo.columns:
            df_negativo_agrupado = df_negativo.groupby('ContaContabil')['Valor'].sum().abs().reset_index()
            if not df_negativo_agrupado.empty:
                # Top 5 maiores saídas
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
        else:
            st.write("Coluna 'ContaContabil' não encontrada. Não é possível gerar o gráfico de Saídas.")

        # GRÁFICO DE ENTRADAS x SAÍDAS MENSAL
        st.subheader("Entradas x Saídas (por Mês/Ano)")
        if 'Mês/Ano' in df.columns:
            df_entradas_mensal = df[df['Valor'] > 0].groupby('Mês/Ano')['Valor'].sum().reset_index()
            df_saidas_mensal = df[df['Valor'] < 0].groupby('Mês/Ano')['Valor'].sum().reset_index()
            df_saidas_mensal['Valor'] = df_saidas_mensal['Valor'].abs()  # para exibir valor positivo

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
        else:
            st.write("Coluna 'Mês/Ano' não encontrada. Não é possível gerar o gráfico de Entradas x Saídas.")

    # --- ABA 4: EXPORTAÇÃO ---
    with tab4:
        st.subheader("Exportar Resumo")
        if 'ContaContabil' in df.columns and 'Mês/Ano' in df.columns:
            # Reutilizamos o resumo_pivot criado na Aba Resumo
            csv_data = convert_df(resumo_pivot)
            st.download_button(
                label="💾 Exportar Resumo para CSV",
                data=csv_data,
                file_name='Resumo_ContaContabil.csv',
                mime='text/csv'
            )
        else:
            st.write("Colunas necessárias para resumo não encontradas. Não é possível exportar.")
else:
    st.warning("Por favor, faça o upload de um arquivo Excel para começar.")

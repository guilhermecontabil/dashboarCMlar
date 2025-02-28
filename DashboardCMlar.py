import streamlit as st
import pandas as pd
import plotly.express as px

# Configuração inicial da página do Streamlit
st.set_page_config(page_title="Dashboard Contábil", layout="wide")

# Função para converter DataFrame para CSV
def convert_df(df):
    return df.to_csv(index=False).encode('utf-8')

# --- Estilos CSS Personalizados ---
st.markdown("""
    <style>
    /* Estilo dos títulos */
    h1, h2, h3, h4, h5, h6 {
        color: #39ff14;
    }
    /* Estilo dos textos */
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
    /* Estilo dos elementos da barra lateral */
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

if uploaded_file is not None:
    # Carregar o arquivo Excel na memória
    df = pd.read_excel(uploaded_file)
    st.sidebar.success("Arquivo carregado com sucesso.")
    st.session_state['df'] = df
elif 'df' in st.session_state:
    df = st.session_state['df']
else:
    st.sidebar.warning("Por favor, faça o upload de um arquivo Excel para começar.")
    df = None

if df is not None:
    # --- Tratamento de dados ---
    # Converter 'Data' para datetime e 'Valor' para numérico
    df['Data'] = pd.to_datetime(df['Data'], dayfirst=True, errors='coerce')
    df['Valor'] = pd.to_numeric(df['Valor'], errors='coerce')

    # Filtro de intervalo de datas
    min_date = df['Data'].min()
    max_date = df['Data'].max()
    selected_dates = st.sidebar.date_input("Selecione o intervalo de datas", [min_date, max_date])
    if isinstance(selected_dates, list) and len(selected_dates) == 2:
        start_date, end_date = selected_dates
        df = df[(df['Data'] >= pd.to_datetime(start_date)) & (df['Data'] <= pd.to_datetime(end_date))]

    # (Opcional) Filtro por GrupoDeConta
    todos_grupos = df['GrupoDeConta'].dropna().unique()
    grupo_selecionado = st.sidebar.selectbox("🗂️ Filtrar por Grupo de Conta:", ["Todos"] + list(todos_grupos))
    if grupo_selecionado != "Todos":
        df = df[df['GrupoDeConta'] == grupo_selecionado]

    # Filtro por ContaContabil (busca por texto)
    filtro_conta = st.sidebar.text_input("🔍 Filtrar Conta Contábil:")
    if filtro_conta:
        df = df[df['ContaContabil'].str.contains(filtro_conta, case=False, na=False)]

    # --- Cabeçalho ---
    st.title("💹 Dashboard Contábil")
    st.markdown("Bem-vindo ao dashboard contábil. Visualize e analise os dados de forma clara e objetiva.")
    st.markdown("<hr>", unsafe_allow_html=True)

    # --- Cálculo de métricas principais ---
    # Entradas (Valores positivos)
    total_entradas = df[df['Valor'] > 0]['Valor'].sum()
    # Saídas (Valores negativos) - usamos valor absoluto para exibir positivo
    total_saidas = df[df['Valor'] < 0]['Valor'].sum()
    total_saidas_abs = abs(total_saidas)
    # Saldo
    saldo = total_entradas + total_saidas

    # Exibir métricas no cabeçalho
    col1, col2, col3 = st.columns(3)
    col1.metric("Entradas (R$)", f"{total_entradas:,.2f}")
    col2.metric("Saídas (R$)", f"{total_saidas_abs:,.2f}")
    col3.metric("Saldo (R$)", f"{saldo:,.2f}")

    # --- Criação das Abas ---
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Resumo", "📄 Dados", "📈 Gráficos", "💾 Exportação"])

    # --- Aba Resumo ---
    with tab1:
        st.subheader("Resumo de Contas")
        # Criar coluna auxiliar para Mês/Ano
        df['Mês/Ano'] = df['Data'].dt.to_period('M').astype(str)

        # Agrupar por ContaContabil e Mês/Ano
        resumo = df.groupby(['ContaContabil', 'Mês/Ano'])['Valor'].sum().reset_index()
        resumo_pivot = resumo.pivot(index='ContaContabil', columns='Mês/Ano', values='Valor').fillna(0)
        resumo_pivot['Total'] = resumo_pivot.sum(axis=1)

        st.subheader("Total por Conta Contábil (Agrupado por Mês/Ano)")
        st.dataframe(
            resumo_pivot.style
            .format(lambda x: f"R$ {x:,.2f}")
            .set_properties(**{'background-color': '#1a1a1a', 'color': '#ffffff'})
        )

    # --- Aba Dados ---
    with tab2:
        st.subheader("Dados Importados")
        st.dataframe(
            df.style
            .format({'Valor': lambda x: f"R$ {x:,.2f}"})
            .set_properties(**{'background-color': '#1a1a1a', 'color': '#ffffff'})
        )

    # --- Aba Gráficos ---
    with tab3:
        # Gráfico de Entradas (valores positivos)
        st.subheader("Entradas (Valores Positivos)")
        df_positivo = df[df['Valor'] > 0]
        df_positivo_agrupado = df_positivo.groupby('ContaContabil')['Valor'].sum().reset_index()
        if not df_positivo_agrupado.empty:
            fig = px.bar(
                df_positivo_agrupado,
                x='ContaContabil',
                y='Valor',
                color='ContaContabil',
                title='Entradas por Conta Contábil',
                labels={'Valor': 'Valor (R$)'},
                template='plotly_dark',
                color_discrete_sequence=px.colors.qualitative.Prism
            )
            fig.update_layout(
                xaxis_tickangle=-45,
                showlegend=False,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#39ff14')
            )
            fig.update_yaxes(tickprefix="R$ ", tickformat=",.2f")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.write("Não há valores positivos para exibir.")

        # Gráfico de Saídas (valores negativos)
        st.subheader("Saídas (Valores Negativos)")
        df_negativo = df[df['Valor'] < 0]
        df_negativo_agrupado = df_negativo.groupby('ContaContabil')['Valor'].sum().abs().reset_index()
        if not df_negativo_agrupado.empty:
            # Top 5 para exibir as maiores saídas
            top_5 = df_negativo_agrupado.nlargest(5, 'Valor')
            fig2 = px.bar(
                top_5,
                y='ContaContabil',
                x='Valor',
                orientation='h',
                title='Top 5 Categorias de Saídas',
                labels={'Valor': 'Valor (R$)', 'ContaContabil': 'Conta Contábil'},
                template='plotly_dark',
                color_discrete_sequence=['#ff1493']
            )
            fig2.update_layout(
                yaxis={'categoryorder': 'total ascending'},
                showlegend=False,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#39ff14')
            )
            fig2.update_xaxes(tickprefix="R$ ", tickformat=",.2f")
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.write("Não há valores negativos para exibir nas top 5 saídas.")

        # Gráfico: Entradas e Saídas ao Longo dos Meses
        st.subheader("Entradas e Saídas Mensais")
        df_entradas = df[df['Valor'] > 0].groupby('Mês/Ano')['Valor'].sum().reset_index()
        df_saidas = df[df['Valor'] < 0].groupby('Mês/Ano')['Valor'].sum().reset_index()
        df_saidas['Valor'] = df_saidas['Valor'].abs()  # Converte para positivo para o gráfico comparativo

        df_entradas['Tipo'] = 'Entradas'
        df_saidas['Tipo'] = 'Saídas'

        df_dre = pd.concat([df_entradas, df_saidas], axis=0)

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

    # --- Aba Exportação ---
    with tab4:
        st.subheader("Exportar Resumo")
        # Reaproveitamos o pivot (resumo_pivot) criado na Aba Resumo
        csv_data = convert_df(resumo_pivot)
        st.download_button(
            label="💾 Exportar Resumo para CSV",
            data=csv_data,
            file_name='Resumo_ContaContabil.csv',
            mime='text/csv'
        )
else:
    st.warning("Por favor, faça o upload de um arquivo Excel para começar.")

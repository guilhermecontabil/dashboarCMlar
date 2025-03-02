import streamlit as st
import pandas as pd
import plotly.express as px

# Configuração inicial da página do Streamlit
st.set_page_config(page_title="Dashboard Contábil", layout="wide")

# Função para converter DataFrame em CSV (para exportação)
def convert_df(df):
    return df.to_csv(index=False).encode('utf-8')

# --- CSS customizado para tema dark ---
st.markdown("""
    <style>
    body {
        background-color: #1a1a1a;
        color: #ffffff;
    }
    h1, h2, h3, h4, h5, h6 {
        color: #39ff14;
    }
    .stMetric-label {
        color: #39ff14;
    }
    .stMetric-value {
        color: #39ff14;
    }
    .stButton>button {
        background-color: #39ff14;
        color: #000000;
    }
    .sidebar .sidebar-content {
        background-color: #1a1a1a;
    }
    hr {
        border: 1px solid #39ff14;
    }
    </style>
""", unsafe_allow_html=True)

# --- Barra Lateral ---
st.sidebar.title("⚙️ Configurações")
uploaded_file = st.sidebar.file_uploader("📥 Importar arquivo Excel", type=["xlsx"])

# Carregar e manter o DataFrame na sessão
if uploaded_file is not None:
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
    df['Data'] = pd.to_datetime(df['Data'], dayfirst=True, errors='coerce')
    df['Valor'] = pd.to_numeric(df['Valor'], errors='coerce')

    # Filtro de intervalo de datas
    min_date = df['Data'].min()
    max_date = df['Data'].max()
    selected_dates = st.sidebar.date_input("Selecione o intervalo de datas:", [min_date, max_date])
    if isinstance(selected_dates, list) and len(selected_dates) == 2:
        start_date, end_date = selected_dates
        df = df[(df['Data'] >= pd.to_datetime(start_date)) & (df['Data'] <= pd.to_datetime(end_date))]

    # Filtro por GrupoDeConta (se existir)
    if "GrupoDeConta" in df.columns:
        grupos_unicos = df["GrupoDeConta"].dropna().unique()
        grupo_selecionado = st.sidebar.selectbox("🗂️ Filtrar por Grupo de Conta:", ["Todos"] + list(grupos_unicos))
        if grupo_selecionado != "Todos":
            df = df[df["GrupoDeConta"] == grupo_selecionado]
    else:
        st.sidebar.warning("A coluna 'GrupoDeConta' não foi encontrada. Filtro de grupo desabilitado.")

    # Filtro por ContaContabil (busca por texto)
    filtro_conta = st.sidebar.text_input("🔍 Filtrar Conta Contábil:")
    if filtro_conta:
        df = df[df["ContaContabil"].str.contains(filtro_conta, case=False, na=False)]

    # --- Cabeçalho e Métricas Gerais ---
    st.title("💹 Dashboard Contábil")
    st.markdown("Visualize e analise os dados de forma clara e objetiva.")
    st.markdown("<hr>", unsafe_allow_html=True)

    # Cálculo de métricas gerais
    total_entradas = df[df["Valor"] > 0]["Valor"].sum()
    total_saidas = df[df["Valor"] < 0]["Valor"].sum()
    total_saidas_abs = abs(total_saidas)
    saldo = total_entradas + total_saidas

    col1, col2, col3 = st.columns(3)
    col1.metric("Entradas (R$)", f"{total_entradas:,.2f}")
    col2.metric("Saídas (R$)", f"{total_saidas_abs:,.2f}")
    col3.metric("Saldo (R$)", f"{saldo:,.2f}")

    # --- Cálculo para Comparação ---
    # Soma dos valores para "Receita Vendas ML" e "Receita Vendas SH"
    receita_vendas = df[df["ContaContabil"].isin(["Receita Vendas ML", "Receita Vendas SH"])]["Valor"].sum()
    # Soma dos valores para "Impostos" e "DAS Simples Nacional"
    impostos_das = df[df["ContaContabil"].isin(["Impostos", "DAS Simples Nacional"])]["Valor"].sum()
    # Exibição com valores absolutos para evitar barras negativas
    receita_vendas_display = abs(receita_vendas)
    impostos_das_display = abs(impostos_das)

    # --- Criação das Abas ---
    # Abas: Resumo, Dados, Comparação, Gráficos e Exportação
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Resumo", "📄 Dados", "🔍 Comparação", "📈 Gráficos", "💾 Exportação"])

    # Aba 1: Resumo
    with tab1:
        st.subheader("Resumo por Conta Contábil")
        # Cria a coluna auxiliar Mês/Ano
        df["Mês/Ano"] = df["Data"].dt.to_period("M").astype(str)
        # Agrupa os dados por ContaContabil e Mês/Ano
        resumo = df.groupby(["ContaContabil", "Mês/Ano"])["Valor"].sum().reset_index()
        resumo_pivot = resumo.pivot(index="ContaContabil", columns="Mês/Ano", values="Valor").fillna(0)
        resumo_pivot["Total"] = resumo_pivot.sum(axis=1)
        st.dataframe(
            resumo_pivot.style
            .format(lambda x: f"R$ {x:,.2f}")
            .set_properties(**{"background-color": "#1a1a1a", "color": "#ffffff"})
        )

    # Aba 2: Dados
    with tab2:
        st.subheader("Dados Importados")
        st.dataframe(
            df.style
            .format({"Valor": lambda x: f"R$ {x:,.2f}"})
            .set_properties(**{"background-color": "#1a1a1a", "color": "#ffffff"})
        )

    # Aba 3: Comparação
    with tab3:
        st.subheader("Comparação: Receita vs Impostos")
        col_a, col_b = st.columns(2)
        col_a.metric("Receita Vendas (ML + SH)", f"R$ {receita_vendas_display:,.2f}")
        col_b.metric("Impostos - DAS Simples Nacional", f"R$ {impostos_das_display:,.2f}")
        # Cria um DataFrame para o gráfico comparativo
        comp_df = pd.DataFrame({
            "Categoria": ["Receita Vendas (ML + SH)", "Impostos - DAS Simples Nacional"],
            "Valor": [receita_vendas_display, impostos_das_display]
        })
        fig_comp = px.bar(
            comp_df,
            x="Valor",
            y="Categoria",
            orientation="h",
            title="Comparação: Receita vs Impostos",
            labels={"Valor": "Valor (R$)", "Categoria": "Categoria"},
            template="plotly_dark",
            color="Categoria",
            color_discrete_sequence=["#39ff14", "#ff1493"]
        )
        fig_comp.update_layout(
            xaxis_tickformat="R$,.2f",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#39ff14")
        )
        st.plotly_chart(fig_comp, use_container_width=True)

    # Aba 4: Gráficos
    with tab4:
        st.subheader("Gráficos")
        st.markdown("### Entradas (Valores Positivos)")
        df_positivo = df[df["Valor"] > 0]
        df_positivo_agrupado = df_positivo.groupby("ContaContabil")["Valor"].sum().reset_index()
        if not df_positivo_agrupado.empty:
            fig_entradas = px.bar(
                df_positivo_agrupado,
                x="ContaContabil",
                y="Valor",
                color="ContaContabil",
                title="Entradas por Conta Contábil",
                labels={"Valor": "Valor (R$)"},
                template="plotly_dark",
                color_discrete_sequence=px.colors.qualitative.Prism
            )
            fig_entradas.update_layout(
                xaxis_tickangle=-45,
                showlegend=False,
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#39ff14")
            )
            fig_entradas.update_yaxes(tickprefix="R$ ", tickformat=",.2f")
            st.plotly_chart(fig_entradas, use_container_width=True)
        else:
            st.write("Não há valores positivos para exibir.")

        st.markdown("### Saídas (Valores Negativos)")
        df_negativo = df[df["Valor"] < 0]
        df_negativo_agrupado = df_negativo.groupby("ContaContabil")["Valor"].sum().abs().reset_index()
        if not df_negativo_agrupado.empty:
            top_5_saidas = df_negativo_agrupado.nlargest(5, "Valor")
            fig_saidas = px.bar(
                top_5_saidas,
                y="ContaContabil",
                x="Valor",
                orientation="h",
                title="Top 5 Categorias de Saídas",
                labels={"Valor": "Valor (R$)", "ContaContabil": "Conta Contábil"},
                template="plotly_dark",
                color_discrete_sequence=["#ff1493"]
            )
            fig_saidas.update_layout(
                yaxis={"categoryorder": "total ascending"},
                showlegend=False,
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#39ff14")
            )
            fig_saidas.update_xaxes(tickprefix="R$ ", tickformat=",.2f")
            st.plotly_chart(fig_saidas, use_container_width=True)
        else:
            st.write("Não há valores negativos para exibir.")

        st.markdown("### Entradas x Saídas (por Mês/Ano)")
        df_entradas_mensal = df[df["Valor"] > 0].groupby("Mês/Ano")["Valor"].sum().reset_index()
        df_saidas_mensal = df[df["Valor"] < 0].groupby("Mês/Ano")["Valor"].sum().reset_index()
        df_saidas_mensal["Valor"] = df_saidas_mensal["Valor"].abs()
        df_entradas_mensal["Tipo"] = "Entradas"
        df_saidas_mensal["Tipo"] = "Saídas"
        df_dre = pd.concat([df_entradas_mensal, df_saidas_mensal], axis=0)
        if not df_dre.empty:
            fig_dre = px.bar(
                df_dre,
                x="Mês/Ano",
                y="Valor",
                color="Tipo",
                barmode="group",
                title="Entradas x Saídas (por Mês/Ano)",
                labels={"Valor": "Valor (R$)"},
                template="plotly_dark"
            )
            fig_dre.update_yaxes(tickprefix="R$ ", tickformat=",.2f")
            fig_dre.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#39ff14")
            )
            st.plotly_chart(fig_dre, use_container_width=True)
        else:
            st.write("Não há dados suficientes para exibir o gráfico de Entradas x Saídas.")

    # Aba 5: Exportação
    with tab5:
        st.subheader("Exportar Resumo")
        csv_data = convert_df(resumo_pivot)
        st.download_button(
            label="💾 Exportar Resumo para CSV",
            data=csv_data,
            file_name="Resumo_ContaContabil.csv",
            mime="text/csv"
        )
else:
    st.warning("Por favor, faça o upload de um arquivo Excel para começar.")

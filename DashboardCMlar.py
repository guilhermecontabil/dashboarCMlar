import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit.components.v1 as components
import io

# ------------------------------------------------------------------------------
# Configuração da página
# ------------------------------------------------------------------------------
st.set_page_config(page_title="Dashboard Contábil", layout="wide")

# ------------------------------------------------------------------------------
# Funções auxiliares
# ------------------------------------------------------------------------------
def convert_df_to_xlsx(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Resumo')
    return output.getvalue()

def formata_valor_brasil(valor):
    if pd.isnull(valor):
        return ""
    # Formata para o padrão brasileiro: milhar com ponto e decimal com vírgula
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# ------------------------------------------------------------------------------
# Injeção de CSS para customização visual
# ------------------------------------------------------------------------------
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;700&family=Roboto&display=swap');
    html, body, [class*="css"] {
        font-family: 'Roboto', sans-serif;
    }
    .main {
        background: #f0f2f6;
    }
    .header {
        text-align: center;
        padding: 30px;
        background: linear-gradient(135deg, #6a11cb, #2575fc);
        color: white;
        border-radius: 10px;
        margin-bottom: 20px;
    }
    .chart-container, .data-container {
        background: white;
        padding: 20px;
        border-radius: 8px;
        margin-bottom: 20px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }
    /* Card para Margem de Contribuição Ajustada */
    .mc-card {
        background-color: #00796B;
        padding: 20px;
        border-radius: 10px;
        color: white;
        margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True
)

# ------------------------------------------------------------------------------
# Cabeçalho customizado
# ------------------------------------------------------------------------------
components.html(
    """
    <div class="header">
        <h1>Dashboard Contábil</h1>
        <p>Visualize e interaja com os dados contábeis</p>
    </div>
    """, height=150
)

# ------------------------------------------------------------------------------
# Sidebar: Upload, Filtros e Seleção Global de Contas
# ------------------------------------------------------------------------------
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

if df is not None:
    # Filtro global de contas
    all_accounts = sorted(df["ContaContabil"].unique())
    select_all = st.sidebar.checkbox("Selecionar todas as contas", value=True)
    if select_all:
        selected_accounts_global = all_accounts
    else:
        selected_accounts_global = st.sidebar.multiselect("Selecione as Contas (global):", 
                                                           options=all_accounts, default=all_accounts)
    df = df[df["ContaContabil"].isin(selected_accounts_global)]

# ------------------------------------------------------------------------------
# Conversão da coluna "Data" e filtro por "Mês/Ano"
# ------------------------------------------------------------------------------
if df is not None:
    # Converte a coluna 'Data' para datetime (dayfirst=True para padrão brasileiro)
    df['Data'] = pd.to_datetime(df['Data'], dayfirst=True, errors='coerce')
    # Cria a coluna "Mês/Ano"
    df['Mês/Ano'] = df['Data'].dt.to_period('M').astype(str)
    # Filtra por Mês/Ano usando um multiselect
    all_months = sorted(df["Mês/Ano"].unique())
    selected_months = st.sidebar.multiselect("Selecione os meses (Mês/Ano):", options=all_months, default=all_months)
    df = df[df["Mês/Ano"].isin(selected_months)]
    
    if 'GrupoDeConta' in df.columns:
        grupos_unicos = df['GrupoDeConta'].dropna().unique()
        grupo_selecionado = st.sidebar.selectbox("🗂️ Filtrar por Grupo de Conta:", ["Todos"] + list(grupos_unicos))
        if grupo_selecionado != "Todos":
            df = df[df['GrupoDeConta'] == grupo_selecionado]
    
    filtro_conta = st.sidebar.text_input("🔍 Filtrar Conta Contábil (texto):")
    if filtro_conta:
        df = df[df['ContaContabil'].str.contains(filtro_conta, case=False, na=False)]

# ------------------------------------------------------------------------------
# Processamento dos dados e cálculos (se houver dados)
# ------------------------------------------------------------------------------
if df is not None:
    df['Valor'] = pd.to_numeric(df['Valor'], errors='coerce')
    
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
    
    required_cols = [
        "Receita Vendas ML", 
        "Receita Vendas SH", 
        "Compras de Mercadoria para Revenda", 
        "Taxa / Comissão / Fretes - makeplace", 
        "Impostos - DAS Simples Nacional"
    ]
    for col in required_cols:
        if col not in df.columns:
            df[col] = 0
    
    # Cálculo da Margem de Contribuição Ajustada por período:
    # Fórmula: (Receita Vendas ML + Receita Vendas SH) - (|Compras de Mercadoria para Revenda| +
    #         |Taxa / Comissão / Fretes - makeplace| + |Impostos - DAS Simples Nacional|)
    def calc_contribuicao_ajustada(grupo):
        receita_ml = grupo.loc[grupo["ContaContabil"] == "Receita Vendas ML", "Valor"].sum()
        receita_sh = grupo.loc[grupo["ContaContabil"] == "Receita Vendas SH", "Valor"].sum()
        total_receita = receita_ml + receita_sh
        compras = grupo.loc[grupo["ContaContabil"] == "Compras de Mercadoria para Revenda", "Valor"].sum()
        taxa = grupo.loc[grupo["ContaContabil"] == "Taxa / Comissão / Fretes - makeplace", "Valor"].sum()
        impostos = grupo.loc[grupo["ContaContabil"] == "Impostos - DAS Simples Nacional", "Valor"].sum()
        despesas = abs(compras) + abs(taxa) + abs(impostos)
        return total_receita - despesas

    df_contrib = df.groupby("Mês/Ano").apply(calc_contribuicao_ajustada).reset_index(name="Contribuição Ajustada")
    
    # Cria pivot para o gráfico de evolução
    df_pivot = df.groupby(['Mês/Ano', 'ContaContabil'])['Valor'].sum().unstack(fill_value=0).reset_index()
    df_pivot["Contribuição Ajustada"] = (
        df_pivot.get("Receita Vendas ML", 0) +
        df_pivot.get("Receita Vendas SH", 0) -
        (abs(df_pivot.get("Compras de Mercadoria para Revenda", 0)) +
         abs(df_pivot.get("Taxa / Comissão / Fretes - makeplace", 0)) +
         abs(df_pivot.get("Impostos - DAS Simples Nacional", 0)))
    )
    
    # ------------------------------
    # Card e Mini-Gráfico da Margem de Contribuição Ajustada
    # ------------------------------
    valor_total_mc = df_contrib["Contribuição Ajustada"].sum()
    idx_melhor = df_contrib["Contribuição Ajustada"].idxmax()
    melhor_mes = df_contrib.loc[idx_melhor, "Mês/Ano"]
    valor_melhor_mes = df_contrib.loc[idx_melhor, "Contribuição Ajustada"]
    
    valor_total_str = f"R$ {valor_total_mc:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    valor_melhor_mes_str = f"R$ {valor_melhor_mes:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    
    st.markdown(
        f"""
        <div class="mc-card">
            <h2 style="margin-top: 0;">Margem de Contribuição Ajustada</h2>
            <p style="font-size: 1.5rem; margin-bottom: 10px;">{valor_total_str}</p>
            <p style="margin-bottom: 10px;">Melhor mês: {melhor_mes} — {valor_melhor_mes_str}</p>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # Mini-gráfico (sparkline) da evolução da margem
    fig_spark = px.line(
        df_contrib,
        x="Mês/Ano",
        y="Contribuição Ajustada",
        markers=True,
        title=""
    )
    fig_spark.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis_title="",
        yaxis_title="",
        font=dict(color="#FFFFFF"),
        height=150
    )
    fig_spark.update_traces(line_color="#FFFFFF")
    fig_spark.update_yaxes(tickprefix="R$ ", tickformat=",.2f")
    
    st.plotly_chart(fig_spark, use_container_width=True)
    
    # ------------------------------
    # Gráfico de Evolução da Margem de Contribuição Ajustada
    # ------------------------------
    fig_evol = go.Figure()
    x_vals = df_pivot["Mês/Ano"]
    contas = ["Receita Vendas ML", "Receita Vendas SH", 
              "Compras de Mercadoria para Revenda", 
              "Taxa / Comissão / Fretes - makeplace", 
              "Impostos - DAS Simples Nacional"]
    for conta in contas:
        if conta in df_pivot.columns:
            fig_evol.add_trace(
                go.Scatter(
                    x=x_vals,
                    y=df_pivot[conta],
                    mode="lines+markers",
                    name=conta,
                    line=dict(dash="dash")
                )
            )
    fig_evol.add_trace(
        go.Scatter(
            x=x_vals,
            y=df_pivot["Contribuição Ajustada"],
            mode="lines+markers",
            name="Contribuição Ajustada",
            line=dict(dash="solid", width=3)
        )
    )
    fig_evol.update_layout(
        title="Evolução da Contribuição Ajustada (por Mês/Ano)",
        yaxis_tickprefix="R$ ",
        yaxis_tickformat=",.2f"
    )
    
    # ------------------------------
    # Novo Gráfico: Comparação (Receita Vendas ML + SH) vs (Compras de Mercadoria para Revenda)
    # ------------------------------
    df_receitas = df[df['ContaContabil'].isin(['Receita Vendas ML', 'Receita Vendas SH'])]
    df_receitas_mensal = df_receitas.groupby('Mês/Ano')['Valor'].sum().reset_index()
    df_receitas_mensal.rename(columns={'Valor': 'Receitas'}, inplace=True)
    
    df_compras = df[df['ContaContabil'] == 'Compras de Mercadoria para Revenda']
    df_compras_mensal = df_compras.groupby('Mês/Ano')['Valor'].sum().reset_index()
    df_compras_mensal['Compras'] = df_compras_mensal['Valor'].abs()
    df_compras_mensal.drop(columns=['Valor'], inplace=True)
    
    df_comp = pd.merge(df_receitas_mensal, df_compras_mensal, on='Mês/Ano', how='outer').fillna(0)
    df_comp_melt = df_comp.melt(id_vars='Mês/Ano', value_vars=['Receitas', 'Compras'],
                                var_name='Tipo', value_name='Valor')
    
    fig_comp2 = px.bar(
        df_comp_melt,
        x='Mês/Ano',
        y='Valor',
        color='Tipo',
        barmode='group',
        title='(Receita Vendas ML + SH) vs (Compras de Mercadoria para Revenda)',
        labels={'Valor': 'Valor (R$)'},
        template='plotly_white'
    )
    fig_comp2.update_yaxes(tickprefix="R$ ", tickformat=",.2f")
    
    # ------------------------------------------------------------------------------
    # Abas do Dashboard
    # ------------------------------------------------------------------------------
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Resumo", "📄 Dados", "📈 Gráficos", "💾 Exportação"])
    
    # ABA 1: Resumo por Conta Contábil
    with tab1:
        st.markdown("<h2>Resumo por Conta Contábil</h2>", unsafe_allow_html=True)
        resumo = df.groupby(['ContaContabil', 'Mês/Ano'])['Valor'].sum().reset_index()
        resumo_pivot = resumo.pivot(index='ContaContabil', columns='Mês/Ano', values='Valor').fillna(0)
        resumo_pivot['Total'] = resumo_pivot.sum(axis=1)
        resumo_pivot.sort_values(by='Total', ascending=False, inplace=True)
        total_geral = pd.DataFrame(resumo_pivot.sum(axis=0)).T
        total_geral.index = ['Total Geral']
        resumo_pivot = pd.concat([resumo_pivot, total_geral])
        with st.container():
            st.markdown("<div class='chart-container'>", unsafe_allow_html=True)
            st.table(resumo_pivot.style.format(lambda x: formata_valor_brasil(x)))
            st.markdown("</div>", unsafe_allow_html=True)
    
    # ABA 2: Dados
    with tab2:
        st.markdown("<h2>Dados Importados</h2>", unsafe_allow_html=True)
        df_sorted = df.sort_values(by='Valor', ascending=False)
        with st.container():
            st.markdown("<div class='data-container'>", unsafe_allow_html=True)
            st.table(df_sorted.style.format({'Valor': lambda x: formata_valor_brasil(x)}))
            st.markdown("</div>", unsafe_allow_html=True)
    
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
                template='plotly_white'
            )
            fig_entradas.update_layout(xaxis_tickangle=-45)
            fig_entradas.update_yaxes(tickprefix="R$ ", tickformat=",.2f")
            with st.container():
                st.markdown("<div class='chart-container'>", unsafe_allow_html=True)
                st.plotly_chart(fig_entradas, use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)
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
                template='plotly_white'
            )
            fig_saidas.update_layout(yaxis={'categoryorder': 'total ascending'})
            fig_saidas.update_xaxes(tickprefix="R$ ", tickformat=",.2f")
            with st.container():
                st.markdown("<div class='chart-container'>", unsafe_allow_html=True)
                st.plotly_chart(fig_saidas, use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)
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
                template='plotly_white'
            )
            fig_dre.update_yaxes(tickprefix="R$ ", tickformat=",.2f")
            with st.container():
                st.markdown("<div class='chart-container'>", unsafe_allow_html=True)
                st.plotly_chart(fig_dre, use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.write("Não há dados suficientes para exibir o gráfico de Entradas x Saídas.")
    
        st.subheader("Evolução da Contribuição Ajustada (por Mês/Ano)")
        with st.container():
            st.plotly_chart(fig_evol, use_container_width=True)
    
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
                template='plotly_white'
            )
            fig_comp.update_yaxes(tickprefix="R$ ", tickformat=",.2f")
            with st.container():
                st.markdown("<div class='chart-container'>", unsafe_allow_html=True)
                st.plotly_chart(fig_comp, use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.write("Não há dados para gerar a comparação entre Receitas e Impostos (DAS).")
    
    # ------------------------------------------------------------------------------
    # ABA 4: Exportação (arquivo XLSX)
    # ------------------------------------------------------------------------------
    with tab4:
        st.subheader("Exportar Resumo")
        resumo2 = df.groupby(['ContaContabil', 'Mês/Ano'])['Valor'].sum().reset_index()
        resumo_pivot2 = resumo2.pivot(index='ContaContabil', columns='Mês/Ano', values='Valor').fillna(0)
        resumo_pivot2['Total'] = resumo_pivot2.sum(axis=1)
        resumo_pivot2.sort_values(by='Total', ascending=False, inplace=True)
        total_geral = pd.DataFrame(resumo_pivot2.sum(axis=0)).T
        total_geral.index = ['Total Geral']
        resumo_pivot2 = pd.concat([resumo_pivot2, total_geral]).reset_index()
        xlsx_data = convert_df_to_xlsx(resumo_pivot2)
        st.download_button(
            label="💾 Exportar Resumo para XLSX",
            data=xlsx_data,
            file_name='Resumo_ContaContabil.xlsx',
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
else:
    st.warning("Por favor, faça o upload de um arquivo Excel para começar.")

# ------------------------------------------------------------------------------
# Footer personalizado
# ------------------------------------------------------------------------------
st.markdown('<div style="text-align:center; color:#7F8C8D; font-size:0.8rem;">Dashboard desenvolvido por [Seu Nome] - 2025</div>', unsafe_allow_html=True)

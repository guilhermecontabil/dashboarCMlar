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
    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

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
# Sidebar: Upload de arquivo e filtros
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

# ------------------------------------------------------------------------------
# Execução do Dashboard (se houver dados)
# ------------------------------------------------------------------------------
if df is not None:
    # Conversões de tipo
    df['Data'] = pd.to_datetime(df['Data'], dayfirst=True, errors='coerce')
    df['Valor'] = pd.to_numeric(df['Valor'], errors='coerce')
    
    # Filtro: Intervalo de datas
    min_date = df['Data'].min()
    max_date = df['Data'].max()
    selected_dates = st.sidebar.date_input("Selecione o intervalo de datas:", [min_date, max_date])
    if isinstance(selected_dates, list) and len(selected_dates) == 2:
        start_date, end_date = selected_dates
        df = df[(df['Data'] >= pd.to_datetime(start_date)) & (df['Data'] <= pd.to_datetime(end_date))]
    
    # Filtro: Grupo de Conta (caso exista)
    if 'GrupoDeConta' in df.columns:
        grupos_unicos = df['GrupoDeConta'].dropna().unique()
        grupo_selecionado = st.sidebar.selectbox("🗂️ Filtrar por Grupo de Conta:", ["Todos"] + list(grupos_unicos))
        if grupo_selecionado != "Todos":
            df = df[df['GrupoDeConta'] == grupo_selecionado]
    
    # Filtro: Conta Contábil
    filtro_conta = st.sidebar.text_input("🔍 Filtrar Conta Contábil:")
    if filtro_conta:
        df = df[df['ContaContabil'].str.contains(filtro_conta, case=False, na=False)]
    
    st.markdown("<hr>", unsafe_allow_html=True)
    
    # ------------------------------------------------------------------------------
    # Métricas principais
    # ------------------------------------------------------------------------------
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
    
    # ------------------------------------------------------------------------------
    # Cálculo da Contribuição Ajustada por período (consolidação por Mês/Ano)
    # ------------------------------------------------------------------------------
    # Para cada período, a Contribuição Ajustada é:
    # (Receita Vendas ML + Receita Vendas SH) - (Compras de Mercadoria para Revenda +
    # Taxa / Comissão / Fretes - makeplace + Impostos - DAS Simples Nacional)
    def calc_contribuicao_ajustada(grupo):
        receita_ml = grupo.loc[grupo["ContaContabil"] == "Receita Vendas ML", "Valor"].sum()
        receita_sh = grupo.loc[grupo["ContaContabil"] == "Receita Vendas SH", "Valor"].sum()
        compras = grupo.loc[grupo["ContaContabil"] == "Compras de Mercadoria para Revenda", "Valor"].sum()
        taxa = grupo.loc[grupo["ContaContabil"] == "Taxa / Comissão / Fretes - makeplace", "Valor"].sum()
        impostos = grupo.loc[grupo["ContaContabil"] == "Impostos - DAS Simples Nacional", "Valor"].sum()
        return (receita_ml + receita_sh) - (compras + taxa + impostos)
    
    # Cria a coluna de agrupamento "Mês/Ano"
    df['Mês/Ano'] = df['Data'].dt.to_period('M').astype(str)
    
    # Aplica a função para obter um DataFrame com a Contribuição Ajustada por período
    df_contrib = df.groupby("Mês/Ano").apply(calc_contribuicao_ajustada).reset_index(name="Contribuicao Ajustada")
    
    # ------------------------------------------------------------------------------
    # Gráfico de Composição da Contribuição Ajustada (Waterfall)
    # ------------------------------------------------------------------------------
    # Calcula os valores totais para cada conta no período filtrado (consolidado)
    receita_ml_total = df[df['ContaContabil'] == "Receita Vendas ML"]['Valor'].sum()
    receita_sh_total = df[df['ContaContabil'] == "Receita Vendas SH"]['Valor'].sum()
    compras_total = df[df['ContaContabil'] == "Compras de Mercadoria para Revenda"]['Valor'].sum()
    taxa_total = df[df['ContaContabil'] == "Taxa / Comissão / Fretes - makeplace"]['Valor'].sum()
    impostos_total = df[df['ContaContabil'] == "Impostos - DAS Simples Nacional"]['Valor'].sum()
    # O valor final (Contribuição Ajustada) será a soma dos itens acima
    # A waterfall chart usará os valores dos itens individuais e calculará o total
    measures = ["relative", "relative", "relative", "relative", "relative", "total"]
    x_labels = ["Receita Vendas ML", "Receita Vendas SH",
                "Compras de Mercadoria para Revenda",
                "Taxa / Comissão / Fretes - makeplace",
                "Impostos - DAS Simples Nacional", "Contribuição Ajustada"]
    y_values = [receita_ml_total, receita_sh_total, -compras_total, -taxa_total, -impostos_total, 0]  # último valor é ignorado para "total"
    
    fig_waterfall = go.Figure(go.Waterfall(
        measure = measures,
        x = x_labels,
        y = y_values,
        connector = {"line": {"color": "rgb(63, 63, 63)"}}
    ))
    fig_waterfall.update_layout(
        title = "Composição da Contribuição Ajustada",
        waterfallgroupgap = 0.3
    )
    
    # ------------------------------------------------------------------------------
    # Abas do Dashboard
    # ------------------------------------------------------------------------------
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Resumo", "📄 Dados", "📈 Gráficos", "💾 Exportação"])
    
    # ABA 1: Resumo
    with tab1:
        st.markdown("<h2>Resumo por Conta Contábil</h2>", unsafe_allow_html=True)
        resumo = df.groupby(['ContaContabil', 'Mês/Ano'])['Valor'].sum().reset_index()
        resumo_pivot = resumo.pivot(index='ContaContabil', columns='Mês/Ano', values='Valor').fillna(0)
        resumo_pivot['Total'] = resumo_pivot.sum(axis=1)
        resumo_pivot.sort_values(by='Total', ascending=False, inplace=True)
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
                labels={'Valor': 'Valor (R$)', 'ContaContábil': 'Conta Contábil'},
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
        if not df_contrib.empty:
            fig_contrib = px.line(
                df_contrib,
                x='Mês/Ano',
                y="Contribuicao Ajustada",
                title="Evolução da Contribuição Ajustada",
                markers=True,
                labels={'Contribuicao Ajustada': 'Contribuição Ajustada (R$)'},
                template='plotly_white'
            )
            fig_contrib.update_yaxes(tickprefix="R$ ", tickformat=",.2f")
            with st.container():
                st.markdown("<div class='chart-container'>", unsafe_allow_html=True)
                st.plotly_chart(fig_contrib, use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.write("Não há dados para exibir a Contribuição Ajustada.")
    
        st.subheader("Composição da Contribuição Ajustada")
        # Exibe o gráfico waterfall com os componentes do cálculo
        with st.container():
            st.plotly_chart(fig_waterfall, use_container_width=True)
    
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

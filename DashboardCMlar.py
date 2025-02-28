import streamlit as st
import pandas as pd
import plotly.express as px
import streamlit.components.v1 as components

# Configuração da página
st.set_page_config(page_title="Dashboard Movimento - Atualizado", layout="wide")

# Custom CSS para estilos
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto&display=swap');
    html, body, [class*="css"] {
        font-family: 'Roboto', sans-serif;
    }
    .header {
        text-align: center;
        padding: 20px;
        background: linear-gradient(135deg, #6a11cb, #2575fc);
        color: white;
        border-radius: 10px;
        margin-bottom: 20px;
    }
    .chart-container, .data-container, .metrics-container {
        background: white;
        padding: 20px;
        border-radius: 8px;
        margin-bottom: 20px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }
    </style>
    """, unsafe_allow_html=True
)

# Cabeçalho com HTML customizado
components.html(
    """
    <div class="header">
        <h1>Dashboard Movimento - Atualizado</h1>
        <p>Análise detalhada dos dados do arquivo de movimento</p>
    </div>
    """, height=150
)

# Sidebar: upload e filtros
st.sidebar.markdown("## Filtros de Dados")
uploaded_file = st.sidebar.file_uploader("Selecione o arquivo XLSX", type=["xlsx"])

# Exemplo de dicionário para mapear códigos a descrições (adicione conforme necessário)
codigo_para_descricao = {
    111: "Aluguel",
    112: "Assessorias e associações",
    113: "Cartório",
    # ... inclua demais mapeamentos
    211: "Vendas de produtos",
    212: "Vendas no balcão",
}

if uploaded_file is not None:
    try:
        # Leitura do arquivo Excel
        df = pd.read_excel(uploaded_file)
        
        # Verifica e ajusta a coluna de data
        if "Data" not in df.columns:
            if "Data Movimento" in df.columns:
                df.rename(columns={"Data Movimento": "Data"}, inplace=True)
            else:
                st.error("Coluna de data não encontrada. Verifique o arquivo.")
                st.stop()
        
        # Converte a coluna de data (formato DD/MM/YYYY)
        df["Data"] = pd.to_datetime(df["Data"], dayfirst=True, errors="coerce")
        df = df[df["Data"].notnull()]  # Remove linhas com data inválida
        df.sort_values("Data", inplace=True)
        
        # Mapeia a coluna "Codigo" para "Descricao", se existir; caso contrário, espera que a coluna "Descricao" já exista
        if "Codigo" in df.columns:
            df["Descricao"] = df["Codigo"].map(codigo_para_descricao).fillna("Código Desconhecido")
        elif "Descricao" not in df.columns:
            st.warning("Nenhuma coluna 'Codigo' ou 'Descricao' encontrada. As categorias não poderão ser filtradas.")
        
        # Filtro de datas na sidebar
        min_date = df["Data"].min().date()
        max_date = df["Data"].max().date()
        date_range = st.sidebar.date_input("Selecione o intervalo de datas", [min_date, max_date])
        if isinstance(date_range, list) and len(date_range) == 2:
            start_date, end_date = date_range
            df = df[(df["Data"].dt.date >= start_date) & (df["Data"].dt.date <= end_date)]
        
        # Filtro de categoria (descrição) se existir
        if "Descricao" in df.columns:
            categorias = sorted(df["Descricao"].unique())
            selected_categorias = st.sidebar.multiselect("Selecione as categorias:", categorias, default=categorias)
            df = df[df["Descricao"].isin(selected_categorias)]
        
        # Nova funcionalidade: Cards de métricas
        st.markdown("## Resumo Geral")
        with st.container():
            col1, col2, col3 = st.columns(3)
            total_valor = df["Valor"].sum() if "Valor" in df.columns else 0
            total_registros = df.shape[0]
            media_valor = df["Valor"].mean() if "Valor" in df.columns and total_registros > 0 else 0
            
            col1.metric("Total Valor", f"R$ {total_valor:,.2f}")
            col2.metric("Total Registros", total_registros)
            col3.metric("Média Valor", f"R$ {media_valor:,.2f}")
        
        # Cria abas para Dashboard e Visualização dos Dados
        tabs = st.tabs(["Dashboard", "Visualização dos Dados"])
        
        # Aba "Dashboard" com gráficos
        with tabs[0]:
            # Gráfico de linha: Evolução do Valor ao longo do tempo
            if "Valor" in df.columns:
                fig_line = px.line(df, x="Data", y="Valor", title="Evolução do Valor ao longo do Tempo",
                                   markers=True, template="plotly_white")
                fig_line.update_yaxes(tickformat=",.2f", exponentformat="none")
                fig_line.update_traces(hovertemplate="%{y:,.2f}")
                st.markdown("<div class='chart-container'>", unsafe_allow_html=True)
                st.plotly_chart(fig_line, use_container_width=True, config={"locale": "pt-BR"})
                st.markdown("</div>", unsafe_allow_html=True)
            else:
                st.warning("Coluna 'Valor' não encontrada para gerar gráfico de linha.")
            
            # Gráfico de barras: Valor agregado por categoria
            if "Descricao" in df.columns and "Valor" in df.columns:
                df_agg = df.groupby("Descricao", as_index=False)["Valor"].sum()
                fig_bar = px.bar(df_agg, x="Descricao", y="Valor", title="Valor Total por Categoria",
                                 template="plotly_white")
                fig_bar.update_yaxes(tickformat=",.2f", exponentformat="none")
                fig_bar.update_traces(hovertemplate="%{y:,.2f}")
                st.markdown("<div class='chart-container'>", unsafe_allow_html=True)
                st.plotly_chart(fig_bar, use_container_width=True, config={"locale": "pt-BR"})
                st.markdown("</div>", unsafe_allow_html=True)
        
        # Aba "Visualização dos Dados" com a tabela
        with tabs[1]:
            st.markdown("<div class='data-container'>", unsafe_allow_html=True)
            st.subheader("Tabela de Dados")
            st.dataframe(df)
            st.markdown("</div>", unsafe_allow_html=True)
        
    except Exception as e:
        st.error(f"Ocorreu um erro ao processar o arquivo: {e}")
else:
    st.sidebar.info("Aguardando o upload do arquivo XLSX.")
    st.info("Utilize a barra lateral para carregar o arquivo e configurar os filtros.")

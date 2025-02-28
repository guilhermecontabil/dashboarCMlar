import streamlit as st
import pandas as pd
import plotly.express as px
import streamlit.components.v1 as components

st.set_page_config(page_title="Novo Dashboard", layout="wide")

# Exemplo de dicionário de códigos -> descrições
codigo_para_descricao = {
    111: "Aluguel",
    112: "Assessorias e associações",
    113: "Cartório",
    # ...
    211: "Vendas de produtos",
    212: "Vendas no balcão",
    # ...
}

# Função para formatar valores no padrão BR
def format_brl(x):
    try:
        if pd.isna(x) or (isinstance(x, (int, float)) and x == 0):
            return ""
        return format(x, ",.2f").replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return x

# Cabeçalho / CSS
st.markdown(
    """
    <style>
    /* Estilos de exemplo */
    .header {
        text-align: center;
        padding: 30px;
        background: linear-gradient(135deg, #6a11cb, #2575fc);
        color: white;
        border-radius: 10px;
        margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True
)

components.html(
    """
    <div class="header">
        <h1>Novo Dashboard</h1>
        <p>Exemplo de Dashboard com Códigos e Descrições</p>
    </div>
    """,
    height=150
)

# Sidebar para upload
st.sidebar.markdown("## Filtros de Dados")
uploaded_file = st.sidebar.file_uploader("Selecione o arquivo XLSX", type=["xlsx"])

if uploaded_file is not None:
    try:
        # Leitura do Excel
        df = pd.read_excel(uploaded_file)

        # Ajuste de nomes de colunas, se necessário
        # Vamos assumir que as colunas estão nomeadas como: "Data", "Codigo", "Valor"
        # Se forem diferentes, renomeie: df.rename(columns={"MÊS": "Data", ...}, inplace=True)

        # Converte coluna Data (caso esteja em formato string)
        # Se precisar de parsing específico, use to_datetime com format ou errors='coerce'
        df["Data"] = pd.to_datetime(df["Data"], errors='coerce')
        
        # Remove linhas sem data válida
        df = df[df["Data"].notnull()]

        # Ordena pelo campo de data
        df.sort_values("Data", inplace=True)

        # Mapeia o código para descrição
        df["Descricao"] = df["Codigo"].map(codigo_para_descricao).fillna("Código Desconhecido")

        # Filtro de intervalo de datas
        min_date = df["Data"].min().date()
        max_date = df["Data"].max().date()
        date_range = st.sidebar.date_input("Selecione o intervalo de datas", [min_date, max_date])
        if isinstance(date_range, list) and len(date_range) == 2:
            start_date, end_date = date_range
            df = df[(df["Data"].dt.date >= start_date) & (df["Data"].dt.date <= end_date)]
        
        # Agora selecionamos quais categorias (descrições) queremos ver nos gráficos
        todas_categorias = sorted(df["Descricao"].unique())
        selected_categorias = st.sidebar.multiselect("Selecione as categorias (códigos):", 
                                                    todas_categorias, 
                                                    default=todas_categorias)

        # Filtra o DataFrame pelas categorias selecionadas
        df_filtered = df[df["Descricao"].isin(selected_categorias)]

        # Cria abas
        tabs = st.tabs(["Dashboard", "Visualização dos Dados"])
        
        with tabs[0]:
            st.markdown("## Gráficos")
            # Exemplo: agrupar por data e descrição para somar valores
            # (Dependendo da sua necessidade, você pode fazer pivot para ter uma curva por categoria)
            
            # Vamos fazer um pivot para plotar linhas empilhadas ou sobrepostas
            if not df_filtered.empty:
                pivot_df = df_filtered.pivot_table(
                    index="Data",
                    columns="Descricao",
                    values="Valor",
                    aggfunc="sum"
                ).fillna(0)

                # Gráfico de linha com Plotly
                fig = px.line(
                    pivot_df,
                    x=pivot_df.index,
                    y=pivot_df.columns,
                    title="Evolução das Categorias Selecionadas",
                    markers=True,
                    template="plotly_white"
                )
                # Ajusta formatação do eixo Y
                fig.update_yaxes(tickformat=",.2f", exponentformat="none")
                # Ajusta tooltip
                fig.update_traces(hovertemplate="%{y:,.2f}")
                st.plotly_chart(fig, use_container_width=True, config={"locale": "pt-BR"})
            else:
                st.warning("Não há dados para as categorias selecionadas neste intervalo.")

        with tabs[1]:
            st.markdown("## Tabela de Dados")
            # Exibe tabela
            if not df_filtered.empty:
                # Para exibir os valores formatados
                display_df = df_filtered.copy()
                # Você pode agrupar por Data e Descrição para mostrar o total
                # ou simplesmente mostrar linha a linha
                
                # Exemplo: agrupar por Data, Descrição e somar Valor
                grouped_df = display_df.groupby(["Data","Descricao"], as_index=False)["Valor"].sum()
                # Formata
                grouped_df["Valor"] = grouped_df["Valor"].apply(format_brl)
                
                st.dataframe(grouped_df)
            else:
                st.warning("Não há dados para exibir na tabela.")

    except Exception as e:
        st.error(f"Erro ao processar o arquivo: {e}")
else:
    st.sidebar.info("Aguardando o upload de um arquivo XLSX.")
    st.info("Utilize a barra lateral para carregar o arquivo e configurar os filtros.")

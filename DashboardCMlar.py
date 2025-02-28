import streamlit as st
import pandas as pd
import plotly.express as px
import traceback

# ------------------------------------------------------------------------------
# Configuração da página
# ------------------------------------------------------------------------------
st.set_page_config(page_title="Dashboard Financeiro", layout="wide")

# ------------------------------------------------------------------------------
# CSS customizado para Dark Mode
# ------------------------------------------------------------------------------
st.markdown(
    """
    <style>
    /* Fonte e fundo escuro */
    @import url('https://fonts.googleapis.com/css2?family=Roboto&display=swap');
    html, body, [class*="css"] {
        font-family: 'Roboto', sans-serif;
        background-color: #121212;
        color: #e0e0e0;
    }
    .main {
        background-color: #121212;
    }
    /* Título */
    .titulo {
        text-align: center;
        padding: 20px;
        background: #1f1f1f;
        border-radius: 8px;
        margin-bottom: 20px;
    }
    /* Containers dos gráficos e tabelas */
    .container {
        background: #1e1e1e;
        padding: 20px;
        border-radius: 8px;
        margin-bottom: 20px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.3);
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ------------------------------------------------------------------------------
# Título
# ------------------------------------------------------------------------------
st.markdown("<div class='titulo'><h1>Dashboard Financeiro</h1></div>", unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# Barra Lateral: Upload dos arquivos
# ------------------------------------------------------------------------------
st.sidebar.title("Uploads")

plano_file = st.sidebar.file_uploader("Carregar arquivo do Plano de Contas (XLSX ou CSV)", type=["xlsx", "csv"])
dados_file = st.sidebar.file_uploader("Carregar arquivo de Dados Financeiros (XLSX ou CSV)", type=["xlsx", "csv"])

if plano_file and dados_file:
    try:
        # =======================================================================
        # 1. Leitura e tratamento do Plano de Contas
        # =======================================================================
        if plano_file.name.endswith(".xlsx"):
            df_plano = pd.read_excel(plano_file)
        else:
            df_plano = pd.read_csv(plano_file)
        
        # Remove espaços e converte colunas para minúsculo
        df_plano.columns = df_plano.columns.str.strip().str.lower()
        
        # Renomeia, se necessário
        rename_map_plano = {
            'codcontacontabil': 'CodContaContabil',
            'contacontabil': 'ContaContabil'
        }
        for k, v in rename_map_plano.items():
            if k in df_plano.columns:
                df_plano.rename(columns={k: v}, inplace=True)
        
        # Verifica colunas obrigatórias
        required_plano = {"CodContaContabil", "ContaContabil"}
        missing_plano = required_plano - set(df_plano.columns)
        if missing_plano:
            st.error(f"O Plano de Contas deve ter as colunas {missing_plano}.")
            st.stop()
        
        # =======================================================================
        # 2. Leitura e tratamento dos Dados Financeiros
        # =======================================================================
        if dados_file.name.endswith(".xlsx"):
            df_dados = pd.read_excel(dados_file)
        else:
            df_dados = pd.read_csv(dados_file)
        
        # Remove espaços e converte colunas para minúsculo
        df_dados.columns = df_dados.columns.str.strip().str.lower()
        
        # Renomeia para o padrão interno
        rename_map_dados = {
            'data': 'DATA',
            'codcontacontabil': 'CodContaContabil',
            'valor': 'Valor',
            'descrição': 'Descricao',
            'tipo': 'Tipo'
        }
        for k, v in rename_map_dados.items():
            if k in df_dados.columns:
                df_dados.rename(columns={k: v}, inplace=True)
        
        # Verifica colunas obrigatórias
        required_dados = {"DATA", "CodContaContabil", "Valor", "Descricao", "Tipo"}
        missing_dados = required_dados - set(df_dados.columns)
        if missing_dados:
            st.error(f"O arquivo de dados deve ter as colunas {missing_dados}.")
            st.stop()
        
        # =======================================================================
        # 3. Converte a coluna Valor para numérico
        # =======================================================================
        df_dados["Valor"] = df_dados["Valor"].astype(str)
        df_dados["Valor"] = df_dados["Valor"].str.replace('.', '', regex=False)  # remove pontos de milhar
        df_dados["Valor"] = df_dados["Valor"].str.replace(',', '.', regex=False) # troca vírgula por ponto
        df_dados["Valor"] = pd.to_numeric(df_dados["Valor"], errors='coerce')
        
        # =======================================================================
        # 4. Tenta converter a coluna DATA para datas (opcional)
        # =======================================================================
        # Se já estiver em formato data, não há problema. Caso seja string, tentamos converter.
        # Ajuste o formato se necessário, ou remova se não precisar.
        df_dados["DATA"] = pd.to_datetime(df_dados["DATA"], errors='coerce')
        
        # =======================================================================
        # 5. Merge: correlaciona com base em CodContaContabil
        # =======================================================================
        df_merged = pd.merge(
            df_dados,
            df_plano[["CodContaContabil", "ContaContabil"]],
            on="CodContaContabil",
            how="left"
        )
        
        # =======================================================================
        # 6. Cálculos de métricas simples
        # =======================================================================
        # Mapeamos 'Tipo' = 'C' (Receita) e 'D' (Despesa)
        df_merged["Tipo"] = df_merged["Tipo"].str.upper()
        
        total_receita = df_merged.loc[df_merged["Tipo"] == "C", "Valor"].sum()
        total_despesa = df_merged.loc[df_merged["Tipo"] == "D", "Valor"].sum()
        saldo = total_receita - total_despesa
        
        # =======================================================================
        # 7. Exibição de Dashboard
        # =======================================================================
        st.subheader("Métricas Gerais")
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Receita", f"{total_receita:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        col2.metric("Total Despesa", f"{total_despesa:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        col3.metric("Saldo", f"{saldo:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        
        # Gráfico de barras: Total por Conta
        df_por_conta = df_merged.groupby("ContaContabil")["Valor"].sum().reset_index()
        fig = px.bar(
            df_por_conta,
            x="ContaContabil",
            y="Valor",
            title="Total por ContaContabil",
            template="plotly_dark"
        )
        
        st.markdown("<div class='container'>", unsafe_allow_html=True)
        st.plotly_chart(fig, use_container_width=True, config={"locale": "pt-BR"})
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Tabela com os dados finais
        st.markdown("<div class='container'>", unsafe_allow_html=True)
        st.subheader("Dados Consolidados (Merge)")
        
        # Exemplo: exibe as primeiras 20 linhas
        st.dataframe(df_merged.head(20))
        st.markdown("</div>", unsafe_allow_html=True)
        
    except Exception as e:
        st.error(f"Erro ao processar os arquivos: {e}")
        st.text(traceback.format_exc())
else:
    st.info("Carregue o Plano de Contas e o Arquivo de Dados Financeiros na barra lateral.")

import streamlit as st
import pandas as pd
import plotly.express as px
import streamlit.components.v1 as components
import traceback

# ------------------------------------------------------------------------------
# Configuração da página
# ------------------------------------------------------------------------------
st.set_page_config(page_title="Dashboard Fiscal Avançada", layout="wide")

# ------------------------------------------------------------------------------
# CSS customizado para melhorar a interface
# ------------------------------------------------------------------------------
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;700&family=Roboto&display=swap');
    html, body, [class*="css"]  {
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
# Header customizado
# ------------------------------------------------------------------------------
components.html(
    """
    <div class="header">
        <h1>Dashboard Fiscal Avançada</h1>
        <p>Integre e analise seus dados financeiros com um Plano de Contas embutido</p>
    </div>
    """, 
    height=150
)

# ------------------------------------------------------------------------------
# Funções auxiliares
# ------------------------------------------------------------------------------
def converter_mes(valor):
    """Tenta converter a coluna de mês para datetime utilizando vários formatos."""
    formatos = ["%Y-%m", "%m/%Y", "%B %Y", "%b %Y"]  # Exemplos: "2023-05", "05/2023", "Maio 2023", "May 2023"
    for fmt in formatos:
        try:
            return pd.to_datetime(valor, format=fmt)
        except (ValueError, TypeError):
            continue
    return pd.NaT

def format_brl(x):
    """Formata números para o padrão BR (ponto para milhar e vírgula para decimal)."""
    try:
        if pd.isna(x) or (isinstance(x, (int, float)) and x == 0):
            return ""
        return format(x, ",.2f").replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return x

# ------------------------------------------------------------------------------
# Plano de Contas embutido (ajuste conforme a sua necessidade)
# ------------------------------------------------------------------------------
default_plano = {
    "CodContaContabil": [1001, 2001, 3001, 4001],
    "ContaContabil": [
        "Receita de Vendas",
        "Despesa Administrativa",
        "Despesa Operacional",
        "Outras Receitas"
    ]
}
df_plano = pd.DataFrame(default_plano)
df_plano.columns = df_plano.columns.str.strip()  # Limpa espaços nos nomes das colunas

# ------------------------------------------------------------------------------
# Sidebar: Upload do arquivo de Dados Financeiros
# ------------------------------------------------------------------------------
st.sidebar.markdown("## Upload do Arquivo de Dados Financeiros")
dados_file = st.sidebar.file_uploader("Selecione o arquivo de Dados Financeiros (XLSX ou CSV)", type=["xlsx", "csv"], key="dados")

if dados_file is not None:
    try:
        # Leitura do arquivo de Dados Financeiros
        if dados_file.name.endswith('.xlsx'):
            df = pd.read_excel(dados_file)
        else:
            df = pd.read_csv(dados_file)
        
        # Normaliza os nomes das colunas (remove espaços e converte para minúsculas)
        df.columns = df.columns.str.strip().str.lower()
        
        # Renomeia para o padrão esperado no código
        # Ajuste conforme os nomes reais das colunas no seu arquivo
        rename_map = {
            'codcontacontabil': 'CodContaContabil',
            'tipo': 'Tipo',
            'valor': 'Valor',
            'mês': 'MÊS',           # Se a coluna vier como "MÊS" (minúsculo ou maiúsculo)
            'data': 'DATA',         # Caso precise
            'descrição': 'DESCRICAO' # Caso precise
        }
        for k, v in rename_map.items():
            if k in df.columns:
                df.rename(columns={k: v}, inplace=True)
        
        # Agora, checamos a existência das colunas necessárias
        required_cols = {"CodContaContabil", "Tipo", "Valor"}
        missing_cols = required_cols - set(df.columns)
        if missing_cols:
            st.error(f"O arquivo de dados deve conter as colunas {missing_cols}.")
            st.stop()
        
        # Checar se a coluna Tipo tem apenas D ou C
        valores_validos = {"D", "C"}
        # Converte a coluna "Tipo" para maiúsculo, caso venha misturado
        df["Tipo"] = df["Tipo"].astype(str).str.upper()
        if not set(df["Tipo"].unique()).issubset(valores_validos):
            st.error("A coluna 'Tipo' deve conter apenas 'D' ou 'C'.")
            st.stop()
        
        # Processamento da data, se a coluna "MÊS" existir (agora em maiúsculo)
        if "MÊS" in df.columns:
            df["Data"] = df["MÊS"].apply(converter_mes)
            if df["Data"].isnull().all():
                st.warning("Não foi possível converter a coluna 'MÊS' para data. Usaremos os valores originais.")
                x_axis = "MÊS"
                df.sort_values("MÊS", inplace=True)
            else:
                df = df[df["Data"].notnull()]
                df.sort_values("Data", inplace=True)
                x_axis = "Data"
                df["MÊS_FORMATADO"] = df["Data"].dt.strftime("%m/%Y")
                # Filtro de intervalo de datas
                min_date = df["Data"].min().date()
                max_date = df["Data"].max().date()
                date_range = st.sidebar.date_input("Selecione o intervalo de datas", [min_date, max_date])
                if isinstance(date_range, list) and len(date_range) == 2:
                    start_date, end_date = date_range
                    df = df[(df["Data"].dt.date >= start_date) & (df["Data"].dt.date <= end_date)]
        else:
            # Se não existir a coluna "MÊS", consideramos o eixo X como CodContaContabil
            x_axis = "CodContaContabil"
        
        # ------------------------------------------------------------------------------
        # Merge: Correlaciona os dados financeiros com o Plano de Contas embutido
        # ------------------------------------------------------------------------------
        df = pd.merge(
            df, 
            df_plano[["CodContaContabil", "ContaContabil"]],
            on="CodContaContabil",
            how="left"
        )
        
        # Mapeia o tipo de lançamento: "D" para Despesa e "C" para Receita
        df['Tipo_Descricao'] = df['Tipo'].map({'D': 'Despesa', 'C': 'Receita'})
        
        # ------------------------------------------------------------------------------
        # Cálculo de Métricas Gerais
        # ------------------------------------------------------------------------------
        total_receita = df.loc[df['Tipo'] == 'C', 'Valor'].sum()
        total_despesa = df.loc[df['Tipo'] == 'D', 'Valor'].sum()
        saldo = total_receita - total_despesa
        
        # ------------------------------------------------------------------------------
        # Criação de abas: Dashboard e Relatório Consolidado
        # ------------------------------------------------------------------------------
        tabs = st.tabs(["Dashboard", "Relatório Consolidado"])
        
        # ------------------------------------------------------------------------------
        # Aba "Dashboard": Métricas e Gráficos Interativos
        # ------------------------------------------------------------------------------
        with tabs[0]:
            st.markdown("## Métricas Gerais")
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Receita", format_brl(total_receita))
            col2.metric("Total Despesa", format_brl(total_despesa))
            col3.metric("Saldo", format_brl(saldo))
            
            # Gráfico: Evolução de Valores (Receitas e Despesas) se houver data
            if x_axis in ["Data", "MÊS"]:
                df_line = df.copy()
                # Agrupa por data e tipo de lançamento
                df_line = df_line.groupby([x_axis, 'Tipo_Descricao'])['Valor'].sum().reset_index()
                fig_line = px.line(
                    df_line,
                    x=x_axis,
                    y="Valor",
                    color="Tipo_Descricao",
                    title="Evolução de Receitas e Despesas",
                    markers=True,
                    template="plotly_white"
                )
                fig_line.update_yaxes(tickformat=',.2f', exponentformat='none')
                fig_line.update_traces(hovertemplate='%{y:,.2f}')
                st.markdown("<div class='chart-container'>", unsafe_allow_html=True)
                st.plotly_chart(fig_line, use_container_width=True, config={"locale": "pt-BR"})
                st.markdown("</div>", unsafe_allow_html=True)
            
            # Gráfico: Proporção de Receitas vs Despesas
            df_pie = pd.DataFrame({
                "Categoria": ["Receita", "Despesa"],
                "Valor": [total_receita, total_despesa]
            })
            fig_pie = px.pie(
                df_pie,
                values="Valor",
                names="Categoria",
                title="Proporção de Receitas vs Despesas",
                template="plotly_white"
            )
            st.markdown("<div class='chart-container'>", unsafe_allow_html=True)
            st.plotly_chart(fig_pie, use_container_width=True, config={"locale": "pt-BR"})
            st.markdown("</div>", unsafe_allow_html=True)
        
        # ------------------------------------------------------------------------------
        # Aba "Relatório Consolidado": Tabela com agrupamento por Conta e Tipo
        # ------------------------------------------------------------------------------
        with tabs[1]:
            st.markdown("<div class='data-container'>", unsafe_allow_html=True)
            st.subheader("Relatório Consolidado por Conta")
            
            # Agrupa os dados por conta e tipo de lançamento, somando os valores
            relatorio = df.groupby(["ContaContabil", "Tipo_Descricao"])["Valor"].sum().reset_index()
            relatorio["Valor"] = relatorio["Valor"].apply(format_brl)
            st.dataframe(relatorio)
            st.markdown("</div>", unsafe_allow_html=True)
            
            # Exibe os dados detalhados com o merge efetuado
            st.markdown("<div class='data-container'>", unsafe_allow_html=True)
            st.subheader("Dados Detalhados")
            
            display_df = df.copy()
            # Se existir a coluna de data formatada, usa para exibição
            if "MÊS_FORMATADO" in display_df.columns:
                display_df["MÊS"] = display_df["MÊS_FORMATADO"]
            
            # Remove colunas auxiliares
            for col_to_drop in ["Data", "MÊS_FORMATADO"]:
                if col_to_drop in display_df.columns:
                    display_df.drop(col_to_drop, axis=1, inplace=True)
            
            # Adiciona uma linha total para colunas numéricas
            total_values = {}
            for col in display_df.columns:
                if pd.api.types.is_numeric_dtype(display_df[col]):
                    total_values[col] = display_df[col].sum()
                else:
                    total_values[col] = "Total" if col.upper() == "MÊS" else ""
            total_df = pd.DataFrame(total_values, index=["Total"])
            display_df = pd.concat([display_df, total_df])
            
            # Aplica formatação BR
            display_df = display_df.applymap(
                lambda x: "" if (isinstance(x, (int, float)) and (pd.isna(x) or x == 0))
                else format_brl(x) if isinstance(x, (int, float))
                else x
            )
            st.dataframe(display_df)
            st.markdown("</div>", unsafe_allow_html=True)
            
    except Exception as e:
        st.error(f"Erro ao processar o arquivo: {e}")
        st.text(traceback.format_exc())
else:
    st.sidebar.info("Aguardando o upload do arquivo de Dados Financeiros.")
    st.info("Utilize a barra lateral para carregar o arquivo e configurar os filtros.")

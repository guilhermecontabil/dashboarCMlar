import streamlit as st
import pandas as pd
import plotly.express as px
import streamlit.components.v1 as components
import traceback

# ------------------------------------------------------------------------------
# Configuração da Página
# ------------------------------------------------------------------------------
st.set_page_config(page_title="Dashboard Fiscal Avançada", layout="wide")

# ------------------------------------------------------------------------------
# CSS Customizado
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
# Header Customizado
# ------------------------------------------------------------------------------
components.html(
    """
    <div class="header">
        <h1>Dashboard Fiscal Avançada</h1>
        <p>Correlacione seus lançamentos com o Plano de Contas</p>
    </div>
    """, height=150
)

# ------------------------------------------------------------------------------
# Funções Auxiliares
# ------------------------------------------------------------------------------
def converter_mes(valor):
    """Tenta converter a coluna de mês para datetime utilizando vários formatos."""
    formatos = ["%Y-%m", "%m/%Y", "%B %Y", "%b %Y"]
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
# Sidebar: Upload dos Arquivos
# ------------------------------------------------------------------------------
st.sidebar.markdown("## Upload dos Arquivos")

# Upload do Plano de Contas
plano_file = st.sidebar.file_uploader("Selecione o arquivo do Plano de Contas (XLSX ou CSV)", type=["xlsx", "csv"], key="plano")
# Upload dos Dados Financeiros
dados_file = st.sidebar.file_uploader("Selecione o arquivo de Dados Financeiros (XLSX ou CSV)", type=["xlsx", "csv"], key="dados")

if plano_file is not None and dados_file is not None:
    try:
        # ------------------------------------------------------------------------------
        # Leitura do Plano de Contas
        # ------------------------------------------------------------------------------
        if plano_file.name.endswith('.xlsx'):
            df_plano = pd.read_excel(plano_file)
        else:
            df_plano = pd.read_csv(plano_file)
        
        # Normaliza os nomes das colunas e remove espaços
        df_plano.columns = df_plano.columns.str.strip().str.lower()
        # Renomeia para o padrão esperado
        rename_map_plano = {
            'codcontacontabil': 'CodContaContabil',
            'contacontabil': 'ContaContabil'
        }
        for k, v in rename_map_plano.items():
            if k in df_plano.columns:
                df_plano.rename(columns={k: v}, inplace=True)
        
        # Verifica se o Plano de Contas possui as colunas necessárias
        required_plano = {"CodContaContabil", "ContaContabil"}
        missing_plano = required_plano - set(df_plano.columns)
        if missing_plano:
            st.error(f"O arquivo do Plano de Contas deve conter as colunas {missing_plano}.")
            st.stop()
        
        # ------------------------------------------------------------------------------
        # Leitura dos Dados Financeiros
        # ------------------------------------------------------------------------------
        if dados_file.name.endswith('.xlsx'):
            df = pd.read_excel(dados_file)
        else:
            df = pd.read_csv(dados_file)
        
        # Normaliza os nomes das colunas: remove espaços e converte para minúsculas
        df.columns = df.columns.str.strip().str.lower()
        rename_map_dados = {
            'codcontacontabil': 'CodContaContabil',
            'tipo': 'Tipo',
            'valor': 'Valor',
            'mês': 'MÊS',    # se existir
            'data': 'DATA',
            'descrição': 'DESCRICAO'
        }
        for k, v in rename_map_dados.items():
            if k in df.columns:
                df.rename(columns={k: v}, inplace=True)
        
        # Verifica se o arquivo de dados possui as colunas necessárias
        required_dados = {"CodContaContabil", "Tipo", "Valor"}
        missing_dados = required_dados - set(df.columns)
        if missing_dados:
            st.error(f"O arquivo de dados deve conter as colunas {missing_dados}.")
            st.stop()
        
        # ------------------------------------------------------------------------------
        # Tratamento da Coluna Tipo
        # ------------------------------------------------------------------------------
        df["Tipo"] = df["Tipo"].astype(str).str.upper()
        if not set(df["Tipo"].unique()).issubset({"D", "C"}):
            st.error("A coluna 'Tipo' deve conter apenas 'D' (Despesa) ou 'C' (Receita).")
            st.stop()
        
        # ------------------------------------------------------------------------------
        # Conversão da Coluna Valor para Numérico
        # ------------------------------------------------------------------------------
        df["Valor"] = df["Valor"].astype(str)
        df["Valor"] = df["Valor"].str.replace('.', '', regex=False)
        df["Valor"] = df["Valor"].str.replace(',', '.', regex=False)
        df["Valor"] = pd.to_numeric(df["Valor"], errors='coerce')
        
        # ------------------------------------------------------------------------------
        # Processamento da Data, se a Coluna "MÊS" existir
        # ------------------------------------------------------------------------------
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
                # Filtro de intervalo de datas na sidebar
                min_date = df["Data"].min().date()
                max_date = df["Data"].max().date()
                date_range = st.sidebar.date_input("Selecione o intervalo de datas", [min_date, max_date])
                if isinstance(date_range, list) and len(date_range) == 2:
                    start_date, end_date = date_range
                    df = df[(df["Data"].dt.date >= start_date) & (df["Data"].dt.date <= end_date)]
        else:
            x_axis = "CodContaContabil"
        
        # ------------------------------------------------------------------------------
        # Merge: Correlaciona os Dados Financeiros com o Plano de Contas
        # ------------------------------------------------------------------------------
        df = pd.merge(
            df,
            df_plano[["CodContaContabil", "ContaContabil"]],
            on="CodContaContabil",
            how="left"
        )
        
        # Se desejar, exiba os dados do merge para conferência:
        # st.write(df.head())
        
        # ------------------------------------------------------------------------------
        # Filtro (Opcional): Seleciona as contas a serem analisadas, a partir do plano
        # ------------------------------------------------------------------------------
        contas_disponiveis = df_plano["ContaContabil"].unique().tolist()
        contas_selecionadas = st.sidebar.multiselect("Selecione as Contas para Análise:",
                                                     options=contas_disponiveis,
                                                     default=contas_disponiveis)
        df = df[df["ContaContabil"].isin(contas_selecionadas)]
        
        # ------------------------------------------------------------------------------
        # Mapeamento do Tipo: "D" para Despesa, "C" para Receita
        # ------------------------------------------------------------------------------
        df['Tipo_Descricao'] = df['Tipo'].map({'D': 'Despesa', 'C': 'Receita'})
        
        # ------------------------------------------------------------------------------
        # Cálculo de Métricas Gerais
        # ------------------------------------------------------------------------------
        total_receita = df.loc[df['Tipo'] == 'C', 'Valor'].sum()
        total_despesa = df.loc[df['Tipo'] == 'D', 'Valor'].sum()
        saldo = total_receita - total_despesa
        
        # Agrupamento por conta para gráfico de barras
        df_agg = df.groupby("ContaContabil")["Valor"].sum().reset_index()
        df_agg["Valor"] = df_agg["Valor"].apply(format_brl)
        
        # ------------------------------------------------------------------------------
        # Criação de Abas: Dashboard e Relatório Consolidado
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
            
            # Gráfico: Evolução dos Lançamentos por Conta (se houver data)
            if x_axis in ["Data", "MÊS"]:
                df_line = df.copy()
                df_line = df_line.groupby([x_axis, "ContaContabil"])["Valor"].sum().reset_index()
                fig_line = px.line(
                    df_line,
                    x=x_axis,
                    y="Valor",
                    color="ContaContabil",
                    title="Evolução dos Lançamentos por Conta",
                    markers=True,
                    template="plotly_white"
                )
                fig_line.update_yaxes(tickformat=',.2f', exponentformat='none')
                fig_line.update_traces(hovertemplate='%{y:,.2f}')
                st.markdown("<div class='chart-container'>", unsafe_allow_html=True)
                st.plotly_chart(fig_line, use_container_width=True, config={"locale": "pt-BR"})
                st.markdown("</div>", unsafe_allow_html=True)
            
            # Gráfico: Total de Lançamentos por Conta (Barras)
            fig_bar = px.bar(
                df_agg,
                x="ContaContabil",
                y="Valor",
                title="Total de Lançamentos por Conta",
                template="plotly_white"
            )
            st.markdown("<div class='chart-container'>", unsafe_allow_html=True)
            st.plotly_chart(fig_bar, use_container_width=True, config={"locale": "pt-BR"})
            st.markdown("</div>", unsafe_allow_html=True)
        
        # ------------------------------------------------------------------------------
        # Aba "Relatório Consolidado": Tabela de Agrupamento por Conta e Tipo
        # ------------------------------------------------------------------------------
        with tabs[1]:
            st.markdown("<div class='data-container'>", unsafe_allow_html=True)
            st.subheader("Relatório Consolidado por Conta")
            relatorio = df.groupby(["ContaContabil", "Tipo_Descricao"])["Valor"].sum().reset_index()
            relatorio["Valor"] = relatorio["Valor"].apply(format_brl)
            st.dataframe(relatorio)
            st.markdown("</div>", unsafe_allow_html=True)
            
            # Dados Detalhados
            st.markdown("<div class='data-container'>", unsafe_allow_html=True)
            st.subheader("Dados Detalhados")
            display_df = df.copy()
            if "MÊS_FORMATADO" in display_df.columns:
                display_df["MÊS"] = display_df["MÊS_FORMATADO"]
            for col_to_drop in ["Data", "MÊS_FORMATADO"]:
                if col_to_drop in display_df.columns:
                    display_df.drop(col_to_drop, axis=1, inplace=True)
            total_values = {}
            for col in display_df.columns:
                if pd.api.types.is_numeric_dtype(display_df[col]):
                    total_values[col] = display_df[col].sum()
                else:
                    total_values[col] = "Total" if col.upper() == "MÊS" else ""
            total_df = pd.DataFrame(total_values, index=["Total"])
            display_df = pd.concat([display_df, total_df])
            display_df = display_df.applymap(
                lambda x: "" if (isinstance(x, (int, float)) and (pd.isna(x) or x == 0))
                else format_brl(x) if isinstance(x, (int, float))
                else x
            )
            st.dataframe(display_df)
            st.markdown("</div>", unsafe_allow_html=True)
            
    except Exception as e:
        st.error(f"Erro ao processar os arquivos: {e}")
        st.text(traceback.format_exc())
else:
    st.sidebar.info("Aguardando o upload dos arquivos de Plano de Contas e Dados Financeiros.")
    st.info("Utilize a barra lateral para carregar os arquivos e configurar os filtros.")

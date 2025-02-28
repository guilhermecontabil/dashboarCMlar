import streamlit as st
import pandas as pd
import plotly.express as px
import streamlit.components.v1 as components

st.title("Dashboard de Consolidação de Dados")

# Upload do arquivo XLSX
uploaded_file = st.file_uploader("Selecione um arquivo XLSX", type=["xlsx"])
if uploaded_file is not None:
    # Leitura do arquivo e conversão da coluna DATA para datetime
    df = pd.read_excel(uploaded_file)
    df['DATA'] = pd.to_datetime(df['DATA'], errors='coerce')
    
    # Criar coluna 'Mês' no formato AAAA-MM
    df['Mês'] = df['DATA'].dt.to_period('M').astype(str)
    
    # Consolidação: soma dos valores por mês e por tipo
    df_grouped = df.groupby(['Mês', 'TIPO'])['VALOR'].sum().reset_index()
    
    # Pivot para reorganizar os dados e facilitar a visualização
    df_pivot = df_grouped.pivot(index='Mês', columns='TIPO', values='VALOR').fillna(0).reset_index()
    
    st.subheader("Base de Dados Consolidada")
    st.dataframe(df_pivot)
    
    # Cálculo dos totais gerais para cada TIPO
    # Ajuste os nomes de acordo com os valores presentes na coluna 'TIPO'
    total_venda = df[df['TIPO'].str.lower() == 'venda']['VALOR'].sum()
    total_compras = df[df['TIPO'].str.lower() == 'compras']['VALOR'].sum()
    total_impostos = df[df['TIPO'].str.lower() == 'impostos das']['VALOR'].sum()
    
    st.subheader("Indicadores")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Vendas", f"R$ {total_venda:,.2f}")
    col2.metric("Total Compras", f"R$ {total_compras:,.2f}")
    col3.metric("Total Impostos DAS", f"R$ {total_impostos:,.2f}")
    
    # Gráfico: Evolução dos totais por mês para cada TIPO
    st.subheader("Evolução Mensal")
    # Convertendo o DataFrame pivotado para o formato "long" para o plotly express
    df_long = df_pivot.melt(id_vars='Mês', var_name='TIPO', value_name='VALOR')
    fig = px.line(df_long, x='Mês', y='VALOR', color='TIPO', markers=True, 
                  title="Totais por Mês para cada TIPO")
    st.plotly_chart(fig)
    
    # Exemplo de componente customizado (cartão com HTML)
    html_card = f"""
    <div style="background-color:#f0f2f6; padding:20px; border-radius:10px; text-align:center;">
        <h3>Resumo Geral</h3>
        <p>Total Vendas: R$ {total_venda:,.2f}</p>
        <p>Total Compras: R$ {total_compras:,.2f}</p>
        <p>Total Impostos DAS: R$ {total_impostos:,.2f}</p>
    </div>
    """
    st.subheader("Cartão Resumo")
    components.html(html_card, height=200)
else:
    st.info("Aguarde o upload do arquivo XLSX para exibir o dashboard.")

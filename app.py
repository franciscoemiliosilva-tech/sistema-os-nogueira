
# app.py
import streamlit as st
import pandas as pd

def renderizar_interface_entrada():
    st.set_page_config(page_title="Detalhamento de Pisos", layout="wide")
    st.title("Ordem de Produção de Pisos e Estruturas")

    # Módulo 1: Captura de medidas estruturais exatas
    st.subheader("Configuração da Malha de Vãos")
    st.write("Insira o comprimento exato de cada vão para identificar os módulos fora de padrão e alocar o material corretamente.")
    
    numero_vaos = st.number_input("Quantidade total de vãos na estrutura", min_value=1, max_value=20, value=3, step=1)
    
    colunas_vaos = st.columns(numero_vaos)
    medidas_vaos = {}
    
    for i in range(numero_vaos):
        with colunas_vaos[i]:
            # Trava o valor padrão da barra em 100 cm para agilizar o preenchimento
            medida = st.number_input(f"Vão {i+1} (cm)", min_value=10.0, value=100.0, step=1.0, key=f"vao_{i}")
            medidas_vaos[f"Vão {i+1}"] = medida

    st.divider()

    # Módulo 2: Captura das características geométricas das peças
    st.subheader("Configuração das Peças (Pisos)")
    
    # Estrutura base da tabela de preenchimento
    dados_iniciais = pd.DataFrame({
        "Identificação": [1, 2, 3],
        "Cor": ["Azul escuro", "Amarelo", "Azul escuro"],
        "Formato": ["Quadrado", "Quadrado", "Quadrado"],
        "Contatos Horizontais": [1, 2, 2],
        "Isolado por Degrau": [False, False, False]
    })

    # Grade editável com opções restritas para evitar erros de digitação
    tabela_editada = st.data_editor(
        dados_iniciais,
        column_config={
            "Formato": st.column_config.SelectboxColumn(
                "Formato Geométrico",
                help="Selecione a geometria da peça.",
                options=["Quadrado", "L", "Triângulo"],
                required=True
            ),
            "Contatos Horizontais": st.column_config.NumberColumn(
                "Encaixes",
                help="Número de peças conectadas no mesmo nível horizontal.",
                min_value=0,
                max_value=4,
                required=True
            )
        },
        num_rows="dynamic",
        use_container_width=True
    )
    
    return medidas_vaos, tabela_editada

# Execução temporária para visualizar o layout
if __name__ == "__main__":
    renderizar_interface_entrada()
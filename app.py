import streamlit as st
import pandas as pd
import re
import math
import os
import base64
from html import escape
from datetime import datetime

st.set_page_config(page_title="ERP Produção - Nogueira", layout="wide", initial_sidebar_state="expanded")

# --- MENU LATERAL (CONFIGURAÇÕES) ---
st.sidebar.image("https://img.icons8.com/color/96/000000/settings--v1.png", width=60)
st.sidebar.markdown("### 📝 Configurações da OS")

st.sidebar.caption("O sistema extrai automático do CSV. Use os campos abaixo APENAS se quiser forçar outro nome na OS:")
cliente_manual = st.sidebar.text_input("Forçar Nome do Cliente", "")
projeto_manual = st.sidebar.text_input("Forçar Número do PV", "")

st.title("Sistema Gerador de Ordem de Serviço")
st.markdown("---")

# --- FUNÇÕES CORE ---
def padronizar_medidas_maior_menor(texto):
    if not texto: return ""
    def repl(match):
        v1 = float(match.group(1).replace(',', '.'))
        v2 = float(match.group(2).replace(',', '.'))
        maior = max(v1, v2); menor = min(v1, v2)
        m1_str = f"{int(maior)}" if maior.is_integer() else f"{maior}"
        m2_str = f"{int(menor)}" if menor.is_integer() else f"{menor}"
        return f"{m1_str}x{m2_str}"
    return re.sub(r'\b(\d+(?:[.,]\d+)?)\s*[xX]\s*(\d+(?:[.,]\d+)?)\b', repl, str(texto))

def normalizar_nome_cruzamento(texto):
    n = str(texto).upper()
    n = n.replace('º', '').replace('°', '') 
    n = n.replace(',', '.') 
    n = re.sub(r'\s*[X]\s*', 'X', n) 
    n = re.sub(r'\bMT\b', '', n) 
    n = re.sub(r'[^\w\s\.]', ' ', n) 
    n = re.sub(r'\s+', ' ', n).strip() 
    return n

def corrigir_ortografia_cor(cor_bruta):
    texto = str(cor_bruta).upper().strip()
    cores_detectadas = []
    if "AMAAR" in texto or "AMAR" in texto: cores_detectadas.append("Amarelo")
    if "VERME" in texto: cores_detectadas.append("Vermelho")
    if "VERD" in texto:
        if "CLAR" in texto: cores_detectadas.append("Verde Claro")
        elif "ESCUR" in texto: cores_detectadas.append("Verde Escuro")
        else: cores_detectadas.append("Verde")
    if "AZU" in texto:
        if "CLAR" in texto: cores_detectadas.append("Azul Claro")
        elif "ESCUR" in texto: cores_detectadas.append("Azul Escuro")
        else: cores_detectadas.append("Azul")
    if "PRET" in texto or "PRETA" in texto: cores_detectadas.append("Preto")
    if "LARAN" in texto: cores_detectadas.append("Laranja")
    if "MARRO" in texto: cores_detectadas.append("Marrom")
    if "ROX" in texto: cores_detectadas.append("Roxo")
    if "ROS" in texto: cores_detectadas.append("Rosa")
    if "CINZA" in texto: cores_detectadas.append("Cinza")
    
    base = " / ".join(cores_detectadas) if cores_detectadas else texto.title()
    if "NEON" in texto and "Neon" not in base: base = f"{base} Neon"
    return base

def parse_dim(val, campo='', item=''):
    if pd.isna(val):
        raise ValueError(f"{item or 'Item'}: campo {campo or 'dimensão'} sem valor")

    # O exportador 3D pode fornecer números em notação científica,
    # por exemplo 9.15527e-05. Primeiro tentamos a conversão direta,
    # que preserva corretamente esse formato.
    texto = str(val).strip().replace(',', '.')
    try:
        numero = float(texto)
    except (TypeError, ValueError):
        # Fallback para valores acompanhados de texto/unidade.
        # A regex também aceita notação científica.
        match = re.search(r'[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?', texto)
        if not match:
            raise ValueError(f"{item or 'Item'}: valor inválido em {campo or 'dimensão'}: {val!r}")
        try:
            numero = float(match.group(0))
        except (TypeError, ValueError):
            raise ValueError(f"{item or 'Item'}: valor inválido em {campo or 'dimensão'}: {val!r}")

    if not math.isfinite(numero):
        raise ValueError(f"{item or 'Item'}: valor não finito em {campo or 'dimensão'}: {val!r}")

    # Pequenos resíduos numéricos do CAD são tratados como zero.
    if abs(numero) < 1e-4:
        numero = 0.0

    return numero

# --- GERADOR DO HTML PROFISSIONAL (A4) ---
def gerar_html_os(categoria, dados, cliente, projeto):
    data_atual = datetime.now().strftime("%d/%m/%Y")
    categoria = escape(str(categoria))
    cliente = escape(str(cliente))
    projeto = escape(str(projeto))
    
    logo_html = ""
    try:
        arquivos_locais = os.listdir('.')
        for f in arquivos_locais:
            if 'logo' in f.lower() and f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                with open(f, "rb") as img_file:
                    b64 = base64.b64encode(img_file.read()).decode('utf-8')
                    ext = f.lower().split('.')[-1]
                    logo_html = f'<img src="data:image/{ext};base64,{b64}" style="max-height: 55px; max-width: 250px; object-fit: contain;">'
                    break
    except: pass
            
    if not logo_html:
        logo_html = """<div style="font-weight: bold; font-size: 22px; color: #000;">NOGUEIRA BRINQUEDOS</div>"""
    
    is_checklist = (categoria == "CHECK LIST DE EXPEDIÇÃO")
    is_compras = (categoria == "LISTA DE COMPRAS")
    is_categorized = is_checklist or is_compras
    
    if is_checklist:
        header_html = """
            <tr>
                <th>ITEM / DESCRIÇÃO</th>
                <th style="width: 15%;">MEDIDA</th>
                <th style="width: 10%;">QTD</th>
                <th class="center" style="width: 11%; font-size: 9px; line-height: 1.2;">OK<br>EMBALAGEM</th>
                <th class="center" style="width: 11%; font-size: 9px; line-height: 1.2;">OK<br>EXPEDIÇÃO</th>
            </tr>
        """
        td_ok = "<td></td><td></td>"
        colspan_cat = 5
    elif categoria == "CONEXÕES DE ALUMÍNIO":
        header_html = """
            <tr>
                <th>TIPO / MODELO</th>
                <th style="width: 15%;"></th>
                <th style="width: 10%;">QTD</th>
                <th class="check-col">OK</th>
            </tr>
        """
        td_ok = "<td></td>"
        colspan_cat = 4
    elif is_compras:
        header_html = """
            <tr>
                <th>ITEM / DESCRIÇÃO</th>
                <th style="width: 15%;"></th>
                <th style="width: 10%;">QTD</th>
                <th class="check-col">OK</th>
            </tr>
        """
        td_ok = "<td></td>"
        colspan_cat = 4
    else:
        header_html = """
            <tr>
                <th>ITEM / DESCRIÇÃO</th>
                <th style="width: 15%;">MEDIDA</th>
                <th style="width: 10%;">QTD</th>
                <th class="check-col">OK</th>
            </tr>
        """
        td_ok = "<td></td>"
        colspan_cat = 4
    
    linhas_tabela = ""
    total_q = 0
    
    if is_categorized and 'agregados_por_categoria' in dados:
        if is_checklist:
            ordem_cats = ["ATIVIDADES KID PLAY", "ROTTO BRASIL", "FIBRA DE VIDRO", "SERRALHERIA", "MARCENARIA", "COSTURA", "IMPRESSÃO", "ESTOQUE", "PISOS E CONTENÇÕES"]
        else:
            ordem_cats = ["CONEXÕES DE ALUMÍNIO", "ESTOQUE", "PARAFUSOS E FERRAGENS", "MATÉRIAS PRIMAS", "TUBOS KID PLAY", "MARCENARIA", "ROTTO BRASIL", "FIBRA DE VIDRO", "ESPUMAS ESPECIAIS", "ILUMINAÇÃO"]
            
        def sort_cat(c):
            try: return ordem_cats.index(c)
            except: return 99

        for cat_c in sorted(dados['agregados_por_categoria'].keys(), key=sort_cat):
            itens_cat = dados['agregados_por_categoria'][cat_c]
            if not itens_cat: continue
            
            linhas_tabela += f'<tr><td colspan="{colspan_cat}" style="background-color: #e0e0e0; font-weight: bold; text-align: center; padding: 4px; font-size: 10px;">{cat_c}</td></tr>'
            
            for chave in sorted(itens_cat.keys(), key=lambda x: x[0]):
                qtd = itens_cat[chave]
                
                if isinstance(qtd, float) and qtd.is_integer():
                    qtd = int(qtd)
                elif isinstance(qtd, float):
                    qtd = f"{qtd:.2f}"
                
                nome = escape(str(chave[0]))
                medida = escape(str(chave[1])) if chave[1] else "-"
                cor = f" ({escape(str(chave[2]))})" if chave[2] else ""
                linhas_tabela += f'<tr><td>{nome}{cor}</td><td class="center">{medida}</td><td class="center bold">{qtd}</td>{td_ok}</tr>'
                
                try: total_q += float(qtd)
                except: pass
    else:
        if 'lista_sequencial' in dados:
            for linha in dados['lista_sequencial']:
                linha = escape(str(linha))
                linhas_tabela += f'<tr><td>{linha}</td><td class="center">-</td><td class="center bold">1</td>{td_ok}</tr>'
                total_q += 1

        if 'agregados' in dados:
            for chave in sorted(dados['agregados'].keys(), key=lambda x: x[0]):
                qtd = dados['agregados'][chave]
                nome = escape(str(chave[0]))
                medida = escape(str(chave[1])) if chave[1] else ""
                cor = f" ({escape(str(chave[2]))})" if chave[2] else ""
                linhas_tabela += f'<tr><td>{nome}{cor}</td><td class="center">{medida}</td><td class="center bold">{qtd}</td>{td_ok}</tr>'
                try: total_q += float(qtd)
                except: pass

    if isinstance(total_q, float) and total_q.is_integer():
        total_q = int(total_q)
    elif isinstance(total_q, float):
        total_q = f"{total_q:.2f}"

    html_template = f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <title>OS - {categoria}</title>
        <style>
            * {{
                -webkit-print-color-adjust: exact !important;
                print-color-adjust: exact !important;
                color-adjust: exact !important;
            }}
            body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; color: #000; font-size: 11px; }}
            .header {{ display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 2px solid #000; padding-bottom: 10px; margin-bottom: 15px; }}
            .os-title {{ text-align: right; font-weight: bold; font-size: 14px; margin-top: 15px; }}
            .os-subtitle {{ font-size: 11px; font-weight: normal; display: block; color: #444; }}
            .info-table {{ width: 100%; margin-bottom: 15px; font-size: 11px; }}
            .info-table td {{ padding: 3px 0; }}
            .data-table {{ width: 100%; border-collapse: collapse; font-size: 11px; }}
            .data-table th, .data-table td {{ border: 1px solid #000; padding: 6px; text-align: left; }}
            .data-table th {{ background-color: #f9f9f9; font-weight: bold; text-align: center; font-size: 10px; }}
            .center {{ text-align: center !important; }}
            .bold {{ font-weight: bold; }}
            .check-col {{ width: 45px; }}
            .tfoot-td {{ font-weight: bold; text-align: right; padding-right: 10px; }}
            .footer-signs {{ display: flex; justify-content: space-between; margin-top: 60px; text-align: center; }}
            .signature {{ border-top: 1px solid #000; width: 40%; padding-top: 5px; font-size: 10px; }}
            @media print {{
                body {{ padding: 0; margin: 0; }}
                @page {{ margin: 1cm; size: A4; }}
                button {{ display: none; }}
            }}
            .print-btn {{ margin-bottom: 20px; padding: 10px 20px; background-color: #007bff; color: #fff; border: none; border-radius: 5px; cursor: pointer; }}
        </style>
    </head>
    <body>
        <button class="print-btn" onclick="window.print()">🖨️ Imprimir Agora</button>
        <div class="header">
            <div>
                {logo_html}
            </div>
            <div class="os-title">ORDEM DE SERVIÇO<br><span class="os-subtitle">{categoria}</span></div>
        </div>
        <table class="info-table">
            <tr>
                <td style="width: 60%;"><b>Cliente:</b> {cliente}</td>
                <td style="text-align: right;"><b>Data:</b> {data_atual}</td>
            </tr>
            <tr>
                <td><b>Projeto:</b> {projeto}</td>
                <td style="text-align: right;"><b>Responsável:</b> __________________________________</td>
            </tr>
        </table>
        <table class="data-table">
            <thead>
                {header_html}
            </thead>
            <tbody>
                {linhas_tabela}
            </tbody>
            <tfoot>
                <tr>
                    <td colspan="2" class="tfoot-td">TOTAL:</td>
                    <td class="center bold">{total_q}</td>
                    {td_ok}
                </tr>
            </tfoot>
        </table>
        <div class="footer-signs">
            <div class="signature">Assinatura do Responsável</div>
            <div class="signature">Visto da Expedição / Produção</div>
        </div>
    </body>
    </html>
    """
    return html_template

# --- UPLOAD DE ARQUIVOS ---
col_u1, col_u2 = st.columns(2)
with col_u1: arquivos_excel = st.file_uploader("1. Planilhas (.xlsx) - Suba a MESTRE e a COMPOSIÇÃO", type=["xlsx"], accept_multiple_files=True)
with col_u2: arquivo_csv_3d = st.file_uploader("2. Projeto 3D (.csv)", type=["csv"])

if arquivos_excel and arquivo_csv_3d:
    try:
        arquivo_mestre = None
        arquivo_comp = None
        
        for f in arquivos_excel:
            xls = pd.ExcelFile(f)
            for sheet_name in xls.sheet_names:
                df_sheet = pd.read_excel(xls, sheet_name=sheet_name, header=None)
                sheet_str = df_sheet.astype(str).to_string().upper()
                s_name = sheet_name.upper()
                
                if "COMP" in s_name or "PEÇAS" in s_name or "RECEIT" in s_name or ("COMPENSADO 17MM" in sheet_str and "LONA" in sheet_str):
                    arquivo_comp = f
                elif "PARAFUSO" in s_name or ("FITILHO" in sheet_str and "TERMINAL" in sheet_str and "ITENS" in sheet_str) or ("ABRAÇADEIRA" in sheet_str and "TERMINAL" in sheet_str):
                    pass
                else:
                    arquivo_mestre = f
            
        if not arquivo_mestre: arquivo_mestre = arquivos_excel[0]
        
        # --- LEITURA E SANITIZAÇÃO DE DADOS 3D ---
        df_3d = pd.read_csv(arquivo_csv_3d, sep='\t')

        colunas_obrigatorias = {'Name', 'Width', 'Length', 'Height', 'PosX', 'PosY', 'PosZ'}
        faltantes = sorted(colunas_obrigatorias - set(df_3d.columns))
        if faltantes:
            raise ValueError('CSV incompatível. Colunas ausentes: ' + ', '.join(faltantes))

        for col_num in ['Width', 'Length', 'Height', 'PosX', 'PosY', 'PosZ']:
            df_3d[col_num] = pd.to_numeric(df_3d[col_num].astype(str).str.replace(',', '.', regex=False), errors='coerce')
        invalidos = df_3d[['Width', 'Length', 'Height', 'PosX', 'PosY', 'PosZ']].isna().any(axis=1)
        if invalidos.any():
            amostra = df_3d.loc[invalidos, ['Name', 'Width', 'Length', 'Height', 'PosX', 'PosY', 'PosZ']].head(10)
            raise ValueError('CSV contém dimensões/posições inválidas. Revise os itens: ' + '; '.join(amostra.astype(str).agg(' | '.join, axis=1).tolist()))
        
        # Filtro Anti-Clone
        df_3d['X_round'] = df_3d['PosX'].round(0)
        df_3d['Y_round'] = df_3d['PosY'].round(0)
        df_3d['Z_round'] = df_3d['PosZ'].round(0)
        
        qt_original = len(df_3d)
        duplicados_mask = df_3d.duplicated(subset=['Name', 'Width', 'Length', 'Height', 'X_round', 'Y_round', 'Z_round'], keep=False)
        qt_limpo = qt_original

        if duplicados_mask.any():
            st.warning(f"⚠️ Auditoria: foram encontradas {int(duplicados_mask.sum())} linhas potencialmente duplicadas/sobrepostas. Nenhuma peça foi removida automaticamente.")
        
        cliente_csv, projeto_csv = "", ""
        for col in df_3d.columns:
            if "CLIENTE" in str(col).upper(): val = str(df_3d[col].iloc[0]); cliente_csv = val if val != 'nan' else ""
            if "PV" in str(col).upper() or "PROJETO" in str(col).upper(): val = str(df_3d[col].iloc[0]); projeto_csv = val if val != 'nan' else ""
                
        if not cliente_csv:
            filename = arquivo_csv_3d.name.replace('.csv', '')
            if " - " in filename: parts = filename.split(" - "); cliente_csv = parts[0]; projeto_csv = parts[1] if len(parts) > 1 else projeto_csv
            elif "_" in filename: parts = filename.split("_"); cliente_csv = parts[0]; projeto_csv = parts[1] if len(parts) > 1 else projeto_csv
            else: cliente_csv = filename

        cliente_final = cliente_manual if cliente_manual else (cliente_csv if cliente_csv else "NÃO INFORMADO")
        projeto_final = projeto_manual if projeto_manual else (projeto_csv if projeto_csv else "-")

        # --- MOTOR DE LEITURA BLINDADO (Aba por Aba) ---
        banco_dados = {}
        df_paraf = None
        df_comp = None

        for f in arquivos_excel:
            xls = pd.ExcelFile(f)
            for sheet_name in xls.sheet_names:
                df_sheet = pd.read_excel(xls, sheet_name=sheet_name, header=None)
                sheet_str = df_sheet.astype(str).to_string().upper()
                s_name = sheet_name.upper()
                
                if "COMP" in s_name or "PEÇAS" in s_name or "RECEIT" in s_name or ("COMPENSADO 17MM" in sheet_str and "LONA" in sheet_str):
                    df_comp = df_sheet
                elif "PARAFUSO" in s_name or ("FITILHO" in sheet_str and "TERMINAL" in sheet_str and "ITENS" in sheet_str) or ("ABRAÇADEIRA" in sheet_str and "TERMINAL" in sheet_str):
                    df_paraf = df_sheet
                else:
                    cat_atual = "ITENS GERAIS"
                    for _, row in df_sheet.iterrows():
                        for val in row:
                            val_str = str(val).strip()
                            if pd.notna(val) and val_str != '':
                                if "=" in val_str and len(val_str.split("=")) >= 2:
                                    parts = val_str.split("=")
                                    sku = re.sub(r'([A-Z])O(\d)', r'\g<1>0\g<2>', parts[1].strip().upper().replace('_', ''))
                                    if "CONEXAO_" in sku: sku = parts[1].strip().upper() 
                                    banco_dados[sku] = {'nome': parts[0].strip(), 'cat': cat_atual}
                                elif "DESTINO" not in val_str.upper() and "ITENS" not in val_str.upper() and len(val_str) < 40:
                                    cat_atual = re.sub(r'\s+', ' ', val_str).strip().upper()

        banco_dados_seguro = {
            'CONEXAO_BASE': 'Base', 'CONEXAO_COTOVELO': 'Cotovelo', 
            'CONEXAO_LUVA': 'Luva', 'CONEXAO_PUNHO': 'Punho',
            'CONEXAO_T_4_SAIDAS': 'T 4 Saídas', 'CONEXAO_CRUZETA': 'Cruzeta',
            'CONEXAO_ARTICULADA': 'Articulada'
        }
        
        # --- EXTRATOR DA COMPOSIÇÃO DE MATERIAIS ---
        dict_composicao = {}
        if df_comp is not None:
            codigo_atual = None
            for index, row in df_comp.iterrows():
                col1 = str(row[1]).strip() if pd.notna(row[1]) else ""
                col2 = row[2] if pd.notna(row[2]) else None
                col3 = str(row[3]).strip() if pd.notna(row[3]) else ""
                
                if col1 == "" and pd.isna(row[2]):
                    codigo_atual = None
                    continue
                
                match_cod = re.search(r'=([A-Z][0-9O]{2})', col1.upper())
                if match_cod:
                    codigo_atual = match_cod.group(1).replace('O', '0')
                    dict_composicao[codigo_atual] = []
                    
                elif codigo_atual is not None and col1 != "":
                    try:
                        q_val = float(col2)
                    except:
                        q_val = 0.0
                    
                    if q_val > 0:
                        dict_composicao[codigo_atual].append({
                            "material": col1,
                            "qtd": q_val,
                            "unidade": col3
                        })

        # (2) PROCESSAMENTO PRINCIPAL DO 3D
        items_parsed = []
        area_eva_por_cor, area_rede_por_cor = {}, {}
        cores_bolinhas, metragem_tubos_por_cor = set(), {}
        lista_auditoria = [] 
        area_marcenaria_m2 = 0.0
        
        area_total_espuma_m2 = 0.0
        lona_calculada_por_cor = {}
        
        contagem_codigos_oficiais = {}
        codigos_pisos = set()
        
        for _, row in df_3d.iterrows():
            nome_original = str(row.get('Name', '')).strip().upper()
            cor_limpa = corrigir_ortografia_cor(str(row.get('Material', 'SEM COR')))
            match_codigo = re.match(r'^([A-Z][0-9O]{2})', nome_original)
            
            nome_amigavel = nome_original
            categoria_peca = "OUTROS"
            codigo_base = ""
            
            is_conexao_nativa = False
            for chv_conexao, nome_padrao in banco_dados_seguro.items():
                if chv_conexao in nome_original:
                    nome_amigavel = banco_dados.get(chv_conexao, {}).get('nome', nome_padrao)
                    categoria_peca = banco_dados.get(chv_conexao, {}).get('cat', 'CONEXÕES DE ALUMÍNIO')
                    is_conexao_nativa = True
                    break

            if not is_conexao_nativa and match_codigo:
                codigo_base = match_codigo.group(1).replace('O', '0')
                if codigo_base in banco_dados:
                    nome_amigavel = padronizar_medidas_maior_menor(banco_dados[codigo_base]['nome'])
                    categoria_peca = banco_dados[codigo_base]['cat']
                    chave_cod = (codigo_base, cor_limpa)
                    contagem_codigos_oficiais[chave_cod] = contagem_codigos_oficiais.get(chave_cod, 0) + 1
                    
                    if categoria_peca == "PISOS E CONTENÇÕES":
                        codigos_pisos.add(codigo_base)

            if not is_conexao_nativa and ("MATERIAL" in cor_limpa.upper() or "SEM COR" in cor_limpa.upper()):
                lista_auditoria.append(nome_amigavel)

            w = parse_dim(row.get('Width', 0), 'Width', nome_original); l = parse_dim(row.get('Length', 0), 'Length', nome_original); h = parse_dim(row.get('Height', 0), 'Height', nome_original)
            dims_reais = sorted([w, l, h])
            dims = [int(round(x)) for x in dims_reais]
            px = parse_dim(row.get('PosX', 0), 'PosX', nome_original); py = parse_dim(row.get('PosY', 0), 'PosY', nome_original); pz = parse_dim(row.get('PosZ', 0), 'PosZ', nome_original)
            
            is_tubo = ("TUBOS KID PLAY" in categoria_peca) or (not is_conexao_nativa and bool(re.match(r'^T\d{2}\b', nome_original)))
            if is_tubo:
                categoria_peca = "TUBOS KID PLAY"
                medida_exata = max(w, l, h) 
                dims = [0, 0, int(round(medida_exata))] 
                metragem_tubos_por_cor[cor_limpa] = metragem_tubos_por_cor.get(cor_limpa, 0.0) + (medida_exata / 100.0)
                nome_amigavel = "Tubo de Kid Play" 
                
            if "EVA" in nome_amigavel.upper():
                area_eva_por_cor[cor_limpa] = area_eva_por_cor.get(cor_limpa, 0.0) + ((dims_reais[1] * dims_reais[2]) / 10000.0)
                continue
            if "REDE" in nome_amigavel.upper() or "REDE" in categoria_peca:
                area_rede_por_cor[cor_limpa] = area_rede_por_cor.get(cor_limpa, 0.0) + ((dims_reais[1] * dims_reais[2]) / 10000.0)
                continue
                
            nome_amigavel_upper = nome_amigavel.upper()
                
            # Filtro Inteligente de Bolinhas
            if "BOLINHA" in nome_amigavel_upper and not is_conexao_nativa:
                # Ignora a cor se for uma estrutura (Rampa, Degrau, Escada, Piscina, Rede)
                if any(x in nome_amigavel_upper for x in ["PISCINA", "REDE", "PISO", "CONTEN", "PORTA", "SACO", "ESCAD", "RAMPA", "DEGRAU", "ACESS", "PASSA", "ESTRUTURA"]):
                    pass 
                else:
                    cores_bolinhas.add(cor_limpa)
                    continue
                
            is_impresso = False
            cor_limpa_upper = cor_limpa.upper()
            if any(x in nome_amigavel_upper for x in ["ADESIV", "IMPRESS", "LONA"]) or any(x in cor_limpa_upper for x in ["ADESIV", "IMPRESS", "LONA"]):
                is_impresso = True

            is_contencao_flag = "CONTEN" in nome_amigavel_upper

            # Componentes de cama elastica. O cadastro Mestre usa o nome
            # "Ferro com Furo Para Camaelastica=S15_", sem espaco entre
            # CAMA e ELASTICA, por isso a regra antiga nao reconhecia o S15.
            is_ferro_furo_cama = (
                codigo_base == "S15"
                or "FERRO COM FURO" in nome_amigavel_upper
                or "FERRO C/ FURO" in nome_amigavel_upper
                or "FERRO FURADO" in nome_amigavel_upper
            )
            is_cama_elastica = is_ferro_furo_cama or any(
                x in nome_amigavel_upper
                for x in [
                    "CAMA ELÁSTICA", "CAMA ELASTICA", "CAMAELASTICA",
                    "ÁREA DE PULO", "AREA DE PULO",
                    "PROTEÇÃO PARA CAMA", "PROTECAO PARA CAMA"
                ]
            )

            if (categoria_peca == "PISOS E CONTENÇÕES" or is_contencao_flag) and not is_cama_elastica:
                area = (dims_reais[1] * dims_reais[2]) / 10000.0
                area_marcenaria_m2 += area
                area_total_espuma_m2 += area
                
                is_triangulo = "TRIANG" in nome_amigavel_upper or "TRIÂNG" in nome_amigavel_upper
                
                if is_triangulo:
                    metros_lona = 1.29
                elif is_contencao_flag:
                    metros_lona = (dims[2] + 20.0) / 100.0
                else:
                    metros_lona = ((dims[1] + 20.0) * 2.0) / 100.0
                    
                if cor_limpa.title() not in lona_calculada_por_cor:
                    lona_calculada_por_cor[cor_limpa.title()] = 0.0
                lona_calculada_por_cor[cor_limpa.title()] += metros_lona

            items_parsed.append({
                'cat': categoria_peca, 'nome': nome_amigavel, 'cor': cor_limpa,
                'is_piso_contencao': categoria_peca == "PISOS E CONTENÇÕES",
                'is_contencao': is_contencao_flag,
                'is_cama_elastica': is_cama_elastica,
                'is_ferro_furo_cama': is_ferro_furo_cama,
                'codigo_base': codigo_base,
                'is_impresso': is_impresso,
                'z_round': round(pz/40.0)*40.0, 'y_round': round(py/40.0)*40.0, 'x': px, 'dims': dims
            })

        items_parsed.sort(key=lambda x: (x['is_piso_contencao'], x['is_contencao'], x['z_round'], x['y_round'], -x['x']))

        # (4) CONSTRUÇÃO DO RELATÓRIO 
        relatorio = {}
        contador_pisos = 1
        qtd_turbilhao = 0
        qtd_ponte_105 = 0; qtd_ponte_210 = 0
        qtd_ferro_triangulo = 0; qtd_ferro_fora_padrao = 0
        
        qtd_escorregador_2v = 0
        qtd_escorregador_3v = 0
        qtd_escorregador_4v = 0
        
        for item in items_parsed:
            cat = item['cat']
            nome_upper = item['nome'].upper()
            if cat not in relatorio: relatorio[cat] = {}
            
            if cat not in ["TUBOS KID PLAY", "PISOS E CONTENÇÕES", "SERRALHERIA"]:
                if "TURBILHÃO" in nome_upper: qtd_turbilhao += 1
                
            is_nome_piso = "PISO" in nome_upper or "CONTEN" in nome_upper
            if "PONTE" in nome_upper and "105" in nome_upper and "30" in nome_upper and not is_nome_piso: qtd_ponte_105 += 1
            if "PONTE" in nome_upper and "210" in nome_upper and "30" in nome_upper and not is_nome_piso: qtd_ponte_210 += 1
                
            if item['is_piso_contencao']:
                if "TRIANG" in nome_upper or "TRIÂNG" in nome_upper: qtd_ferro_triangulo += 1
                if "FORA DE PADR" in nome_upper and item['dims'][2] > 109: qtd_ferro_fora_padrao += 1

            if "ESCORREGADOR" in nome_upper:
                if "2 VIA" in nome_upper: qtd_escorregador_2v += 1
                elif "3 VIA" in nome_upper: qtd_escorregador_3v += 1
                elif "4 VIA" in nome_upper: qtd_escorregador_4v += 1

            medida = ""
            if cat == "TUBOS KID PLAY":
                medida = str(int(max(item['dims'])))
            elif item.get('is_ferro_furo_cama'):
                # Para o S15 interessa o comprimento de corte do ferro,
                # representado pela maior dimensao geometrica do bloco 3D.
                comprimento = max(item['dims'])
                if comprimento > 0:
                    medida = f"{int(comprimento)} cm" if float(comprimento).is_integer() else f"{comprimento:.1f} cm"
            elif any(x in nome_upper for x in ["CONTEN", "PORT", "FORA DE PADR", "BANNER", "ADESIV", "IMPRESS", "LONA"]):
                if item['dims'][1] > 0 and cat != "COSTURA":
                    medida = f"{item['dims'][2]}x{item['dims'][1]}"
            elif item.get('is_cama_elastica') and item['dims'][1] > 0:
                medida = f"{item['dims'][2]}x{item['dims'][1]}"

            cor_display = "" if cat in ["TUBOS KID PLAY", "SERRALHERIA", "CONEXÕES DE ALUMÍNIO"] else item['cor']

            if item['is_piso_contencao']:
                if 'lista_sequencial' not in relatorio[cat]: relatorio[cat]['lista_sequencial'] = []
                med_str = f" {medida}" if medida else ""
                cor_str = f" {cor_display}" if cor_display else ""
                relatorio[cat]['lista_sequencial'].append(f"#{contador_pisos:03d} - {item['nome']}{med_str}{cor_str}")
                contador_pisos += 1
            else:
                if 'agregados' not in relatorio[cat]: relatorio[cat]['agregados'] = {}
                chave = (item['nome'], medida, cor_display)
                if chave not in relatorio[cat]['agregados']: relatorio[cat]['agregados'][chave] = 0
                relatorio[cat]['agregados'][chave] += 1
                
            if any(x in nome_upper for x in ["SINUOSO 1", "SINUOSO 2", "RAMPA DE CINTA", "TURBILHÃO"]):
                if "COSTURA" not in relatorio: relatorio["COSTURA"] = {}
                if 'agregados' not in relatorio["COSTURA"]: relatorio["COSTURA"]['agregados'] = {}
                chave_cost = (item['nome'], "", item['cor'])
                if chave_cost not in relatorio["COSTURA"]['agregados']: relatorio["COSTURA"]['agregados'][chave_cost] = 0
                relatorio["COSTURA"]['agregados'][chave_cost] += 1
                
            if item['is_piso_contencao']:
                if "MARCENARIA" not in relatorio: relatorio["MARCENARIA"] = {}
                if 'agregados' not in relatorio["MARCENARIA"]: relatorio["MARCENARIA"]['agregados'] = {}
                medida_marcenaria = f"{item['dims'][2]}x{item['dims'][1]}" if any(x in nome_upper for x in ["CONTEN", "FORA DE PADR", "PORT"]) and item['dims'][1] > 0 else ""
                chave_marc = (item['nome'], medida_marcenaria, "")
                if chave_marc not in relatorio["MARCENARIA"]['agregados']: relatorio["MARCENARIA"]['agregados'][chave_marc] = 0
                relatorio["MARCENARIA"]['agregados'][chave_marc] += 1
                
            if item.get('is_impresso'):
                if "IMPRESSÃO" not in relatorio: relatorio["IMPRESSÃO"] = {}
                if 'agregados' not in relatorio["IMPRESSÃO"]: relatorio["IMPRESSÃO"]['agregados'] = {}
                chave_imp = (item['nome'], medida, cor_display)
                if chave_imp not in relatorio["IMPRESSÃO"]['agregados']: relatorio["IMPRESSÃO"]['agregados'][chave_imp] = 0
                relatorio["IMPRESSÃO"]['agregados'][chave_imp] += 1

        # --- REGRAS DE INJEÇÃO (MADEIRA DE APOIO ESCORREGADOR) ---
        if qtd_escorregador_2v > 0:
            if "ATIVIDADES KID PLAY" not in relatorio: relatorio["ATIVIDADES KID PLAY"] = {'agregados': {}}
            relatorio["ATIVIDADES KID PLAY"]['agregados'][("Madeira de Apoio para Escorregador", "100x08", "")] = relatorio["ATIVIDADES KID PLAY"]['agregados'].get(("Madeira de Apoio para Escorregador", "100x08", ""), 0) + qtd_escorregador_2v
            if "MARCENARIA" not in relatorio: relatorio["MARCENARIA"] = {'agregados': {}}
            relatorio["MARCENARIA"]['agregados'][("Madeira de Apoio para Escorregador", "100x08", "")] = relatorio["MARCENARIA"]['agregados'].get(("Madeira de Apoio para Escorregador", "100x08", ""), 0) + qtd_escorregador_2v

        if qtd_escorregador_3v > 0:
            if "ATIVIDADES KID PLAY" not in relatorio: relatorio["ATIVIDADES KID PLAY"] = {'agregados': {}}
            relatorio["ATIVIDADES KID PLAY"]['agregados'][("Madeira de Apoio para Escorregador", "150x08", "")] = relatorio["ATIVIDADES KID PLAY"]['agregados'].get(("Madeira de Apoio para Escorregador", "150x08", ""), 0) + qtd_escorregador_3v
            if "MARCENARIA" not in relatorio: relatorio["MARCENARIA"] = {'agregados': {}}
            relatorio["MARCENARIA"]['agregados'][("Madeira de Apoio para Escorregador", "150x08", "")] = relatorio["MARCENARIA"]['agregados'].get(("Madeira de Apoio para Escorregador", "150x08", ""), 0) + qtd_escorregador_3v

        if qtd_escorregador_4v > 0:
            if "ATIVIDADES KID PLAY" not in relatorio: relatorio["ATIVIDADES KID PLAY"] = {'agregados': {}}
            relatorio["ATIVIDADES KID PLAY"]['agregados'][("Madeira de Apoio para Escorregador", "205x08", "")] = relatorio["ATIVIDADES KID PLAY"]['agregados'].get(("Madeira de Apoio para Escorregador", "205x08", ""), 0) + qtd_escorregador_4v
            if "MARCENARIA" not in relatorio: relatorio["MARCENARIA"] = {'agregados': {}}
            relatorio["MARCENARIA"]['agregados'][("Madeira de Apoio para Escorregador", "205x08", "")] = relatorio["MARCENARIA"]['agregados'].get(("Madeira de Apoio para Escorregador", "205x08", ""), 0) + qtd_escorregador_4v

        qtd_curva_360 = 0
        if "ROTTO BRASIL" in relatorio and 'agregados' in relatorio["ROTTO BRASIL"]:
            for chave, qtd in relatorio["ROTTO BRASIL"]['agregados'].items():
                if "CURVA" in chave[0].upper(): qtd_curva_360 += qtd

        # (5) FIXOS, SERRALHERIA E ESTOQUE
        if "IMPRESSÃO" not in relatorio: relatorio["IMPRESSÃO"] = {}
        if 'agregados' not in relatorio["IMPRESSÃO"]: relatorio["IMPRESSÃO"]['agregados'] = {}
        relatorio["IMPRESSÃO"]['agregados'][("Régua do Kid Play", "", "")] = 1
        
        if "SERRALHERIA" not in relatorio: relatorio["SERRALHERIA"] = {}
        if 'agregados' not in relatorio["SERRALHERIA"]: relatorio["SERRALHERIA"]['agregados'] = {}
        
        qtd_chifres = 0
        if 2 <= qtd_curva_360 <= 4: qtd_chifres = 1
        elif 5 <= qtd_curva_360 <= 6: qtd_chifres = 2
        elif 7 <= qtd_curva_360 <= 9: qtd_chifres = 3
        elif qtd_curva_360 >= 10: qtd_chifres = 4
        
        if qtd_chifres > 0: relatorio["SERRALHERIA"]['agregados'][("Chifre suporte do 360°", "", "")] = qtd_chifres
        if qtd_curva_360 > 0: relatorio["SERRALHERIA"]['agregados'][("Quadro de curva 360°", "", "")] = 1
        if qtd_turbilhao > 0: relatorio["SERRALHERIA"]['agregados'][("Quadro de Turbilhão", "", "")] = qtd_turbilhao * 2
            
        if qtd_ponte_105 > 0:
            relatorio["SERRALHERIA"]['agregados'][('Quadro ponte em "v" 98 x 75 cm', "", "")] = qtd_ponte_105 * 2
            relatorio["SERRALHERIA"]['agregados'][('Ferros de 1,00 m p/ ponte "v" com grapas', "", "")] = qtd_ponte_105 * 2
            relatorio["SERRALHERIA"]['agregados'][('Ferros de 1,00 m p/ ponte "v" com grapas e ganchos', "", "")] = qtd_ponte_105 * 2
            
        if qtd_ponte_210 > 0:
            relatorio["SERRALHERIA"]['agregados'][('Quadro ponte em "v" 202,5 x 75 cm', "", "")] = qtd_ponte_210 * 2
            relatorio["SERRALHERIA"]['agregados'][('Ferros de 2,05 m p/ ponte "v" com grapas', "", "")] = qtd_ponte_210 * 2
            relatorio["SERRALHERIA"]['agregados'][('Ferros de 2,05 m p/ ponte "v" com grapas e ganchos', "", "")] = qtd_ponte_210 * 2

        if qtd_ferro_triangulo > 0: relatorio["SERRALHERIA"]['agregados'][("Ferro para deck triangulo", "", "")] = qtd_ferro_triangulo
        if qtd_ferro_fora_padrao > 0: relatorio["SERRALHERIA"]['agregados'][("Ferro de 100 com grapas P/ piso fora de padrão", "", "")] = qtd_ferro_fora_padrao

        if "ESTOQUE" not in relatorio: relatorio["ESTOQUE"] = {}
        if 'agregados' not in relatorio["ESTOQUE"]: relatorio["ESTOQUE"]['agregados'] = {}
        
        # SISTEMA DE COMPRAS CATEGORIZADO
        if "LISTA DE COMPRAS" not in relatorio: relatorio["LISTA DE COMPRAS"] = {}
        if 'agregados_por_categoria' not in relatorio["LISTA DE COMPRAS"]: relatorio["LISTA DE COMPRAS"]['agregados_por_categoria'] = {}
        
        consolidador_compras = {
            "ESPUMAS ESPECIAIS": {},
            "ILUMINAÇÃO": {},
            "CONEXÕES DE ALUMÍNIO": {},
            "ROTTO BRASIL": {},
            "FIBRA DE VIDRO": {},
            "ESTOQUE": {},
            "TUBOS KID PLAY": {},
            "MARCENARIA": {},
            "PARAFUSOS E FERRAGENS": {},
            "MATÉRIAS PRIMAS": {}
        }
        
        def add_compra(cat_compra, nome, medida, cor, qtd, is_float=False):
            if cat_compra not in consolidador_compras:
                consolidador_compras[cat_compra] = {}
            chave = (nome, medida, cor)
            if chave not in consolidador_compras[cat_compra]:
                consolidador_compras[cat_compra][chave] = 0.0 if is_float else 0
            consolidador_compras[cat_compra][chave] += qtd

        tem_rede_preta = area_rede_por_cor.get("Preto", 0.0) > 0
        fitilhos_brancos_tubos = 0
        fitilhos_pretos_tubos = 0
        fitilhos_planilha_unidades = 0
        abracadeira_composicao_unidades_branca = 0
        abracadeira_composicao_unidades_preta = 0
        
        molas_para_checklist = {}

        espumas_calc = {
            "ESPUMA CILINDRICA 20X20X60CM": 0,
            "ESPUMA CILINDRICA 26X26X60CM": 0,
            "ESPUMA POLIURETANO 7156 - TRIÂNGULO - 80X33X28CM": 0,
            "ESPUMA POLIURETANO 7156 - MEIA LUA - 80X33X28CM": 0
        }
        
        if "ATIVIDADES KID PLAY" in relatorio and 'agregados' in relatorio["ATIVIDADES KID PLAY"]:
            for chv, q in relatorio["ATIVIDADES KID PLAY"]['agregados'].items():
                nome_k = chv[0].upper()
                if "SACO DE BOXE" in nome_k:
                    if "GRAND" in nome_k or " G " in nome_k or nome_k.endswith(" G"):
                        espumas_calc["ESPUMA CILINDRICA 26X26X60CM"] += q
                    else:
                        espumas_calc["ESPUMA CILINDRICA 20X20X60CM"] += q
                if "CORCOVA" in nome_k:
                    if "TRIANG" in nome_k or "TRIÂNG" in nome_k:
                        espumas_calc["ESPUMA POLIURETANO 7156 - TRIÂNGULO - 80X33X28CM"] += q
                    else:
                        espumas_calc["ESPUMA POLIURETANO 7156 - MEIA LUA - 80X33X28CM"] += q

        for esp_nome, esp_qtd in espumas_calc.items():
            if esp_qtd > 0: add_compra("ESPUMAS ESPECIAIS", esp_nome, "", "", esp_qtd)
                
        if (qtd_curva_360 - 1) > 0:
            add_compra("ILUMINAÇÃO", "Holofote para Curva", "", "", qtd_curva_360 - 1)

        if "CONEXÕES DE ALUMÍNIO" in relatorio and 'agregados' in relatorio["CONEXÕES DE ALUMÍNIO"]:
            for chv, qtd in relatorio["CONEXÕES DE ALUMÍNIO"]['agregados'].items():
                add_compra("CONEXÕES DE ALUMÍNIO", chv[0], chv[1], chv[2], qtd)

        if "ROTTO BRASIL" in relatorio and 'agregados' in relatorio["ROTTO BRASIL"]:
            for chv, qtd in relatorio["ROTTO BRASIL"]['agregados'].items():
                add_compra("ROTTO BRASIL", chv[0], chv[1], chv[2], qtd)

        if "FIBRA DE VIDRO" in relatorio and 'agregados' in relatorio["FIBRA DE VIDRO"]:
            for chv, qtd in relatorio["FIBRA DE VIDRO"]['agregados'].items():
                add_compra("FIBRA DE VIDRO", chv[0], chv[1], chv[2], qtd)

        for cor, area in area_eva_por_cor.items():
            qtd_eva = math.ceil(area / 3.065)
            relatorio["ESTOQUE"]['agregados'][("Placa(s) de EVA", "", cor)] = qtd_eva
            add_compra("ESTOQUE", "Placa(s) de EVA", "", cor, qtd_eva)
            
        total_fardos_rede = 0
        for cor, area in area_rede_por_cor.items():
            fardos = math.ceil(area / 86.25)
            relatorio["ESTOQUE"]['agregados'][("Fardo(s) de Rede", "", cor)] = fardos
            add_compra("ESTOQUE", "Fardo(s) de Rede", "", cor, fardos)
            total_fardos_rede += fardos
            
        # ---------------------------------------------------------
        # CÁLCULO DAS BOLINHAS
        # ---------------------------------------------------------
        if len(cores_bolinhas) > 0:
            area_base_bolinhas = sum(area_eva_por_cor.values())
            calc_bolinhas = area_base_bolinhas * 1.5
            frac = calc_bolinhas - int(calc_bolinhas)
            if frac >= 0.50:
                total_pacotes = int(calc_bolinhas) + 1
            else:
                total_pacotes = int(calc_bolinhas)
                
            if total_pacotes == 0: total_pacotes = 1
            
            qtd_cores = len(cores_bolinhas)
            cores_lista = sorted(cores_bolinhas)
            if qtd_cores > 3: 
                relatorio["ESTOQUE"]['agregados'][("Pacote(s) de Bolinhas", "", "Coloridas")] = total_pacotes
                add_compra("ESTOQUE", "Pacote(s) de Bolinhas", "", "Coloridas", total_pacotes)
            elif qtd_cores > 0:
                base_qtd = total_pacotes // qtd_cores
                resto = total_pacotes % qtd_cores
                for i, cor in enumerate(cores_lista):
                    qtd_para_cor = base_qtd + (1 if i < resto else 0)
                    if qtd_para_cor > 0: 
                        relatorio["ESTOQUE"]['agregados'][("Pacote(s) de Bolinhas", "", cor)] = qtd_para_cor
                        add_compra("ESTOQUE", "Pacote(s) de Bolinhas", "", cor, qtd_para_cor)

        for cor, metros in metragem_tubos_por_cor.items():
            pacotes_iso = math.ceil((metros * 1.25) / 64.0)
            pacotes_fitilho = math.ceil(metros * 0.08)
            if pacotes_iso > 0: 
                relatorio["ESTOQUE"]['agregados'][("Pacote(s) de Isotubo", "", cor)] = pacotes_iso
                add_compra("ESTOQUE", "Pacote(s) de Isotubo", "", cor, pacotes_iso)
            if pacotes_fitilho > 0:
                if tem_rede_preta: fitilhos_pretos_tubos += pacotes_fitilho
                elif cor.upper() in ["PRETO", "MARROM"]: fitilhos_pretos_tubos += pacotes_fitilho
                else: fitilhos_brancos_tubos += pacotes_fitilho

        # TUBOS E MARCENARIA INTELIGENTES
        total_metros_tubo = sum(metragem_tubos_por_cor.values())
        if total_metros_tubo > 0:
            qtd_barras_6m = math.ceil(total_metros_tubo / 6.0)
            add_compra("TUBOS KID PLAY", "Tubo de Kid Play", "Barras de 6m", "", qtd_barras_6m)

        if area_marcenaria_m2 > 0:
            chapas_compensado = math.ceil(area_marcenaria_m2 / 2.42)
            add_compra("MARCENARIA", "Chapa de Compensado 18mm", "2,20x1,10m", "", chapas_compensado)

        # ---------------------------------------------------------
        # INJEÇÃO MATEMÁTICA DE LONA E MANTA DE ESPUMA PARA PISOS
        # ---------------------------------------------------------
        if area_total_espuma_m2 > 0:
            qtd_espuma = math.ceil(area_total_espuma_m2 / 9.5)
            add_compra("MATÉRIAS PRIMAS", "Manta De Espuma 7144 - 1,9Lx5Mx20Mm", "Chapa", "", qtd_espuma)

        for cor_lona, metros_lona in lona_calculada_por_cor.items():
            add_compra("MATÉRIAS PRIMAS", "Lona", "M", cor_lona, metros_lona, is_float=True)

        # ---------------------------------------------------------
        # MOTOR DE COMPOSIÇÃO - EXPLOSÃO E CONSOLIDAÇÃO
        # ---------------------------------------------------------
        for (cod_peca, cor_peca), qtd_peca in contagem_codigos_oficiais.items():
            
            nome_oficial_mestre = banco_dados.get(cod_peca, {}).get('nome', '').upper()
            is_cama_mestre = any(x in nome_oficial_mestre for x in ["CAMA ELÁSTICA", "CAMA ELASTICA", "ÁREA DE PULO", "AREA DE PULO", "PROTEÇÃO PARA CAMA", "PROTECAO PARA CAMA"])
            
            if cod_peca in dict_composicao:
                receita = dict_composicao[cod_peca]
                for mat in receita:
                    nome_mat = mat['material'].upper()
                    qtd_mat = mat['qtd'] * qtd_peca
                    unidade = str(mat['unidade']).strip().title() if pd.notna(mat['unidade']) else ""
                    
                    cor_final = ""
                    if "LONA" in nome_mat or "CINTO" in nome_mat:
                        if cor_peca and cor_peca.upper() not in ["SEM COR", "MATERIAL"]:
                            cor_final = cor_peca.title()
                            
                    nome_final_mat = mat['material'].strip().title().replace('X', 'x')

                    # TRAVA DEFINITIVA DE LONA E MANTA (IGNORA SE FOR PISO OU CAMA ELÁSTICA)
                    if cod_peca in codigos_pisos or is_cama_mestre:
                        if "LONA" in nome_mat or "MANTA" in nome_mat or "7144" in nome_mat:
                            continue
                    
                    if "MOLA" in nome_mat:
                        chave_mola = (nome_final_mat, unidade)
                        molas_para_checklist[chave_mola] = molas_para_checklist.get(chave_mola, 0) + qtd_mat
                    
                    if "ABRAÇADEIRA" in nome_mat:
                        if tem_rede_preta: abracadeira_composicao_unidades_preta += qtd_mat
                        elif cor_peca and cor_peca.upper() in ["PRETO", "MARROM"]: abracadeira_composicao_unidades_preta += qtd_mat
                        else: abracadeira_composicao_unidades_branca += qtd_mat
                        
                    elif "PARAFUSO" in nome_mat or "ARRUELA" in nome_mat or "PORCA" in nome_mat or " P." in nome_mat or nome_mat.startswith("P.") or "PF." in nome_mat or "PF " in nome_mat:
                        add_compra("PARAFUSOS E FERRAGENS", nome_final_mat, unidade, cor_final, qtd_mat, True)
                        
                    elif "TUBO" in nome_mat or "METALON" in nome_mat or "FERRO" in nome_mat or "CANTONEIRA" in nome_mat:
                        add_compra("PARAFUSOS E FERRAGENS", nome_final_mat, unidade, "", qtd_mat, True)
                    elif "COMPENSADO" in nome_mat or "MDF" in nome_mat or "EUCATEX" in nome_mat:
                        pass
                    elif "ESPUMA CILINDRICA" in nome_mat or "POLIURETANO" in nome_mat:
                        pass
                    else:
                        add_compra("MATÉRIAS PRIMAS", nome_final_mat, unidade, cor_final, qtd_mat, True)

        # (6) CHECK LIST SUPER CATEGORIZADO
        checklist_cat = {}
        def add_check(cat_nome, nome, medida, cor, qtd):
            if cat_nome not in checklist_cat: checklist_cat[cat_nome] = {}
            chave = (nome, medida, cor)
            if chave not in checklist_cat[cat_nome]: checklist_cat[cat_nome][chave] = 0
            checklist_cat[cat_nome][chave] += qtd

        cats_to_check = ["ATIVIDADES KID PLAY", "SERRALHERIA", "ROTTO BRASIL", "IMPRESSÃO", "FIBRA DE VIDRO", "ESTOQUE", "COSTURA"]
        for cat_c in cats_to_check:
            if cat_c in relatorio and 'agregados' in relatorio[cat_c]:
                for chv, q in relatorio[cat_c]['agregados'].items():
                    nome_chk = chv[0]
                    nome_chk_u = nome_chk.upper()
                    
                    if cat_c == "COSTURA" and any(x in nome_chk_u for x in ["SINUOSO 1", "SINUOSO 2", "RAMPA DE CINTA", "TURBILHÃO"]): continue
                    if any(x in nome_chk_u for x in ["CINTA DE PROTEÇÃO", "PROTEÇÃO DE CURVA", "HOLOFOTE", "CAIXA DE PARAFUSOS"]): continue
                    if "QUADRO" in nome_chk_u and any(x in nome_chk_u for x in ["PONTE", "PISO SINUOSO"]): continue
                    if cat_c == "IMPRESSÃO" and "RÉGUA" not in nome_chk_u: continue
                        
                    add_check(cat_c, nome_chk, chv[1], chv[2], q)
                    
        # --- SEPARAÇÃO DOS PISOS E CONTENÇÕES ---
        qtd_pisos_comuns = 0
        qtd_pisos_triangulo = 0
        qtd_pisos_l = 0
        qtd_cont_total = 0

        for i in items_parsed:
            if i['is_piso_contencao']:
                if i['is_contencao']:
                    qtd_cont_total += 1
                else:
                    nome_u = i['nome'].upper()
                    if "TRIANG" in nome_u or "TRIÂNG" in nome_u:
                        qtd_pisos_triangulo += 1
                    elif re.search(r'\bL\b', nome_u) or "PISO L" in nome_u:
                        qtd_pisos_l += 1
                    else:
                        qtd_pisos_comuns += 1
                
        if qtd_pisos_comuns > 0: add_check("PISOS E CONTENÇÕES", "Pisos (Soma Total)", "", "", qtd_pisos_comuns)
        if qtd_pisos_triangulo > 0: add_check("PISOS E CONTENÇÕES", "Pisos Triângulo (Soma Total)", "", "", qtd_pisos_triangulo)
        if qtd_pisos_l > 0: add_check("PISOS E CONTENÇÕES", "Pisos L (Soma Total)", "", "", qtd_pisos_l)
        if qtd_cont_total > 0: add_check("PISOS E CONTENÇÕES", "Contenções (Soma Total)", "", "", qtd_cont_total)
        
        add_check("ESTOQUE", "Caixa de Parafusos", "", "", 1)
        if (qtd_curva_360 - 1) > 0:
            add_check("ESTOQUE", "Cinta de Proteção de Curva", "", "", qtd_curva_360 - 1)
            add_check("ESTOQUE", "Holofote para Curva", "", "", qtd_curva_360 - 1)

        for (nome_mola, uni_mola), qtd_mola in molas_para_checklist.items():
            add_check("ESTOQUE", nome_mola, uni_mola, "", qtd_mola)
            
        if qtd_escorregador_2v > 0:
            add_check("ATIVIDADES KID PLAY", "Madeira de Apoio para Escorregador", "100x08", "", qtd_escorregador_2v)
        if qtd_escorregador_3v > 0:
            add_check("ATIVIDADES KID PLAY", "Madeira de Apoio para Escorregador", "150x08", "", qtd_escorregador_3v)
        if qtd_escorregador_4v > 0:
            add_check("ATIVIDADES KID PLAY", "Madeira de Apoio para Escorregador", "205x08", "", qtd_escorregador_4v)

        relatorio["CHECK LIST DE EXPEDIÇÃO"] = {'agregados_por_categoria': checklist_cat, 'agregados': {}}
        for c_dict in checklist_cat.values():
            for k, v in c_dict.items():
                relatorio["CHECK LIST DE EXPEDIÇÃO"]['agregados'][k] = v

        # (7) MOTOR DE PARAFUSOS DO CLIENTE
        if "PARAFUSOS" not in relatorio: relatorio["PARAFUSOS"] = {}
        if 'agregados' not in relatorio["PARAFUSOS"]: relatorio["PARAFUSOS"]['agregados'] = {}

        if df_paraf is not None:
            try:
                df_paraf_calc = df_paraf.copy()
                header_idx = None
                for idx, row_temp in df_paraf_calc.iterrows():
                    if str(row_temp[0]).strip().upper() == "ITENS":
                        header_idx = idx
                        break
                
                if header_idx is None:
                    raise ValueError("Tabela de parafusos inválida: cabeçalho 'ITENS' não encontrado.")

                df_paraf_calc.columns = df_paraf_calc.iloc[header_idx]
                df_paraf_calc = df_paraf_calc[header_idx+1:].fillna(0)
                col_itens = df_paraf_calc.columns[0]
                
                contagem_projeto = {}
                for item in items_parsed:
                    n_limpo = normalizar_nome_cruzamento(item['nome'])
                    contagem_projeto[n_limpo] = contagem_projeto.get(n_limpo, 0) + 1
                    
                for cat, dados_cat in relatorio.items():
                    if cat in ["PARAFUSOS", "CHECK LIST DE EXPEDIÇÃO", "LISTA DE COMPRAS"]: continue
                    if 'agregados' in dados_cat:
                        for chv, qtd in dados_cat['agregados'].items():
                            n_limpo = normalizar_nome_cruzamento(chv[0])
                            contagem_projeto[n_limpo] = max(contagem_projeto.get(n_limpo, 0), qtd)
                
                for _, row_p in df_paraf_calc.iterrows():
                    item_plan = normalizar_nome_cruzamento(row_p.get(col_itens, ''))
                    if not item_plan or item_plan == '0' or item_plan == 'NAN': continue
                    qtd_no_projeto = contagem_projeto.get(item_plan, 0)
                    
                    if qtd_no_projeto > 0:
                        for col_p in df_paraf_calc.columns[2:]:
                            if "Unnamed" in str(col_p): continue 
                            val_p = row_p[col_p]
                            try: v_num = float(val_p)
                            except: v_num = 0.0
                            
                            if v_num > 0:
                                total_paraf = int(math.ceil(v_num * qtd_no_projeto))
                                nome_p = str(col_p).strip()
                                
                                if "FITILHO" in normalizar_nome_cruzamento(nome_p) or "ABRAÇADEIRA" in normalizar_nome_cruzamento(nome_p):
                                    fitilhos_planilha_unidades += total_paraf
                                else:
                                    chv = (nome_p, "", "")
                                    if chv not in relatorio["PARAFUSOS"]['agregados']:
                                        relatorio["PARAFUSOS"]['agregados'][chv] = 0
                                    relatorio["PARAFUSOS"]['agregados'][chv] += total_paraf
                                    
                                    if "TERMINAL DE CALANDRA" not in nome_p.upper():
                                        add_compra("PARAFUSOS E FERRAGENS", nome_p.title(), "UN.", "", float(total_paraf), True)
                                        
            except Exception as ep:
                st.warning(f"Erro ao ler a tabela de parafusos de montagem: {ep}")

        relatorio["PARAFUSOS"]['agregados'][("Bujão de Kid Play", "", "")] = 30
        add_compra("PARAFUSOS E FERRAGENS", "Bujão De Kid Play", "UN.", "", 30.0, True)
        
        if total_fardos_rede > 0:
            relatorio["PARAFUSOS"]['agregados'][("Cordão", "", "")] = total_fardos_rede
            add_compra("ESTOQUE", "Cordão", "", "", total_fardos_rede)

        # ---------------------------------------------------------
        # SOMA E CONVERSÃO DE ABRAÇADEIRAS (ISOLANDO MONTAGEM x COMPRAS)
        # ---------------------------------------------------------
        pacotes_montagem_planilha = int(math.ceil(fitilhos_planilha_unidades / 100.0))
        pacotes_fabrica_comp_branca = int(math.ceil(abracadeira_composicao_unidades_branca / 100.0))
        pacotes_fabrica_comp_preta = int(math.ceil(abracadeira_composicao_unidades_preta / 100.0))
        
        parafusos_os_branca = fitilhos_brancos_tubos
        parafusos_os_preta = fitilhos_pretos_tubos
        
        if pacotes_montagem_planilha > 0:
            if tem_rede_preta: parafusos_os_preta += pacotes_montagem_planilha
            else: parafusos_os_branca += pacotes_montagem_planilha
            
        compras_global_branca = parafusos_os_branca + pacotes_fabrica_comp_branca
        compras_global_preta = parafusos_os_preta + pacotes_fabrica_comp_preta
                
        if parafusos_os_branca > 0: 
            relatorio["PARAFUSOS"]['agregados'][("Abraçadeira 340x4,8Mm", "Pacote(s)", "Branca")] = parafusos_os_branca
        if parafusos_os_preta > 0: 
            relatorio["PARAFUSOS"]['agregados'][("Abraçadeira 340x4,8Mm", "Pacote(s)", "Preta")] = parafusos_os_preta

        if compras_global_branca > 0:
            add_compra("PARAFUSOS E FERRAGENS", "Abraçadeira 340x4,8Mm", "Pacote(s)", "Branca", compras_global_branca, True)
        if compras_global_preta > 0:
            add_compra("PARAFUSOS E FERRAGENS", "Abraçadeira 340x4,8Mm", "Pacote(s)", "Preta", compras_global_preta, True)

        for cat, itens in consolidador_compras.items():
            chaves_para_remover = []
            
            for k in list(itens.keys()):
                nome_limpo = re.sub(r'\s+', ' ', k[0].strip().title())
                unidade_limpa = k[1].strip().title() if k[1] else ""
                cor_limpa = k[2].strip().title() if k[2] else ""
                nova_chave = (nome_limpo, unidade_limpa, cor_limpa)
                
                if nova_chave != k:
                    if nova_chave in itens:
                        itens[nova_chave] += itens[k]
                    else:
                        itens[nova_chave] = itens[k]
                    chaves_para_remover.append(k)
                    
            for k in chaves_para_remover:
                del itens[k]
                
            chaves_para_remover = []
            for k, v in itens.items():
                if isinstance(v, float):
                    consolidador_compras[cat][k] = math.ceil(v)
                if consolidador_compras[cat][k] == 0:
                    chaves_para_remover.append(k)
            for k in chaves_para_remover:
                del consolidador_compras[cat][k]
                    
        relatorio["LISTA DE COMPRAS"]['agregados_por_categoria'] = consolidador_compras

        # --- 8. CRIAÇÃO DO NOVO PAINEL DASHBOARD (CARDS) ---
        st.markdown("### 🖨️ Painel de Produção (Ordens de Serviço)")
        
        icones = {
            "SERRALHERIA": "🔨", "PARAFUSOS": "🔩", "ESTOQUE": "📦", "COSTURA": "🧵",
            "MARCENARIA": "🪵", "IMPRESSÃO": "🖨️", "FIBRA DE VIDRO": "🚤", "ROTTO BRASIL": "🎠",
            "ATIVIDADES KID PLAY": "🎯", "CHECK LIST DE EXPEDIÇÃO": "📋", "TUBOS KID PLAY": "🪈",
            "PISOS E CONTENÇÕES": "🧩", "CONEXÕES DE ALUMÍNIO": "🔗", "LISTA DE COMPRAS": "🛒"
        }

        setores_base = [s for s in sorted(list(relatorio.keys())) if (relatorio[s].get('agregados') or relatorio[s].get('lista_sequencial') or relatorio[s].get('agregados_por_categoria')) and s not in ["CHECK LIST DE EXPEDIÇÃO", "LISTA DE COMPRAS"]]
        
        nomes_abas = setores_base
        if "CHECK LIST DE EXPEDIÇÃO" in relatorio and relatorio["CHECK LIST DE EXPEDIÇÃO"].get('agregados'):
            nomes_abas.append("CHECK LIST DE EXPEDIÇÃO")
        if "LISTA DE COMPRAS" in relatorio and relatorio["LISTA DE COMPRAS"].get('agregados_por_categoria'):
            nomes_abas.append("LISTA DE COMPRAS")
            
        cols = st.columns(3)
        
        for i, cat in enumerate(nomes_abas):
            with cols[i % 3]:
                with st.container(border=True):
                    icone = icones.get(cat, "📁")
                    st.markdown(f"#### {icone} {cat.title()}")
                    st.markdown(f"<p style='color: #666; font-size: 14px;'>Imprimir ordem de serviço de {cat.lower()}.</p>", unsafe_allow_html=True)
                    
                    html_final = gerar_html_os(cat, relatorio[cat], cliente_final, projeto_final)
                    
                    st.download_button(
                        label="📄 Gerar OS para Impressão",
                        data=html_final.encode('utf-8'),
                        file_name=f"OS_{cat.replace(' ', '_')}.html",
                        mime="text/html",
                        key=f"btn_print_{cat}",
                        use_container_width=True
                    )
                    
                    with st.expander("Ver itens na tela"):
                        if 'lista_sequencial' in relatorio[cat]:
                            for linha in relatorio[cat]['lista_sequencial']: st.caption(linha)
                        if 'agregados' in relatorio[cat]:
                            for chave in sorted(relatorio[cat]['agregados'].keys(), key=lambda x: x[0]):
                                qtd = relatorio[cat]['agregados'][chave]
                                med_str = f" {chave[1]}" if chave[1] else ""
                                cor_str = f" {chave[2]}" if chave[2] else ""
                                st.caption(f"{qtd} - {chave[0]}{med_str}{cor_str}")
                        if 'agregados_por_categoria' in relatorio[cat]:
                            for subcat in sorted(relatorio[cat]['agregados_por_categoria'].keys()):
                                if len(relatorio[cat]['agregados_por_categoria'][subcat]) > 0:
                                    st.markdown(f"**{subcat}**")
                                    for chave in sorted(relatorio[cat]['agregados_por_categoria'][subcat].keys(), key=lambda x: x[0]):
                                        qtd = relatorio[cat]['agregados_por_categoria'][subcat][chave]
                                        med_str = f" {chave[1]}" if chave[1] else ""
                                        cor_str = f" {chave[2]}" if chave[2] else ""
                                        st.caption(f"{qtd} - {chave[0]}{med_str}{cor_str}")

        st.markdown("---")
        st.subheader("⚠️ Auditoria 3D")
        if lista_auditoria:
            st.warning("⚠️ Os seguintes itens vieram com 'Material' ou 'Sem Cor'. Verifique o 3D antes da produção:")
            for item_sem_cor in sorted(list(set(lista_auditoria))): st.markdown(f"- {item_sem_cor}")
        else:
            st.success("Tudo perfeito! 100% dos blocos com cores definidas e integrados com a produção.")

    except Exception as e:
        st.error(f"Erro no processamento: {e}")

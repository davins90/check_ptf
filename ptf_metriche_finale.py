import requests
import base64
import json
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import streamlit as st
import time

from io import BytesIO


pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)

def to_excel(df):
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, sheet_name='Sheet1')
    writer.save()
    processed_data = output.getvalue()
    return processed_data

def get_table_download_link(df):
    val = to_excel(df)
    b64 = base64.b64encode(val)  
    return f'<a href="data:application/octet-stream;base64,{b64.decode()}" download="dati_ptf.xlsx">Download excel file</a>' 

st.title('Come stanno andando i portafogli AO?')

def ptf():
    ## AUTENTICAZIONE E INGRESSO NELLA PAGINA
    website = b'admin.virtualb.it'
    username = 'daniele'
    password = 'daniele'
    auth_str = '{}:{}'.format(username, password)
    b64_auth_str = base64.b64encode(auth_str.encode())
    b64_auth_str.decode()
    url = 'https://admin.virtualb.it/portfolios/'
    headers = {'Authorization': "Basic {}".format(b64_auth_str.decode()),'Accept-Encoding': "gzip, deflate",}
    response = requests.request("GET", url, headers=headers)
    data = json.loads(response.text)
    df = pd.read_json(json.dumps((data['results'])))

    ## SELEZIONE PORTAFOGLI CORRETTI --> ELIMINO QUELLI NON PIU' ATTIVI
    df = df.iloc[16:] ## quelli di fundstore?
    df = df[df['id']!=55339] ## portafoglio pir
    df = df[df['id']!=8] ## ptf demo creato da vaghi
    df = df[df['id']!=1007] ## da qua in poi elimino i tattici che non sono più visualizzati sul sito
    df = df[df['id']!=1052]
    df = df[df['id']!=998]
    df = df[df['id']!=11]
    df = df[df['id']!=10]
    df = df[df['id']!=9]
    df = df[df['id']!=14] ## portafoglio pir 2 fatto per l'articolo di f non considerato per errore "500"
    df = df.sort_values('name_portfolio') ## rimangono 34 ptf di adviseonly

    ## PREPARO IL DF PER LA COSTRUZIONE DEL FILE FINALE
    dfg = pd.DataFrame(columns=['diversification_index','performance','maximum_drawdown','volatility','downside_volatility','sharpe_ratio','sortino_ratio','id','period'])

    ## RECUPERO I DATI DI OGNI PTF PER I VARI INTERVALLI TEMPORALI
    for i,item in enumerate(df['id'].values):
        id = item
        period = ['1m','3m','1y','10y']
        if i == 0:
            for t in period:
                if t == '1m':
                    url_single_ptf = url+'?id={}&{}=true&period={}'.format(id,'ts',t)
                    response = requests.request("GET", url_single_ptf, headers=headers)
                    data = json.loads(response.text)
                    df_mex = data['results'][0]['indicators_expost']
                    lista = list(df_mex.values())
                    lista.append(id)
                    lista.append(t)
                    dfg.loc[i] = lista
                    del lista
                else:
                    url_single_ptf = url+'?id={}&{}=true&period={}'.format(id,'ts',t)
                    response = requests.request("GET", url_single_ptf, headers=headers)
                    data = json.loads(response.text)
                    df_mex = data['results'][0]['indicators_expost']
                    lista = list(df_mex.values())
                    lista.append(id)
                    lista.append(t)
                    dfg.loc[dfg.index.max()+1,:]=lista
                    del lista
        else:
            for j in period:
                url_single_ptf = url+'?id={}&{}=true&period={}'.format(id,'ts',j)
                response = requests.request("GET", url_single_ptf, headers=headers)
                data = json.loads(response.text)
                df_mex = data['results'][0]['indicators_expost']
                lista = list(df_mex.values())
                lista.append(id)
                lista.append(j)
                dfg.loc[dfg.index.max()+1,:]=lista
                del lista

    ## CHECK DF FINALE
    # dfg
    #dfg['id'].value_counts()

    ## CREO DF FINALE
    final = pd.DataFrame(columns=['id'])
    final['id'] = dfg['id'].unique()
    # final

    df_1mese = dfg[dfg['period']=='1m']
    df_3mesi = dfg[dfg['period']=='3m']
    df_1anno = dfg[dfg['period']=='1y']
    df_si = dfg[dfg['period']=='10y']

    last = pd.merge(final,df_1mese[['id','performance']],on='id')
    last_1m = last.rename(columns={'performance':'perf_1m'})
    last_3m = pd.merge(last_1m,df_3mesi[['id','performance']],on='id')
    last_3m = last_3m.rename(columns={'performance':'perf_3m'})
    last_1y = pd.merge(last_3m,df_1anno[['id','performance']],on='id')
    last_1y = last_1y.rename(columns={'performance':'perf_1y'})
    last_si = pd.merge(last_1y,df_si[['id','sortino_ratio']],on='id')
    last_si = last_si.rename(columns={'performance':'sortino_ratio_si'})

    ptf = pd.merge(last_si,df[['id','name_portfolio']],on='id')
    ptf['group'] = 'obiettivo'
    ptf['group'] = ptf['group'].mask((ptf['name_portfolio']=='Etico') | (ptf['name_portfolio']=='Euro OK') | (ptf['name_portfolio']=='Euro Tsunami') | (ptf['name_portfolio']=='Intermedio') | (ptf['name_portfolio']=='Lazy') | (ptf['name_portfolio']=='MegaTrends') | (ptf['name_portfolio']=='Tempo Stabile'),'tematico')
    ptf['group'] = ptf['group'].mask((ptf['name_portfolio']=='Tattico RischioBasso 0-18 mesi') | (ptf['name_portfolio']=='Tattico RischioBasso 18 mesi-3 anni') | (ptf['name_portfolio']=='Tattico RischioBasso Oltre3 anni') | (ptf['name_portfolio']=='Tattico RischioMedio 0-18 mesi') | (ptf['name_portfolio']=='Tattico RischioMedio 18 mesi-3 anni') | (ptf['name_portfolio']=='Tattico RischioMedio Oltre3 anni') | (ptf['name_portfolio']=='Tattico RischioAlto 0-18 mesi') | (ptf['name_portfolio']=='Tattico RischioAlto 18 mesi-3 anni') | (ptf['name_portfolio']=='Tattico RischioAlto Oltre3 anni'),'tattico')

    ptf['name_portfolio'] = ptf['name_portfolio'].mask(ptf['name_portfolio']=='Tattico RischioMedio 18 mesi-3 anni','Rischio Medio')
    ptf['name_portfolio'] = ptf['name_portfolio'].mask(ptf['name_portfolio']=='Tattico RischioMedio 0-18 mesi','Rischio Basso')
    ptf['name_portfolio'] = ptf['name_portfolio'].mask(ptf['name_portfolio']=='Tattico RischioAlto Oltre3 anni','Rischio Alto')

    ptf1 = ptf.groupby('group').apply(pd.DataFrame.sort_values,'name_portfolio')
    ptf2 = ptf1.iloc[np.r_[0:len(ptf1)-9,-8,-9]]
    ptf3 = ptf2.append(ptf1.tail(7))
    ptf4 = ptf3.drop(columns='group')

    # ptf4 = ptf4.iloc[:,'perf_1m':'perf_1y'].mul(100)
    ptf4.iloc[:,[1,2,3]] = ptf4.iloc[:,[1,2,3]].mul(100)
    # ptf4
    # ptf4.to_excel('ptf_metriche_26_giugno.xlsx')

    ## Genero un grafico semplice
    chart = st.table(ptf4)
    time.sleep(1)
    
    ptf5 = ptf4
    st.markdown(get_table_download_link(ptf5), unsafe_allow_html=True)
    return

if st.button('Clicca qua per scaricati i dati dei ptf!'):
    ptf()
import pandas as pd
import numpy as np
import random
import multiprocessing


class Eleicao:

    def __init__(self, dicio_perc_votos, nome_estatistica, eleitores=20000, secoes=200, num_simulacoes=10):
        self.num_processadores = int(multiprocessing.cpu_count() - 2)
        if self.num_processadores < 1:
            self.num_processadores = 1

        print('Utilizando até', self.num_processadores, 'núcleos de processamento.')

        # https://www.poder360.com.br/podereleitoral/saiba-quantas-zonas-e-secoes-eleitorais-ha-no-brasil/
        # Existem 2.637 zonas eleitorais e 496.856 seções, no Brasil e no exterior e 156 milhões de eleitores
        # Input Oficial Brasil
        self.brasil_eleitores = 156000000
        self.brasil_secoes = 496856

        #Input simulação
        self.eleitores = eleitores
        self.secoes = secoes
        self.eleitores_secao = eleitores/secoes
        self.num_simulacoes = num_simulacoes
        self.nome_estatistica = nome_estatistica

        print('Ao utilizar um número MENOR de eleitores por seção, AUMENTA a chance de uma seção ter zero votos para um candidato')
        print('    Eleitores por seção na simulação:', int(self.eleitores_secao))
        print('    Eleitores por seção no Brasil:', int(self.brasil_eleitores / self.brasil_secoes))

        # DataFrame de Votos
        votos = []
        i = 0
        for item in dicio_perc_votos:
            valido = False
            if i < 2:
                valido = True
            linha = {'Quem': item, 'Prob': dicio_perc_votos[item], 'ProbAcum': 0.00, 'Valido': valido, 'PercValidos': 0.00}
            votos.append(linha)
            i += 1
        votos = pd.DataFrame(votos)
        votos['ProbAcum'] = votos['Prob'].cumsum()
        perc_valido = votos[votos['Valido']==True]['Prob'].sum()
        print('Votos validos:', perc_valido)
        for idx, row in votos.iterrows():
            if row['Valido']:
                votos.loc[idx, 'PercValidos'] = row['Prob'] / perc_valido
            else:
                votos.loc[idx, 'PercValidos'] = 0
        self.votos = votos			

    def votacao_zona(self):
        votacao = []
        urna = 1
        na_urna = -1
        for i in range(0, self.eleitores): # eleitores
            na_urna += 1
            if na_urna >= self.eleitores_secao:
                na_urna = 0
                urna += 1

            aleatorio = random.uniform(0, 1)
            voto = self.votos[self.votos['ProbAcum']>=aleatorio].head(1)

            linha = {'Aleatorio': aleatorio, 'Voto': voto.iloc[0]['Quem'], 'Seção': urna}
            votacao.append(linha)

        return pd.DataFrame(votacao)

    def simulacao_zona(self):
        votacao = self.votacao_zona()
        contagem = votacao.groupby(['Voto', 'Seção']).count().reset_index()
        contagem.columns = ['Voto', 'Seção', 'Cont']
        resultado = contagem.groupby('Voto').sum()
        resultado.insert(len(resultado.columns), 'PercVotos', [0] * len(resultado))
        resultado['PercVotos'] = resultado['Cont'] / resultado['Cont'].sum()
        return contagem, resultado

    def simulacao_zona_multi(self, linha):
        contagem, resultado = self.simulacao_zona()
        return contagem, resultado

    def roda_simulacao(self):
        print('EXECUTANDO', self.num_simulacoes, 'SIMULAÇÕES')
        print('----------------------------------------')
        print('Dados por simulação:')
        print('    eleitores:', self.eleitores)
        print('    Seções:', self.secoes)
        print('    Eleitores por seção na simulação:', int(self.eleitores_secao))
        print('    Eleitores por seção no Brasil:', int(self.brasil_eleitores / self.brasil_secoes))
        print('    * Ao utilizar um número MENOR de eleitores por seção, AUMENTA a chance de uma seção ter zero votos para um candidato')
        print('Total de eleitores', self.eleitores * self.num_simulacoes / 1000000, 'milhões.')
        print('----------------------------------------')
        print('Tabela de votação simulada')
        print(self.votos.set_index('Quem'))
        print('----------------------------------------')
        funcao_execucao = self.simulacao_zona_multi
        lista_sim = np.arange(1, self.num_simulacoes + 1, 1).tolist()
        print('Execução em paralelo...')
        with multiprocessing.Pool(processes=self.num_processadores) as pool:
            resultados = pool.map(funcao_execucao, lista_sim)
        print('Execução concluída.')
        print('Tratamento dos dados...')
        analise = []
        lin = 0
        for sim_zona in resultados:
            contagem = sim_zona[0]
            resultado = sim_zona[1]
            num_votos = resultado['Cont'].sum()
            min_bolsonaro = contagem[contagem['Voto']==self.nome_estatistica].min()
            zerados = len(contagem[(contagem['Voto']==self.nome_estatistica) & (contagem['Cont']==0)])
            unitarios = len(contagem[(contagem['Voto']==self.nome_estatistica) & (contagem['Cont']==1)])
            linha = {'Sim': lin, 'Seções': len(contagem['Seção'].unique()), 'Votos': num_votos, 'MínCandidatoem1Zona': min_bolsonaro['Cont'], 'Seções Sem Voto': zerados, 'Seções com 1 voto': unitarios}
            lin += 1	
            analise.append(linha)
        analise = pd.DataFrame(analise)
        print('----------------------------------------')
        print('Concluído.')
        print('Resultados obtidos:')
        print(analise.drop('Sim',axis=1).sum())
        print('----------------------------------------')
        print('Em', analise['Seções'].sum(), 'seções foram encontradas', analise['Seções Sem Voto'].sum(), 'sem votos para o candidato',self.nome_estatistica, '.')
        print('Em', analise['Seções'].sum(), 'seções foram encontradas', analise['Seções com 1 voto'].sum(), 'com 1 voto para o candidato',self.nome_estatistica, '.')
        print('Em', analise['Seções'].sum(), 'seções, a menor quantidade de votos para o candidato',self.nome_estatistica, 'em uma única urna foi de', analise['MínCandidatoem1Zona'].min(), '.')
        return analise

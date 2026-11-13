from datetime import time
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Aluno, Disciplina, Disponibilidade, Professor, Usuario
from .views_agendamento import proxima_data


def criar_professor(usuario, nome, valor, modalidade, verificado=False):
    conta = Usuario.objects.create_user(username=usuario, email=f'{usuario}@example.com', nome=nome)
    return Professor.objects.create(usuario=conta, formacao='Licenciatura', valor_hora=Decimal(valor),
                                    modalidade=modalidade, verificado=verificado)


class LinkHorarioPerfilTests(TestCase):
    '''Sprint 9: horário do perfil leva para a página de agendar já preenchida.'''

    def setUp(self):
        self.professor = criar_professor('prof', 'Helena', '90', 'ONLINE')
        Disponibilidade.objects.create(professor=self.professor, dia_semana=4,
                                       hora_inicio=time(14), hora_fim=time(18))
        aluno = Usuario.objects.create_user(username='bia', email='b@example.com', nome='Bia')
        Aluno.objects.create(usuario=aluno)
        self.client.force_login(aluno)

    def test_perfil_tem_link_para_agendar(self):
        resposta = self.client.get(reverse('professor_detalhe', args=[self.professor.pk]))
        link = reverse('agendar_aula', args=[self.professor.pk]) + '?dia=4&hora=14:00'
        self.assertContains(resposta, link)

    def test_agendar_vem_preenchido(self):
        url = reverse('agendar_aula', args=[self.professor.pk]) + '?dia=4&hora=14:00'
        resposta = self.client.get(url)
        data_esperada = proxima_data(4, time(14)).isoformat()
        self.assertContains(resposta, f'value="{data_esperada}"')
        self.assertContains(resposta, 'value="14:00"')

    def test_proxima_data_cai_no_dia_certo_e_no_futuro(self):
        for dia in range(7):
            data = proxima_data(dia, time(23, 59))
            self.assertEqual(data.weekday(), dia)
            self.assertGreaterEqual(data, timezone.localdate())

    def test_link_errado_nao_quebra_a_pagina(self):
        url = reverse('agendar_aula', args=[self.professor.pk])
        for parametros in ['?dia=9&hora=14:00', '?dia=abc&hora=14:00', '?dia=2&hora=xx', '?dia=²&hora=10:00']:
            resposta = self.client.get(url + parametros)
            self.assertEqual(resposta.status_code, 200)
            self.assertContains(resposta, 'name="data" min=')


class FiltroProfessoresTests(TestCase):
    '''Sprint 9: filtro mais abrangente de professores.'''

    def setUp(self):
        self.url = reverse('filtro_professores')
        self.matematica = Disciplina.objects.create(nome='Matemática')
        self.quimica = Disciplina.objects.create(nome='Química')

        self.ana = criar_professor('ana', 'Ana', '50', 'ONLINE', verificado=True)
        self.ana.disciplinas.add(self.matematica)
        Disponibilidade.objects.create(professor=self.ana, dia_semana=0, hora_inicio=time(8), hora_fim=time(11))

        self.bruno = criar_professor('bruno', 'Bruno', '120', 'PRESENCIAL')
        self.bruno.disciplinas.add(self.quimica)
        Disponibilidade.objects.create(professor=self.bruno, dia_semana=2, hora_inicio=time(19), hora_fim=time(22))

        self.carla = criar_professor('carla', 'Carla', '80', 'HIBRIDA')
        self.carla.disciplinas.add(self.matematica, self.quimica)
        Disponibilidade.objects.create(professor=self.carla, dia_semana=2, hora_inicio=time(13), hora_fim=time(17))

    def nomes(self, **filtros):
        resposta = self.client.get(self.url, filtros)
        self.assertEqual(resposta.status_code, 200)
        return [professor.nome_exibicao for professor in resposta.context['professores']]

    def test_sem_filtro_mostra_todos(self):
        self.assertEqual(self.nomes(), ['Ana', 'Bruno', 'Carla'])

    def test_disciplina(self):
        self.assertEqual(self.nomes(disciplina=self.quimica.pk), ['Bruno', 'Carla'])

    def test_modalidade_inclui_hibrida(self):
        self.assertEqual(self.nomes(modalidade='ONLINE'), ['Ana', 'Carla'])
        self.assertEqual(self.nomes(modalidade='PRESENCIAL'), ['Bruno', 'Carla'])

    def test_faixa_de_preco(self):
        self.assertEqual(self.nomes(preco_min='60', preco_max='100'), ['Carla'])
        self.assertEqual(self.nomes(preco_max='80,00'), ['Ana', 'Carla'])

    def test_dia_e_periodo(self):
        self.assertEqual(self.nomes(dia='2'), ['Bruno', 'Carla'])
        self.assertEqual(self.nomes(dia='2', periodo='noite'), ['Bruno'])
        self.assertEqual(self.nomes(periodo='manha'), ['Ana'])

    def test_verificados(self):
        self.assertEqual(self.nomes(verificado='1'), ['Ana'])

    def test_ordem_por_preco(self):
        self.assertEqual(self.nomes(ordem='menor_preco'), ['Ana', 'Carla', 'Bruno'])
        self.assertEqual(self.nomes(ordem='maior_preco'), ['Bruno', 'Carla', 'Ana'])

    def test_valores_estranhos_sao_ignorados(self):
        estranhos = {'disciplina': '99999999999999999999', 'modalidade': 'X', 'preco_min': 'abc',
                     'preco_max': 'NaN', 'dia': '8', 'periodo': 'madrugada', 'nota_min': '10', 'ordem': 'x'}
        self.assertEqual(self.nomes(**estranhos), ['Ana', 'Bruno', 'Carla'])

    def test_busca_simples_tem_link_para_filtro(self):
        resposta = self.client.get(reverse('professores'))
        self.assertContains(resposta, self.url)

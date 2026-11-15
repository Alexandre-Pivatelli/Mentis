from datetime import time
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import (Aluno, Aula, Disciplina, Disponibilidade, Material,
                     Professor, TipoMaterial, Usuario)

INSTAGRAM = 'https://www.instagram.com/plataformamentis/'


def criar_professor(usuario='prof', nome='Helena'):
    conta = Usuario.objects.create_user(username=usuario, email=f'{usuario}@example.com', nome=nome)
    professor = Professor.objects.create(usuario=conta, formacao='Licenciatura',
                                         valor_hora=Decimal('90'), modalidade='ONLINE')
    Disponibilidade.objects.create(professor=professor, dia_semana=4,
                                   hora_inicio=time(14), hora_fim=time(18))
    return professor


def criar_aluno(usuario='bia'):
    conta = Usuario.objects.create_user(username=usuario, email=f'{usuario}@example.com', nome='Bia')
    return Aluno.objects.create(usuario=conta)


class RedesSociaisTests(TestCase):
    '''As redes sociais da Mentis aparecem nas páginas públicas.'''

    def test_pagina_principal_tem_redes(self):
        self.assertContains(self.client.get(reverse('principal')), INSTAGRAM)

    def test_pagina_sobre_tem_redes(self):
        resposta = self.client.get(reverse('sobre'))
        self.assertContains(resposta, INSTAGRAM)
        self.assertContains(resposta, 'https://www.tiktok.com/@plataformamentis')
        self.assertContains(resposta, 'https://www.youtube.com/channel/UCPwyPsOV3UQhQ6QcDaSIgPQ')

    def test_perfil_do_professor_tem_redes(self):
        professor = criar_professor()
        self.assertContains(self.client.get(reverse('professor_detalhe', args=[professor.pk])), INSTAGRAM)


class BotaoAgendamentoTests(TestCase):
    '''Professor logado não vê botão nem links de agendamento.'''

    def setUp(self):
        self.professor = criar_professor()
        self.url = reverse('professor_detalhe', args=[self.professor.pk])
        self.link = reverse('agendar_aula', args=[self.professor.pk])

    def test_professor_nao_ve_agendamento_no_proprio_perfil(self):
        self.client.force_login(self.professor.usuario)
        resposta = self.client.get(self.url)
        self.assertNotContains(resposta, self.link)
        self.assertContains(resposta, '14:00')    # o horário continua aparecendo

    def test_professor_nao_ve_agendamento_no_perfil_de_outro(self):
        outro = criar_professor('prof2', 'Caio')
        self.client.force_login(outro.usuario)
        self.assertNotContains(self.client.get(self.url), self.link)

    def test_aluno_continua_vendo_agendamento(self):
        self.client.force_login(criar_aluno().usuario)
        self.assertContains(self.client.get(self.url), self.link + '?dia=4')

    def test_visitante_continua_vendo_agendamento(self):
        self.assertContains(self.client.get(self.url), self.link)


class LinksEntrePaginasTests(TestCase):
    '''O cabeçalho leva às áreas de cada tipo de usuário.'''

    def test_cabecalho_leva_para_lista_de_professores(self):
        self.assertContains(self.client.get(reverse('sobre')), f'href="{reverse("professores")}"')

    def test_aluno_tem_link_para_o_ambiente(self):
        self.client.force_login(criar_aluno().usuario)
        self.assertContains(self.client.get(reverse('sobre')), f'href="{reverse("ambiente_aluno")}"')

    def test_professor_tem_link_para_o_painel(self):
        self.client.force_login(criar_professor().usuario)
        resposta = self.client.get(reverse('sobre'))
        self.assertContains(resposta, f'href="{reverse("painel_professor")}"')
        self.assertNotContains(resposta, f'href="{reverse("ambiente_aluno")}"')

    def test_ambiente_do_aluno_leva_para_mensagens_e_materiais(self):
        self.client.force_login(criar_aluno().usuario)
        resposta = self.client.get(reverse('ambiente_aluno'))
        self.assertContains(resposta, f'href="{reverse("mensagens_aluno")}"')
        self.assertContains(resposta, f'href="{reverse("materiais")}"')


class BuscaMateriaisTests(TestCase):
    '''A página de materiais permite buscar por tipo e abre o link certo.'''

    def setUp(self):
        professor = criar_professor()
        aluno = criar_aluno()
        disciplina = Disciplina.objects.create(nome='Matemática')
        Aula.objects.create(aluno=aluno, professor=professor, disciplina=disciplina,
                            data_hora=timezone.now(), duracao_min=60, modalidade='ONLINE',
                            local_ou_link='meet', valor=Decimal('90'))
        Material.objects.create(professor=professor, disciplina=disciplina, titulo='Funções',
                                tipo=TipoMaterial.PDF, url='https://example.com/funcoes.pdf')
        Material.objects.create(professor=professor, titulo='Aula gravada',
                                tipo=TipoMaterial.VIDEO, url='https://example.com/video')
        self.client.force_login(aluno.usuario)
        self.resposta = self.client.get(reverse('materiais'))

    def test_cartao_guarda_o_tipo_para_a_busca(self):
        self.assertContains(self.resposta, 'data-tipo="PDF"')
        self.assertContains(self.resposta, 'data-tipo="Vídeo"')
        self.assertContains(self.resposta, 'id="mat-tipos"')

    def test_botao_abre_a_url_do_material(self):
        self.assertContains(self.resposta, 'href="https://example.com/funcoes.pdf"')
        self.assertContains(self.resposta, 'href="https://example.com/video"')

    def test_material_sem_disciplina_nao_mostra_none(self):
        self.assertNotContains(self.resposta, 'None')

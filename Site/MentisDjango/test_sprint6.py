from datetime import timedelta
from decimal import Decimal
from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Aluno, Aula, Disciplina, Professor, StatusAula, Usuario


class AmbienteAlunoTests(TestCase):
    def setUp(self):
        self.user = Usuario.objects.create_user(username='bia', email='bia@example.com',
                                                nome='Bia Teste', password='SenhaTeste123!')
        self.aluno = Aluno.objects.create(usuario=self.user, serie='1º ano EM', escola='Colégio Teste')
        prof_user = Usuario.objects.create_user(username='prof', email='p@example.com', nome='Prof Teste')
        prof = Professor.objects.create(usuario=prof_user, formacao='Lic.', valor_hora=Decimal('50'),
                                        modalidade='ONLINE')
        disc = Disciplina.objects.create(nome='Química')
        Aula.objects.create(aluno=self.aluno, professor=prof, disciplina=disc,
                            data_hora=timezone.now() + timedelta(days=2), duracao_min=60,
                            modalidade='ONLINE', local_ou_link='https://example.com', valor=50,
                            status=StatusAula.AGENDADA)
        self.client.force_login(self.user)

    def test_pagina_do_aluno(self):
        resposta = self.client.get(reverse('ambiente_aluno'))
        self.assertContains(resposta, 'Bia Teste')
        self.assertContains(resposta, 'BT')            # iniciais no card
        self.assertContains(resposta, 'Prof Teste')    # agenda
        self.assertContains(resposta, 'aula__status--agendada')
        self.assertContains(resposta, reverse('editar_perfil'))


class PopularProfessoresTests(TestCase):
    def test_cria_professores_sem_duplicar(self):
        call_command('popular_professores', stdout=StringIO())
        total = Professor.objects.count()
        self.assertEqual(total, 6)
        call_command('popular_professores', stdout=StringIO())  # rodar de novo
        self.assertEqual(Professor.objects.count(), total)
        helena = Professor.objects.get(usuario__username='demo_prof_helena')
        self.assertEqual(helena.disciplinas.count(), 2)
        self.assertEqual(helena.disponibilidades.count(), 3)
        self.assertEqual(helena.materiais.count(), 4)

    def test_dry_run_nao_grava(self):
        call_command('popular_professores', '--dry-run', stdout=StringIO())
        self.assertEqual(Professor.objects.count(), 0)

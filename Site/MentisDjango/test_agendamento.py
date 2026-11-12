from datetime import time, timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Aluno, Aula, Disciplina, Disponibilidade, Professor, Usuario


class AgendarAulaTests(TestCase):
    def setUp(self):
        # Professor de Química que atende todos os dias das 14h às 18h.
        prof_usuario = Usuario.objects.create_user(username='prof', email='p@example.com', nome='Helena')
        self.professor = Professor.objects.create(usuario=prof_usuario, formacao='Química',
                                                  valor_hora=Decimal('90'), modalidade='HIBRIDA')
        self.quimica = Disciplina.objects.create(nome='Química')
        self.professor.disciplinas.add(self.quimica)
        for dia in range(7):
            Disponibilidade.objects.create(professor=self.professor, dia_semana=dia,
                                           hora_inicio=time(14), hora_fim=time(18))

        aluno_usuario = Usuario.objects.create_user(username='bia', email='b@example.com', nome='Bia')
        self.aluno = Aluno.objects.create(usuario=aluno_usuario)
        self.client.force_login(aluno_usuario)

        self.url = reverse('agendar_aula', args=[self.professor.pk])
        self.amanha = (timezone.localdate() + timedelta(days=1)).isoformat()

    def enviar(self, **mudancas):
        dados = {'disciplina': self.quimica.pk, 'data': self.amanha, 'hora': '15:00', 'modalidade': 'ONLINE'}
        dados.update(mudancas)
        return self.client.post(self.url, dados)

    def test_pagina_abre(self):
        resposta = self.client.get(self.url)
        self.assertContains(resposta, 'Agendar aula com Helena')
        self.assertContains(resposta, '14:00 – 18:00')

    def test_agenda_aula_valida(self):
        resposta = self.enviar()
        self.assertEqual(resposta.status_code, 302)          # foi para a agenda
        aula = Aula.objects.get()
        self.assertEqual(aula.aluno, self.aluno)
        self.assertEqual(aula.valor, Decimal('90'))
        self.assertEqual(aula.status, 'AGENDADA')

    def test_nao_agenda_fora_do_horario(self):
        resposta = self.enviar(hora='09:00')
        self.assertContains(resposta, 'O professor não atende nesse dia e horário')
        self.assertEqual(Aula.objects.count(), 0)

    def test_nao_agenda_no_passado(self):
        ontem = (timezone.localdate() - timedelta(days=1)).isoformat()
        resposta = self.enviar(data=ontem)
        self.assertContains(resposta, 'Escolha uma data e um horário no futuro')

    def test_nao_agenda_horario_ocupado(self):
        self.enviar()                        # primeira aula às 15:00
        resposta = self.enviar(hora='15:30')  # bate com a primeira
        self.assertContains(resposta, 'Esse horário já está ocupado')
        self.assertEqual(Aula.objects.count(), 1)

    def test_professor_nao_agenda(self):
        self.client.force_login(self.professor.usuario)
        resposta = self.enviar()
        self.assertContains(resposta, 'Só contas de aluno podem marcar aulas')

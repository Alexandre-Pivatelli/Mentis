from datetime import datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import (Aluno, Assinatura, Aula, Disciplina, Pagamento, Professor,
                     Responsavel, StatusAula, Usuario)
from .painel_resumo import resumo_professor

SP = ZoneInfo('America/Sao_Paulo')


def criar_professor(usuario='prof', valor_assinatura=None):
    conta = Usuario.objects.create_user(username=usuario, email=f'{usuario}@example.com', nome='Helena')
    return Professor.objects.create(usuario=conta, formacao='Licenciatura', valor_hora=Decimal('100'),
                                    modalidade='ONLINE', valor_assinatura=valor_assinatura)


def criar_aluno(usuario='bia'):
    conta = Usuario.objects.create_user(username=usuario, email=f'{usuario}@example.com', nome='Bia')
    return Aluno.objects.create(usuario=conta)


def criar_aula(aluno, professor, quando, status=StatusAula.REALIZADA, minutos=60, valor='100'):
    disciplina, _ = Disciplina.objects.get_or_create(nome='Física')
    return Aula.objects.create(aluno=aluno, professor=professor, disciplina=disciplina, data_hora=quando,
                               duracao_min=minutos, modalidade='ONLINE', local_ou_link='meet',
                               valor=Decimal(valor), status=status)


def pagar(aula, status='PAGO', metodo='PIX'):
    responsavel = Responsavel.objects.create(nome='Mãe', email=f'resp{aula.pk}@example.com',
                                             telefone='21999990000', cpf=f'000.000.000-{aula.pk:02}')
    return Pagamento.objects.create(responsavel=responsavel, aula=aula, valor=aula.valor,
                                    metodo=metodo, status=status)


# ---------- URLS + VIEWS: histórico de pagamento ----------
class HistoricoPagamentosTests(TestCase):

    def setUp(self):
        self.professor = criar_professor()
        self.aluno = criar_aluno()
        agora = timezone.now()
        self.paga = pagar(criar_aula(self.aluno, self.professor, agora - timedelta(days=3), valor='120'))
        self.pendente = pagar(criar_aula(self.aluno, self.professor, agora - timedelta(days=1), valor='80'),
                              status='PENDENTE')
        outro = criar_aluno('outro')
        pagar(criar_aula(outro, self.professor, agora - timedelta(days=2), valor='999'))
        self.url = reverse('historico_pagamentos')
        self.client.force_login(self.aluno.usuario)

    def test_mostra_so_os_pagamentos_do_aluno_com_totais(self):
        resposta = self.client.get(self.url)
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(list(resposta.context['pagamentos']), [self.pendente, self.paga])
        self.assertEqual(resposta.context['total_pago'], Decimal('120'))
        self.assertEqual(resposta.context['total_pendente'], Decimal('80'))
        self.assertNotContains(resposta, '999,00')

    def test_filtra_por_status(self):
        pagos = self.client.get(self.url, {'status': 'pago'}).context['pagamentos']
        pendentes = self.client.get(self.url, {'status': 'pendente'}).context['pagamentos']
        self.assertEqual(list(pagos), [self.paga])
        self.assertEqual(list(pendentes), [self.pendente])

    def test_filtro_desconhecido_mostra_todos(self):
        resposta = self.client.get(self.url, {'status': 'xyz'})
        self.assertEqual(resposta.context['filtro'], '')
        self.assertEqual(len(resposta.context['pagamentos']), 2)

    def test_lista_assinaturas_nao_canceladas(self):
        Assinatura.objects.create(aluno=self.aluno, professor=self.professor, status=Assinatura.Status.ATIVA)
        resposta = self.client.get(self.url)
        self.assertContains(resposta, reverse('assinatura_professor', args=[self.professor.pk]))

    def test_visitante_vai_para_login(self):
        self.client.logout()
        resposta = self.client.get(self.url)
        self.assertEqual(resposta.status_code, 302)
        self.assertIn(reverse('login'), resposta['Location'])

    def test_professor_vai_para_o_resumo_do_painel(self):
        self.client.force_login(self.professor.usuario)
        self.assertRedirects(self.client.get(self.url), reverse('painel_professor') + '#resumo',
                             fetch_redirect_response=False)

    def test_menu_do_estudante_tem_link_de_pagamentos(self):
        self.assertContains(self.client.get(reverse('ambiente_aluno')), f'href="{self.url}"')


# ---------- HTML + CSS (e view): aluno cancelar assinatura ----------
class CancelarAssinaturaTests(TestCase):

    def setUp(self):
        self.professor = criar_professor(valor_assinatura=Decimal('49.90'))
        self.aluno = criar_aluno()
        self.pagina = reverse('assinatura_professor', args=[self.professor.pk])
        self.cancelar = reverse('cancelar_assinatura', args=[self.professor.pk])
        self.client.force_login(self.aluno.usuario)

    def assinar(self, status=Assinatura.Status.ATIVA):
        return Assinatura.objects.create(aluno=self.aluno, professor=self.professor, status=status)

    def test_pagina_mostra_botao_e_confirmacao_para_assinatura_ativa(self):
        self.assinar()
        resposta = self.client.get(self.pagina)
        self.assertContains(resposta, 'Cancelar assinatura')
        self.assertContains(resposta, 'Sim, cancelar')
        self.assertContains(resposta, f'action="{self.cancelar}"')

    def test_pedido_pendente_mostra_cancelar_pedido(self):
        self.assinar(Assinatura.Status.AGUARDANDO)
        self.assertContains(self.client.get(self.pagina), 'Cancelar pedido')

    def test_sem_assinatura_nao_mostra_cancelar(self):
        resposta = self.client.get(self.pagina)
        self.assertNotContains(resposta, 'Sim, cancelar')
        self.assertContains(resposta, 'Quero assinar')

    def test_cancelar_muda_status_e_tira_o_acesso(self):
        assinatura = self.assinar()
        resposta = self.client.post(self.cancelar)
        self.assertRedirects(resposta, self.pagina, fetch_redirect_response=False)
        assinatura.refresh_from_db()
        self.assertEqual(assinatura.status, Assinatura.Status.CANCELADA)
        self.assertContains(self.client.get(self.pagina), 'Quero assinar')

    def test_pode_assinar_de_novo_depois_de_cancelar(self):
        assinatura = self.assinar()
        self.client.post(self.cancelar)
        self.client.post(self.pagina)
        assinatura.refresh_from_db()
        self.assertEqual(assinatura.status, Assinatura.Status.AGUARDANDO)

    def test_get_nao_cancela(self):
        assinatura = self.assinar()
        self.assertEqual(self.client.get(self.cancelar).status_code, 405)
        assinatura.refresh_from_db()
        self.assertEqual(assinatura.status, Assinatura.Status.ATIVA)

    def test_aluno_nao_cancela_assinatura_de_outro(self):
        assinatura = self.assinar()
        self.client.force_login(criar_aluno('intruso').usuario)
        self.client.post(self.cancelar)
        assinatura.refresh_from_db()
        self.assertEqual(assinatura.status, Assinatura.Status.ATIVA)


# ---------- HTML + CSS: painel de informações do professor ----------
class PainelInformacoesTests(TestCase):

    def setUp(self):
        self.professor = criar_professor(valor_assinatura=Decimal('50'))
        self.aluno = criar_aluno()
        self.agora = datetime(2026, 11, 20, 12, tzinfo=SP)
        criar_aula(self.aluno, self.professor, datetime(2026, 11, 3, 10, tzinfo=SP), minutos=90, valor='150')
        criar_aula(self.aluno, self.professor, datetime(2026, 11, 10, 10, tzinfo=SP), minutos=60, valor='100')
        criar_aula(self.aluno, self.professor, datetime(2026, 10, 28, 10, tzinfo=SP), minutos=60, valor='100')
        criar_aula(self.aluno, self.professor, datetime(2026, 11, 12, 10, tzinfo=SP), status=StatusAula.CANCELADA)
        criar_aula(self.aluno, self.professor, datetime(2026, 11, 25, 10, tzinfo=SP),
                   status=StatusAula.CONFIRMADA, minutos=120, valor='200')
        Assinatura.objects.create(aluno=self.aluno, professor=self.professor, status=Assinatura.Status.ATIVA)
        Assinatura.objects.create(aluno=criar_aluno('b2'), professor=self.professor)   # aguardando: não conta

    def test_numeros_do_resumo(self):
        r = resumo_professor(self.professor, agora=self.agora)
        self.assertEqual((r['mes']['ganhos'], r['mes']['horas'], r['mes']['aulas']), (Decimal('250'), 2.5, 2))
        self.assertEqual(r['mes_passado']['ganhos'], Decimal('100'))
        self.assertEqual((r['total']['ganhos'], r['total']['aulas']), (Decimal('350'), 3))
        self.assertEqual((r['proximas']['aulas'], r['proximas']['horas']), (1, 2.0))
        self.assertEqual((r['assinantes'], r['receita_assinaturas']), (1, Decimal('50')))

    def test_painel_mostra_a_secao_de_resumo(self):
        self.client.force_login(self.professor.usuario)
        resposta = self.client.get(reverse('painel_professor'))
        self.assertContains(resposta, 'id="resumo"')
        self.assertContains(resposta, 'Ganhos no mês')
        self.assertContains(resposta, 'Assinantes ativos')

    def test_professor_sem_aulas_mostra_zeros(self):
        outro = criar_professor('novo')
        self.client.force_login(outro.usuario)
        resposta = self.client.get(reverse('painel_professor'))
        self.assertContains(resposta, 'R$ 0,00')
        self.assertContains(resposta, 'Defina o preço da assinatura')

from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import (Aluno, Assinatura, Aula, Avaliacao, Disciplina, Material,
                     Professor, StatusAula, TipoMaterial, Usuario)

LINK_SECRETO = 'https://example.com/lista-secreta.pdf'


def criar_professor(usuario='prof', nome='Helena'):
    conta = Usuario.objects.create_user(username=usuario, email=f'{usuario}@example.com', nome=nome)
    return Professor.objects.create(usuario=conta, formacao='Licenciatura',
                                    valor_hora=Decimal('90'), modalidade='ONLINE')


def criar_aluno(usuario='bia'):
    conta = Usuario.objects.create_user(username=usuario, email=f'{usuario}@example.com', nome='Bia')
    return Aluno.objects.create(usuario=conta)


def criar_aula(aluno, professor, disciplina, quando, status=StatusAula.AGENDADA):
    return Aula.objects.create(aluno=aluno, professor=professor, disciplina=disciplina,
                               data_hora=quando, duracao_min=60, modalidade='ONLINE',
                               local_ou_link='meet', valor=Decimal('90'), status=status)


# ---------- Sprint 9: plano de assinatura ----------
class PlanoAssinaturaTests(TestCase):

    def setUp(self):
        self.professor = criar_professor()
        self.client.force_login(self.professor.usuario)
        self.url = reverse('painel_professor_assinatura')

    def test_professor_salva_preco_e_pix(self):
        self.client.post(self.url, {'valor_assinatura': '49,90', 'chave_pix': 'helena@pix.com'})
        self.professor.refresh_from_db()
        self.assertEqual(self.professor.valor_assinatura, Decimal('49.90'))
        self.assertEqual(self.professor.chave_pix, 'helena@pix.com')

    def test_pagina_de_assinatura_mostra_preco_e_pix(self):
        self.client.post(self.url, {'valor_assinatura': '49.90', 'chave_pix': 'helena@pix.com'})
        self.client.force_login(criar_aluno().usuario)
        resposta = self.client.get(reverse('assinatura_professor', args=[self.professor.pk]))
        self.assertContains(resposta, '49,90')
        self.assertContains(resposta, 'helena@pix.com')
        self.assertNotContains(resposta, 'Preço não informado')

    def test_valor_invalido_nao_salva(self):
        for valor in ['abc', '0', '-10']:
            self.client.post(self.url, {'valor_assinatura': valor, 'chave_pix': 'x'})
            self.professor.refresh_from_db()
            self.assertIsNone(self.professor.valor_assinatura)

    def test_aluno_nao_altera_plano(self):
        self.client.force_login(criar_aluno().usuario)
        self.client.post(self.url, {'valor_assinatura': '10', 'chave_pix': 'golpe'})
        self.professor.refresh_from_db()
        self.assertEqual(self.professor.chave_pix, '')

    def test_painel_mostra_formulario(self):
        self.assertContains(self.client.get(reverse('painel_professor')), 'name="chave_pix"')


# ---------- Sprint 9: destino dos links do menu ----------
class DestinoLinksMenuTests(TestCase):

    def test_materiais_do_professor_leva_ao_painel(self):
        self.client.force_login(criar_professor().usuario)
        resposta = self.client.get(reverse('sobre'))
        self.assertContains(resposta, reverse('painel_professor') + '#materiais')
        self.assertRedirects(self.client.get(reverse('materiais')),
                             reverse('painel_professor') + '#materiais', fetch_redirect_response=False)

    def test_visitante_em_materiais_vai_para_login(self):
        resposta = self.client.get(reverse('materiais'))
        self.assertEqual(resposta.status_code, 302)
        self.assertIn(reverse('login'), resposta['Location'])

    def test_menu_do_estudante_diz_meu_perfil(self):
        self.client.force_login(criar_aluno().usuario)
        resposta = self.client.get(reverse('mensagens_aluno'))
        self.assertContains(resposta, 'Meu perfil')


# ---------- Sprint 8: avaliar aula ----------
class AvaliarAulaTests(TestCase):

    def setUp(self):
        self.professor = criar_professor()
        self.aluno = criar_aluno()
        self.disciplina = Disciplina.objects.create(nome='Física')
        self.passada = criar_aula(self.aluno, self.professor, self.disciplina,
                                  timezone.now() - timedelta(days=2))
        self.client.force_login(self.aluno.usuario)

    def avaliar(self, aula, nota='5', comentario='Ótima aula'):
        return self.client.post(reverse('avaliar_aula', args=[aula.pk]),
                                {'nota': nota, 'comentario': comentario})

    def test_ambiente_mostra_aula_para_avaliar(self):
        resposta = self.client.get(reverse('ambiente_aluno'))
        self.assertContains(resposta, reverse('avaliar_aula', args=[self.passada.pk]))

    def test_aluno_avalia_aula_que_ja_aconteceu(self):
        self.avaliar(self.passada, '4', 'Explicou bem')
        avaliacao = Avaliacao.objects.get(aula=self.passada)
        self.assertEqual((avaliacao.nota, avaliacao.comentario), (4, 'Explicou bem'))
        self.passada.refresh_from_db()
        self.assertEqual(self.passada.status, StatusAula.REALIZADA)

    def test_avaliacao_aparece_no_perfil_do_professor(self):
        self.avaliar(self.passada, '5', 'Recomendo muito')
        resposta = self.client.get(reverse('professor_detalhe', args=[self.professor.pk]))
        self.assertContains(resposta, 'Recomendo muito')

    def test_nao_avalia_duas_vezes(self):
        self.avaliar(self.passada, '5')
        self.avaliar(self.passada, '1')
        self.assertEqual(Avaliacao.objects.get(aula=self.passada).nota, 5)

    def test_nao_avalia_aula_futura(self):
        futura = criar_aula(self.aluno, self.professor, self.disciplina, timezone.now() + timedelta(days=1))
        self.avaliar(futura)
        self.assertFalse(Avaliacao.objects.filter(aula=futura).exists())

    def test_nao_avalia_aula_cancelada(self):
        cancelada = criar_aula(self.aluno, self.professor, self.disciplina,
                               timezone.now() - timedelta(days=3), StatusAula.CANCELADA)
        self.avaliar(cancelada)
        self.assertFalse(Avaliacao.objects.filter(aula=cancelada).exists())

    def test_nota_fora_de_1_a_5_nao_salva(self):
        for nota in ['0', '6', 'x', '']:
            self.avaliar(self.passada, nota)
        self.assertFalse(Avaliacao.objects.filter(aula=self.passada).exists())

    def test_nao_avalia_aula_de_outro_aluno(self):
        self.client.force_login(criar_aluno('intruso').usuario)
        self.assertEqual(self.avaliar(self.passada).status_code, 404)
        self.assertFalse(Avaliacao.objects.filter(aula=self.passada).exists())


# ---------- Sprint 8: proteger materiais pagos ----------
class ProtegerMateriaisTests(TestCase):

    def setUp(self):
        self.professor = criar_professor()
        Material.objects.create(professor=self.professor, titulo='Lista secreta',
                                tipo=TipoMaterial.PDF, url=LINK_SECRETO)
        self.perfil = reverse('professor_detalhe', args=[self.professor.pk])

    def test_visitante_nao_ve_o_link(self):
        resposta = self.client.get(self.perfil)
        self.assertContains(resposta, 'Lista secreta')        # o título continua visível
        self.assertNotContains(resposta, LINK_SECRETO)
        self.assertContains(resposta, 'Assine para acessar')

    def test_aluno_sem_aula_nem_assinatura_nao_ve(self):
        aluno = criar_aluno()
        Assinatura.objects.create(aluno=aluno, professor=self.professor)   # pedido ainda não pago
        self.client.force_login(aluno.usuario)
        self.assertNotContains(self.client.get(self.perfil), LINK_SECRETO)
        self.assertNotContains(self.client.get(reverse('assinatura_professor', args=[self.professor.pk])),
                               LINK_SECRETO)

    def test_aluno_com_assinatura_ativa_ve(self):
        aluno = criar_aluno()
        Assinatura.objects.create(aluno=aluno, professor=self.professor, status=Assinatura.Status.ATIVA)
        self.client.force_login(aluno.usuario)
        self.assertContains(self.client.get(self.perfil), LINK_SECRETO)
        self.assertContains(self.client.get(reverse('materiais')), LINK_SECRETO)

    def test_aluno_com_aula_ve(self):
        aluno = criar_aluno()
        criar_aula(aluno, self.professor, Disciplina.objects.create(nome='Química'), timezone.now())
        self.client.force_login(aluno.usuario)
        self.assertContains(self.client.get(self.perfil), LINK_SECRETO)

    def test_professor_dono_ve(self):
        self.client.force_login(self.professor.usuario)
        self.assertContains(self.client.get(self.perfil), LINK_SECRETO)

    def test_painel_grava_tipo_valido(self):
        self.professor.disciplinas.add(Disciplina.objects.create(nome='Biologia'))
        self.client.force_login(self.professor.usuario)
        self.client.post(reverse('painel_professor_material_criar'), {
            'disciplina': self.professor.disciplinas.first().pk, 'titulo': 'Vídeo 1',
            'tipo': 'VIDEO', 'link': 'https://example.com/v'})
        self.assertEqual(Material.objects.get(titulo='Vídeo 1').get_tipo_display(), 'Vídeo')

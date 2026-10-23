from datetime import timedelta
from django.db import IntegrityError, transaction
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.utils import timezone
from .models import Usuario, AvaliacaoSite


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class AvaliacoesSiteTests(TestCase):
    def setUp(self):
        self.user = Usuario.objects.create_user(username='aluno', nome='Alice Santos', email='a@example.com')
        self.other = Usuario.objects.create_user(username='professor', nome='Ana Cristina', email='p@example.com')

    def test_publico_le_autor_data_nota_e_texto_escapado(self):
        review = AvaliacaoSite.objects.create(usuario=self.user, nota=5, comentario='<script>alert(1)</script> Gostei da Mentis!')
        response = self.client.get(reverse('principal'))
        self.assertContains(response,'Alice Santos')
        self.assertContains(response,'&lt;script&gt;alert(1)&lt;/script&gt;')
        self.assertNotContains(response,'<script>alert(1)</script>')
        self.assertContains(response, timezone.localtime(review.criada_em).strftime('%d/%m/%Y'))
        self.assertContains(response,'Entrar para avaliar')
        self.assertNotContains(response,'name="comentario"')
        self.assertEqual(response.context['resumo_site']['media'],5)

    def test_anonimo_nao_publica_e_get_nao_muda_dados(self):
        response = self.client.post(reverse('avaliar_site'),{'nota':'5','comentario':'Gostei'})
        self.assertEqual(response.status_code,302)
        self.assertIn(reverse('login'),response.url)
        self.assertFalse(AvaliacaoSite.objects.exists())
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse('avaliar_site')).status_code,405)

    def test_publica_e_atualiza_somente_a_propria(self):
        other = AvaliacaoSite.objects.create(usuario=self.other, nota=2, comentario='De outra pessoa')
        self.client.force_login(self.user)
        response = self.client.post(reverse('avaliar_site'),{'nota':'5','comentario':'Gostei!','usuario':self.other.pk})
        self.assertRedirects(response, reverse('principal')+'?avaliacao=salva#avaliacoes')
        review = AvaliacaoSite.objects.get(usuario=self.user)
        criada = review.criada_em
        self.assertEqual(review.nota,5)
        self.assertEqual(self.client.post(reverse('avaliar_site'),{'nota':'4','comentario':'Atualizei!'}).status_code,302)
        review.refresh_from_db();other.refresh_from_db()
        self.assertEqual(review.criada_em,criada)
        self.assertEqual(review.comentario,'Atualizei!')
        self.assertEqual(other.comentario,'De outra pessoa')
        self.assertEqual(AvaliacaoSite.objects.count(),2)
        page=self.client.get(reverse('principal'))
        self.assertContains(page,'Salvar avaliação')
        self.assertEqual(page.context['resumo_site']['media'],3)

    def test_rejeita_invalidos_preserva_texto_e_avaliacao_existente(self):
        review=AvaliacaoSite.objects.create(usuario=self.user,nota=3,comentario='Original')
        self.client.force_login(self.user)
        for data in [dict(nota='0',comentario='Texto preservado'),dict(nota='6',comentario='Texto'),dict(nota='cinco',comentario='Texto'),dict(nota='5',comentario='   '),dict(nota='5',comentario='a'*1501)]:
            response=self.client.post(reverse('avaliar_site'),data)
            self.assertEqual(response.status_code,400)
            self.assertTrue(response.context['avaliacao_site_form'].errors)
            review.refresh_from_db()
            self.assertEqual(review.comentario,'Original')
            self.assertEqual(AvaliacaoSite.objects.count(),1)
        response=self.client.post(reverse('avaliar_site'),dict(nota='0',comentario='Texto preservado'))
        self.assertContains(response,'Texto preservado',status_code=400)

    def test_paginacao_recente_independente_da_busca(self):
        for i in range(8):
            u=Usuario.objects.create_user(username=f'u{i}',email=f'u{i}@example.com')
            AvaliacaoSite.objects.create(usuario=u,nota=4,comentario=f'Opinião {i}')
        first=self.client.get(reverse('principal'),{'q':'inexistente'})
        self.assertEqual(len(first.context['avaliacoes_site']),6)
        self.assertEqual(first.context['resumo_site']['total'],8)
        self.assertContains(first,'Opinião 7')
        second=self.client.get(reverse('principal'),{'review_page':2})
        self.assertEqual(len(second.context['avaliacoes_site']),2)
        self.assertContains(second,'Opinião 0')

    def test_csrf_continua_obrigatorio(self):
        client=Client(enforce_csrf_checks=True);client.force_login(self.user)
        self.assertEqual(client.post(reverse('avaliar_site'),dict(nota=5,comentario='Teste')).status_code,403)
        client.get(reverse('principal'))
        token=client.cookies['csrftoken'].value
        response=client.post(reverse('avaliar_site'),dict(nota=5,comentario='Teste',csrfmiddlewaretoken=token))
        self.assertEqual(response.status_code,302)
        self.assertEqual(AvaliacaoSite.objects.count(),1)

    def test_banco_limita_nota_e_avaliacao_unica(self):
        for nota in (0,6):
            with self.assertRaises(IntegrityError),transaction.atomic():
                AvaliacaoSite.objects.create(usuario=self.user,nota=nota,comentario='Teste')
        AvaliacaoSite.objects.create(usuario=self.user,nota=5,comentario='Teste')
        with self.assertRaises(IntegrityError),transaction.atomic():
            AvaliacaoSite.objects.create(usuario=self.user,nota=4,comentario='Duplicada')

    def test_estado_vazio_e_formulario_identificado(self):
        response=self.client.get(reverse('principal'))
        self.assertContains(response,'A primeira opinião pode ser a sua.')
        self.client.force_login(self.user)
        response=self.client.get(reverse('principal'))
        self.assertContains(response,'name="csrfmiddlewaretoken"')
        self.assertContains(response,'for="id_comentario"')
        self.assertContains(response,'data-session-url=')
        self.assertContains(response,'Publicar avaliação')

from io import BytesIO
from tempfile import TemporaryDirectory

from PIL import Image
from django.core.files.base import ContentFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from .models import Aluno, Usuario


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class CsrfPerfilTests(TestCase):
    def setUp(self):
        media = TemporaryDirectory()
        self.addCleanup(media.cleanup)
        settings = override_settings(MEDIA_ROOT=media.name)
        settings.enable()
        self.addCleanup(settings.disable)
        self.user = Usuario.objects.create_user(username='aluno', email='aluno@example.com',
                                                nome='Aluno Teste', password='UmaSenha!87419')
        Aluno.objects.create(usuario=self.user)
        buffer = BytesIO()
        Image.new('RGB', (20, 30)).save(buffer, 'PNG')
        self.user.foto.save('foto.png', ContentFile(buffer.getvalue()))
        self.client = Client(enforce_csrf_checks=True)
        self.client.force_login(self.user)

    def dados(self, token=None):
        data = dict(nome=self.user.nome, username=self.user.username, email=self.user.email,
                    **{'foto-clear': 'on'})
        if token:
            data['csrfmiddlewaretoken'] = token
        return data

    def test_token_antigo_rejeitado_e_token_atual_permite_remover(self):
        self.client.get(reverse('editar_perfil'))
        antigo = self.client.cookies['csrftoken'].value
        self.client.logout()
        self.client.force_login(self.user)
        session = self.client.get(reverse('sessao_perfil'))
        self.assertEqual(session.json()['userId'], self.user.pk)
        token = session.json()['csrfToken']
        self.assertEqual(self.client.post(reverse('editar_perfil'), self.dados(antigo)).status_code, 403)
        self.user.refresh_from_db()
        self.assertTrue(self.user.foto)
        response = self.client.post(reverse('editar_perfil'), self.dados(token))
        self.assertRedirects(response, reverse('perfil_aluno'))
        self.user.refresh_from_db()
        self.assertFalse(self.user.foto)

    def test_remocao_normal_exige_token_valido(self):
        session = self.client.get(reverse('sessao_perfil')).json()
        self.assertEqual(self.client.post(reverse('editar_perfil'), self.dados()).status_code, 403)
        self.assertEqual(self.client.post(reverse('editar_perfil'), self.dados('x' * 64)).status_code, 403)
        self.user.refresh_from_db()
        self.assertTrue(self.user.foto)
        self.assertEqual(self.client.post(reverse('editar_perfil'), self.dados(session['csrfToken'])).status_code, 302)
        self.user.refresh_from_db()
        self.assertFalse(self.user.foto)

    def test_sessao_e_formulario_nao_sao_cacheados(self):
        for name in ('editar_perfil', 'sessao_perfil'):
            response = self.client.get(reverse(name))
            self.assertIn('no-store', response.headers['Cache-Control'])
        self.assertContains(self.client.get(reverse('editar_perfil')), 'data-user-id=')

    def test_endpoint_exige_login_e_retorna_conta_atual(self):
        outro = Usuario.objects.create_user(username='outro', email='outro@example.com')
        self.client.force_login(outro)
        response = self.client.get(reverse('sessao_perfil'))
        self.assertEqual(response.json()['userId'], outro.pk)
        self.assertIn('no-store', response.headers['Cache-Control'])
        self.client.logout()
        response = self.client.get(reverse('sessao_perfil'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response.url)

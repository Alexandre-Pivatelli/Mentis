from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Aluno, Professor, Usuario


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'],
                   AUTH_SIGNUP_LIMIT=100)
class FotoPerfilTests(TestCase):
    def setUp(self):
        media = TemporaryDirectory()
        self.addCleanup(media.cleanup)
        self.media = Path(media.name)
        settings = override_settings(MEDIA_ROOT=media.name)
        settings.enable()
        self.addCleanup(settings.disable)

    def foto(self, formato='PNG'):
        buffer = BytesIO()
        Image.new('RGB', (20, 30), '#6430d8').save(buffer, formato)
        return SimpleUploadedFile(f'foto.{formato.lower()}', buffer.getvalue(),
                                  content_type=f'image/{formato.lower()}')

    def cadastro(self, tipo, username='novo'):
        return dict(user_type=tipo, nivel_estudo='MEDIO', serie='M2', nome='Pessoa Teste', username=username,
                    email=f'{username}@example.com', password1='UmaSenha!87419',
                    password2='UmaSenha!87419', formacao='Licenciatura',
                    valor_hora='50.00', modalidade='ONLINE')

    def criar_usuario(self, tipo):
        user = Usuario.objects.create_user(username=tipo, nome='Pessoa Teste',
                                           email=f'{tipo}@example.com')
        if tipo == 'professor':
            Professor.objects.create(usuario=user, formacao='Licenciatura',
                                     valor_hora=50, modalidade='ONLINE')
        else:
            Aluno.objects.create(usuario=user)
        return user

    def perfil_url(self, user):
        return (reverse('professor_detalhe', args=[user.pk])
                if hasattr(user, 'professor') else reverse('perfil_aluno'))

    def test_cadastro_envia_e_exibe_foto_para_ambos_os_papeis(self):
        for tipo in ('estudante', 'professor'):
            for formato in ('PNG', 'JPEG', 'WEBP'):
                with self.subTest(tipo=tipo, formato=formato):
                    self.client.logout()
                    data = self.cadastro(tipo, f'{tipo}_{formato}')
                    data['foto'] = self.foto(formato)
                    response = self.client.post(reverse('cadastro'), data)
                    self.assertRedirects(response, reverse('principal'))
                    user = Usuario.objects.get(username=data['username'])
                    self.assertTrue(user.foto.storage.exists(user.foto.name))
                    self.assertContains(self.client.get(self.perfil_url(user)), user.foto.url)
                    if tipo == 'professor':
                        self.assertContains(self.client.get(reverse('principal')), user.foto.url)

    def test_foto_continua_opcional_no_cadastro(self):
        for tipo in ('estudante', 'professor'):
            with self.subTest(tipo=tipo):
                self.client.logout()
                response = self.client.post(reverse('cadastro'), self.cadastro(tipo, tipo))
                self.assertEqual(response.status_code, 302)
                user = Usuario.objects.get(username=tipo)
                self.assertFalse(user.foto)
                self.assertNotContains(self.client.get(self.perfil_url(user)), 'class="profile-photo"')

    def test_cadastro_rejeita_foto_invalida_sem_criar_usuario_ou_arquivo(self):
        for tipo in ('estudante', 'professor'):
            for caso in ('corrompida', 'formato', 'tamanho'):
                with self.subTest(tipo=tipo, caso=caso):
                    data = self.cadastro(tipo)
                    if caso == 'corrompida':
                        data['foto'] = SimpleUploadedFile('foto.png', b'nao e imagem', 'image/png')
                    elif caso == 'formato':
                        data['foto'] = self.foto('GIF')
                    else:
                        data['foto'] = SimpleUploadedFile('foto.png', self.foto().read() + b'0' * (5 * 1024 * 1024))
                    response = self.client.post(reverse('cadastro'), data)
                    self.assertEqual(response.status_code, 200)
                    self.assertIn('foto', response.context['form'].errors)
                    self.assertContains(response, 'value="Pessoa Teste"')
                    self.assertFalse(Usuario.objects.exists())
                    self.assertEqual(list(self.media.rglob('*')), [])

    def test_adicionar_manter_substituir_e_remover_no_perfil(self):
        for tipo in ('estudante', 'professor'):
            with self.subTest(tipo=tipo):
                user = self.criar_usuario(tipo)
                self.client.force_login(user)
                data = dict(nome=user.nome, username=user.username, email=user.email, foto=self.foto())
                response = self.client.post(reverse('editar_perfil'), data)
                self.assertRedirects(response, self.perfil_url(user))
                user.refresh_from_db()
                original = user.foto.name
                edit_page = self.client.get(reverse('editar_perfil'))
                self.assertContains(edit_page, 'Ver foto atual')
                self.assertContains(edit_page, 'Remover foto atual')
                self.assertNotContains(edit_page, f'>{original}</a>')
                data.pop('foto')
                self.assertEqual(self.client.post(reverse('editar_perfil'), data).status_code, 302)
                user.refresh_from_db()
                self.assertEqual(user.foto.name, original)
                data['foto'] = SimpleUploadedFile('falsa.png', b'invalido')
                response = self.client.post(reverse('editar_perfil'), data)
                self.assertIn('foto', response.context['form'].errors)
                user.refresh_from_db()
                self.assertEqual(user.foto.name, original)
                data['foto'] = self.foto('JPEG')
                self.assertEqual(self.client.post(reverse('editar_perfil'), data).status_code, 302)
                user.refresh_from_db()
                self.assertNotEqual(user.foto.name, original)
                self.assertContains(self.client.get(self.perfil_url(user)), user.foto.url)
                data.pop('foto')
                data['foto-clear'] = 'on'
                self.assertEqual(self.client.post(reverse('editar_perfil'), data).status_code, 302)
                user.refresh_from_db()
                self.assertFalse(user.foto)
                self.assertNotContains(self.client.get(self.perfil_url(user)), 'class="profile-photo"')

    def test_campo_acessivel_e_multipart_nos_formularios(self):
        pages = [self.client.get(reverse('cadastro'))]
        self.client.force_login(self.criar_usuario('estudante'))
        pages.append(self.client.get(reverse('editar_perfil')))
        for response in pages:
            self.assertContains(response, 'enctype="multipart/form-data"')
            self.assertContains(response, 'name="foto"')
            self.assertContains(response, 'for="id_foto"')
            self.assertContains(response, 'PNG, JPEG ou WebP, até 5 MB.')

    def test_edicao_disponivel_apenas_ao_dono_do_perfil(self):
        for tipo in ('estudante', 'professor'):
            user = self.criar_usuario(tipo)
            self.client.force_login(user)
            self.assertContains(self.client.get(self.perfil_url(user)),
                                f'href="{reverse("editar_perfil")}"')
            if tipo == 'estudante':
                page = self.client.get(reverse('perfil_aluno'))
                self.assertContains(page, 'card_perfil_aluno.css')
                self.assertNotContains(page, 'profile__flame')
                self.assertTemplateNotUsed(page, 'ambiente_aluno.html')
            self.client.logout()
        url = self.perfil_url(user)
        self.assertNotContains(self.client.get(url), f'href="{reverse("editar_perfil")}"')
        self.client.force_login(Usuario.objects.get(username='estudante'))
        self.assertNotContains(self.client.get(url), f'href="{reverse("editar_perfil")}"')
        self.client.logout()
        self.assertEqual(self.client.post(reverse('editar_perfil'), {'foto': self.foto()}).status_code, 302)

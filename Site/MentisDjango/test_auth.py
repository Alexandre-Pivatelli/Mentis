from datetime import timedelta
from unittest.mock import patch

from django.db import IntegrityError, transaction
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from .models import Aluno, Professor, TentativaAutenticacao, Usuario


class CadastroLoginTests(TestCase):
    def dados(self, **changes):
        data = {'nome': 'Maria da Silva', 'username': 'maria', 'email': 'maria@example.com',
                'password1': 'UmaSenhaForte!9284', 'password2': 'UmaSenhaForte!9284', 'user_type': 'estudante', 'nivel_estudo': 'MEDIO', 'serie': 'M2'}
        data.update(changes)
        return data

    def test_student_created_with_hashed_password_and_session(self):
        self.assertRedirects(self.client.post('/cadastro/', self.dados()), '/')
        user = Usuario.objects.get(username='maria')
        self.assertTrue(user.check_password(self.dados()['password1']))
        self.assertNotEqual(user.password, self.dados()['password1'])
        self.assertEqual(user.nome, 'Maria da Silva')
        self.assertEqual(user.email, 'maria@example.com')
        self.assertTrue(Aluno.objects.filter(usuario=user, responsavel=None).exists())
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertEqual(int(self.client.session['_auth_user_id']), user.pk)

    def test_teacher_required_fields_and_saved_profile(self):
        data = self.dados(user_type='professor')
        response = self.client.post('/cadastro/', data)
        self.assertFormError(response.context['form'], 'formacao', 'Preencha este campo para criar seu perfil de professor.')
        self.assertFalse(Usuario.objects.exists())
        data.update(formacao='Licenciatura', valor_hora='85.50', modalidade='ONLINE')
        self.assertRedirects(self.client.post('/cadastro/', data), '/')
        professor = Professor.objects.get(usuario__username='maria')
        self.assertEqual(str(professor.valor_hora), '85.50')
        self.assertEqual(professor.formacao, 'Licenciatura')
        self.assertFalse(professor.verificado)
        self.assertContains(self.client.get('/'), f'href="/professor/{professor.pk}/">Meu perfil</a>')

    def test_duplicate_email_case_insensitive_and_username(self):
        Usuario.objects.create_user(username='existe', email='Maria@Example.com', password='OutraSenha!4285')
        response = self.client.post('/cadastro/', self.dados())
        self.assertIn('email', response.context['form'].errors)
        response = self.client.post('/cadastro/', self.dados(username='existe', email='novo@example.com'))
        self.assertIn('username', response.context['form'].errors)
        self.assertEqual(Usuario.objects.count(), 1)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Usuario.objects.create(username='outra', email='maria@example.com')

    def test_invalid_password_email_role_and_privilege_escalation(self):
        for values, field in [({'password2': 'diferente'}, 'password2'),
                              ({'password1': '123', 'password2': '123'}, 'password2'),
                              ({'email': 'invalido'}, 'email'), ({'user_type': 'admin'}, 'user_type')]:
            response = self.client.post('/cadastro/', self.dados(**values))
            self.assertIn(field, response.context['form'].errors)
        self.assertFalse(Usuario.objects.exists())
        self.client.post('/cadastro/', self.dados(is_staff='1', is_superuser='1'))
        user = Usuario.objects.get()
        self.assertFalse(user.is_staff or user.is_superuser)

    def test_profile_failure_rolls_back_user(self):
        with patch('MentisDjango.forms.Aluno.objects.create', side_effect=IntegrityError):
            response = self.client.post('/cadastro/', self.dados())
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['form'].non_field_errors())
        self.assertFalse(Usuario.objects.exists())
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_login_rotates_session_logout_invalidates_it(self):
        user = Usuario.objects.create_user(username='maria', email='maria@example.com', password='UmaSenhaForte!9284')
        session = self.client.session
        session['teste'] = True
        session.save()
        old_key = session.session_key
        response = self.client.post('/login/', {'username': 'maria', 'password': 'UmaSenhaForte!9284', 'next': '/perfil-aluno/'})
        self.assertRedirects(response, '/perfil-aluno/')
        self.assertNotEqual(old_key, self.client.session.session_key)
        self.assertEqual(int(self.client.session['_auth_user_id']), user.pk)
        self.assertRedirects(self.client.post('/sair/'), '/')
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertEqual(self.client.get('/sair/').status_code, 405)

    def test_login_invalid_inactive_generic_and_no_password_echo(self):
        Usuario.objects.create_user(username='maria', email='maria@example.com', password='UmaSenhaForte!9284', is_active=False)
        response = self.client.post('/login/', {'username': 'maria', 'password': 'UmaSenhaForte!9284'})
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertContains(response, 'Usuário ou senha incorretos')
        self.assertNotContains(response, 'UmaSenhaForte!9284')
        self.assertIn('no-store', response['Cache-Control'])

    def test_safe_redirect_preserved_after_failed_login(self):
        Usuario.objects.create_user(username='maria', email='maria@example.com', password='UmaSenhaForte!9284')
        response = self.client.post('/login/', {'username': 'maria', 'password': 'errada', 'next': '/perfil-aluno/'})
        self.assertEqual(response.context['next'], '/perfil-aluno/')
        response = self.client.post('/login/', {'username': 'maria', 'password': 'UmaSenhaForte!9284', 'next': '//evil.example/'})
        self.assertRedirects(response, '/')

    def test_signup_and_login_require_csrf(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.post('/cadastro/', self.dados()).status_code, 403)
        self.assertEqual(client.post('/login/', {'username': 'x', 'password': 'x'}).status_code, 403)
        self.assertEqual(client.post('/sair/').status_code, 403)
        self.assertFalse(Usuario.objects.exists())

    def test_https_local_origin_login_with_real_csrf_token(self):
        user = Usuario.objects.create_user(username='maria', email='maria@example.com', password='UmaSenhaForte!9284')
        for host in ('localhost:8000', '127.0.0.1:8000'):
            with self.subTest(host=host):
                client = Client(enforce_csrf_checks=True)
                client.get('/login/', HTTP_HOST=host)
                token = client.cookies['csrftoken'].value
                response = client.post('/login/', {'username': 'maria', 'password': 'UmaSenhaForte!9284',
                    'csrfmiddlewaretoken': token}, HTTP_HOST=host, HTTP_ORIGIN=f'https://{host}')
                self.assertEqual(response.status_code, 302)
                self.assertEqual(int(client.session['_auth_user_id']), user.pk)

    def test_https_local_origin_signup_with_real_csrf_token(self):
        client = Client(enforce_csrf_checks=True)
        client.get('/cadastro/', HTTP_HOST='localhost:8000')
        token = client.cookies['csrftoken'].value
        response = client.post('/cadastro/', self.dados(csrfmiddlewaretoken=token),
            HTTP_HOST='localhost:8000', HTTP_ORIGIN='https://localhost:8000')
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Aluno.objects.filter(usuario__username='maria').exists())

    def test_untrusted_origin_and_missing_token_still_rejected(self):
        client = Client(enforce_csrf_checks=True)
        client.get('/cadastro/', HTTP_HOST='localhost:8000')
        token = client.cookies['csrftoken'].value
        response = client.post('/cadastro/', self.dados(csrfmiddlewaretoken=token),
            HTTP_HOST='localhost:8000', HTTP_ORIGIN='https://evil.example')
        self.assertEqual(response.status_code, 403)
        response = client.post('/cadastro/', self.dados(),
            HTTP_HOST='localhost:8000', HTTP_ORIGIN='https://localhost:8000')
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Usuario.objects.exists())

    @override_settings(AUTH_LOGIN_LIMIT=2, AUTH_SIGNUP_LIMIT=1)
    def test_rate_limits_and_window_expiry(self):
        for _ in range(2):
            self.assertEqual(self.client.post('/login/', {'username': 'x', 'password': 'x'}).status_code, 200)
        response = self.client.post('/login/', {'username': 'x', 'password': 'x'})
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response['Retry-After'], '900')
        self.client.post('/cadastro/', {})
        self.assertEqual(self.client.post('/cadastro/', {}).status_code, 429)
        self.assertEqual(self.client.post('/login/', {}, REMOTE_ADDR='127.0.0.2').status_code, 200)
        TentativaAutenticacao.objects.update(inicio=timezone.now() - timedelta(hours=2))
        self.assertEqual(self.client.post('/login/', {}).status_code, 200)

    def test_form_preserves_values_not_passwords_and_teacher_query(self):
        response = self.client.post('/cadastro/', self.dados(password2='diferente'))
        self.assertContains(response, 'value="Maria da Silva"')
        self.assertNotContains(response, 'value="UmaSenhaForte!9284"')
        response = self.client.get('/cadastro/?tipo=professor')
        self.assertEqual(response.context['form']['user_type'].value(), 'professor')

    def test_redefinir_senha_logged_in_user(self):
        user = Usuario.objects.create_user(username='maria', email='maria@example.com', password='UmaSenhaForte!9284')
        Aluno.objects.create(usuario=user, nivel_estudo='MEDIO', serie='2º ano')
        self.assertRedirects(self.client.get('/perfil/senha/'), '/login/?next=/perfil/senha/')
        self.client.force_login(user)
        response = self.client.get('/perfil/senha/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Redefinir senha')
        self.assertContains(response, '<header class="mentis-header"', count=1)
        # Senha atual incorreta
        response = self.client.post('/perfil/senha/', {
            'old_password': 'Errada!123',
            'new_password1': 'NovaSenhaForte!999',
            'new_password2': 'NovaSenhaForte!999',
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('old_password', response.context['form'].errors)
        # Senhas novas diferentes
        response = self.client.post('/perfil/senha/', {
            'old_password': 'UmaSenhaForte!9284',
            'new_password1': 'NovaSenhaForte!999',
            'new_password2': 'OutraSenhaForte!888',
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('new_password2', response.context['form'].errors)
        # Sucesso mantendo a sessão ativa
        response = self.client.post('/perfil/senha/', {
            'old_password': 'UmaSenhaForte!9284',
            'new_password1': 'NovaSenhaForte!999',
            'new_password2': 'NovaSenhaForte!999',
        })
        self.assertRedirects(response, '/perfil-aluno/')
        user.refresh_from_db()
        self.assertTrue(user.check_password('NovaSenhaForte!999'))
        self.assertEqual(int(self.client.session['_auth_user_id']), user.pk)

from datetime import time, timedelta
from io import BytesIO, StringIO
from tempfile import TemporaryDirectory
from unittest.mock import patch

from PIL import Image
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import Aluno, Aula, Avaliacao, Disciplina, Disponibilidade, Pagamento, Professor, Responsavel, Usuario


class CorrecoesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = Usuario.objects.create_user(username='estudante', nome='Aluno Teste', email='aluno@test.com', password='Senha!92846')
        cls.aluno = Aluno.objects.create(usuario=cls.user)
        cls.teacher_user = Usuario.objects.create_user(username='professor', nome='Prof Teste', email='prof@test.com', password='Senha!92846')
        cls.professor = Professor.objects.create(usuario=cls.teacher_user, formacao='Licenciatura', valor_hora=50, modalidade='ONLINE')
        cls.disciplina = Disciplina.objects.create(nome='Matemática')
        cls.professor.disciplinas.add(cls.disciplina)
        cls.staff = Usuario.objects.create_superuser(username='admin', email='admin@test.com', password='Senha!92846')

    def aula(self, **values):
        data = dict(aluno=self.aluno, professor=self.professor, disciplina=self.disciplina,
                    data_hora=timezone.now() + timedelta(days=2), duracao_min=60,
                    modalidade='ONLINE', local_ou_link='https://example.com', valor=50)
        data.update(values)
        return Aula.objects.create(**data)

    def test_admin_cria_e_troca_senha_com_hash(self):
        self.client.force_login(self.staff)
        response = self.client.post(reverse('admin:MentisDjango_usuario_add'), {
            'username': 'novo', 'nome': 'Novo Usuario', 'email': 'novo@test.com',
            'password1': 'SenhaNova!75982', 'password2': 'SenhaNova!75982', 'usable_password': 'true'})
        self.assertEqual(response.status_code, 302)
        user = Usuario.objects.get(username='novo')
        self.assertTrue(user.check_password('SenhaNova!75982'))
        self.assertNotEqual(user.password, 'SenhaNova!75982')
        response = self.client.post(reverse('admin:auth_user_password_change', args=[user.pk]), {
            'password1': 'OutraSenha!39572', 'password2': 'OutraSenha!39572', 'usable_password': 'true'})
        self.assertEqual(response.status_code, 302)
        user.refresh_from_db()
        self.assertTrue(user.check_password('OutraSenha!39572'))
        self.assertTrue(self.client.login(username='novo', password='OutraSenha!39572'))

    def test_cadastro_campos_erros_e_dados_preservados(self):
        data = dict(nome='Nova Professora', username='nova', email='prof@test.com', user_type='professor',
                    password1='SenhaNova!75982', password2='SenhaNova!75982')
        response = self.client.post(reverse('cadastro'), data)
        self.assertContains(response, 'Este e-mail já está cadastrado')
        self.assertContains(response, 'value="Nova Professora"')
        self.assertEqual(response.context['form']['user_type'].value(), 'professor')
        for name in ('formacao', 'valor_hora', 'modalidade'):
            self.assertContains(response, f'name="{name}"')
            self.assertIn(name, response.context['form'].errors)
        self.assertContains(response, 'Preencha este campo para criar seu perfil de professor.')
        data.update(email='nova@test.com', formacao='Licenciatura', valor_hora='75.50', modalidade='ONLINE')
        self.assertEqual(self.client.post(reverse('cadastro'), data).status_code, 302)
        self.assertEqual(str(Professor.objects.get(usuario__username='nova').valor_hora), '75.50')

    def test_cadastro_salva_serie_e_escola(self):
        response = self.client.post(reverse('cadastro'), dict(nome='Novo Aluno', username='novo',
            email='novo@test.com', user_type='estudante', serie='Ensino Médio', escola='Escola Teste',
            password1='SenhaNova!75982', password2='SenhaNova!75982'))
        self.assertEqual(response.status_code, 302)
        aluno = Aluno.objects.get(usuario__username='novo')
        self.assertEqual((aluno.serie, aluno.escola), ('Ensino Médio', 'Escola Teste'))

    def test_edicao_rejeita_invalidos_e_duplicados(self):
        self.client.force_login(self.user)
        original = (self.user.nome, self.user.username, self.user.email)
        for changes in ({'email': self.teacher_user.email.upper()}, {'username': self.teacher_user.username},
                        {'email': 'invalido'}, {'nome': ''}, {'username': 'nome invalido!'}):
            data = dict(zip(('nome', 'username', 'email'), original))
            data.update(changes)
            response = self.client.post(reverse('editar_perfil'), data)
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context['form'].errors)
            self.user.refresh_from_db()
            self.assertEqual((self.user.nome, self.user.username, self.user.email), original)
        self.assertEqual(self.client.post(reverse('editar_perfil'), {}).status_code, 200)

    def test_edicao_trata_concorrencia(self):
        self.client.force_login(self.user)
        with patch('MentisDjango.forms.EditarPerfilForm.save', side_effect=IntegrityError):
            response = self.client.post(reverse('editar_perfil'), {'nome': 'Novo', 'username': 'estudante', 'email': self.user.email})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['form'].non_field_errors())

    def test_foto_bio_e_redirecionamento_por_perfil(self):
        with TemporaryDirectory() as media, override_settings(MEDIA_ROOT=media):
            for user, url in [(self.user, reverse('ambiente_aluno')), (self.teacher_user, reverse('professor_detalhe', args=[self.professor.pk]))]:
                self.client.force_login(user)
                buffer = BytesIO()
                Image.new('RGB', (8, 8)).save(buffer, 'PNG')
                photo = SimpleUploadedFile('foto.png', buffer.getvalue(), content_type='image/png')
                response = self.client.post(reverse('editar_perfil'), dict(nome=user.nome, username=user.username,
                    email=user.email, bio='Biografia salva', foto=photo))
                self.assertRedirects(response, url)
                user.refresh_from_db()
                self.assertTrue(user.foto.storage.exists(user.foto.name))
                self.assertEqual(user.bio, 'Biografia salva')
                self.assertContains(self.client.get(url), user.foto.url)
                self.assertContains(self.client.get(url), 'Biografia salva')
                self.assertContains(self.client.get(reverse('editar_perfil')), f'href="{url}"')
            self.professor.refresh_from_db()
            self.assertEqual(self.professor.bio, 'Biografia salva')

    def test_upload_invalido(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('editar_perfil'), dict(nome=self.user.nome, username=self.user.username,
            email=self.user.email, foto=SimpleUploadedFile('arquivo.png', b'nao e uma imagem')))
        self.assertIn('foto', response.context['form'].errors)

    def test_foto_pode_ser_removida_e_tem_limite(self):
        self.client.force_login(self.user)
        with TemporaryDirectory() as media, override_settings(MEDIA_ROOT=media):
            data = dict(nome=self.user.nome, username=self.user.username, email=self.user.email)
            buffer = BytesIO()
            Image.new('RGB', (8, 8)).save(buffer, 'PNG')
            data['foto'] = SimpleUploadedFile('foto.png', buffer.getvalue())
            self.assertEqual(self.client.post(reverse('editar_perfil'), data).status_code, 302)
            data.pop('foto')
            data['foto-clear'] = 'on'
            self.assertEqual(self.client.post(reverse('editar_perfil'), data).status_code, 302)
            self.user.refresh_from_db()
            self.assertFalse(self.user.foto)
            data.pop('foto-clear')
            data['foto'] = SimpleUploadedFile('grande.png', buffer.getvalue() + b'0' * (5 * 1024 * 1024))
            response = self.client.post(reverse('editar_perfil'), data)
            self.assertIn('foto', response.context['form'].errors)

    @override_settings(AUTH_SIGNUP_LIMIT=0)
    def test_limite_preserva_dados_sem_expor_senha(self):
        response = self.client.post(reverse('cadastro'), dict(nome='Nome Preservado', username='novo',
            email='novo@test.com', user_type='professor', password1='Senha!92846', password2='Senha!92846'))
        self.assertEqual(response.status_code, 429)
        self.assertContains(response, 'value="Nome Preservado"', status_code=429)
        self.assertEqual(response.context['form']['user_type'].value(), 'professor')
        self.assertNotContains(response, 'value="Senha!92846"', status_code=429)

    def test_agenda_apenas_futuras_e_total_sem_truncar(self):
        for _ in range(11):
            self.aula(data_hora=timezone.now() - timedelta(days=1))
            self.aula()
        self.aula(status='CANCELADA')
        self.client.force_login(self.user)
        for name in ('ambiente_aluno', 'perfil_aluno'):
            response = self.client.get(reverse(name))
            self.assertEqual(len(response.context['agenda']), 10)
            self.assertTrue(all(a.data_hora > timezone.now() for a in response.context['agenda']))
        self.assertEqual(self.client.get(reverse('ambiente_aluno')).context['total_proximas_aulas'], 11)

    def test_filtro_resiste_a_valores_invalidos(self):
        for value in ('²', '9' * 5000, '-1', 'abc', '9223372036854775808'):
            response = self.client.get('/', {'disciplina': value})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context['disciplina_selecionada'], '')
        self.assertEqual(self.client.get('/', {'disciplina': self.disciplina.pk}).context['professores'].paginator.count, 1)

    def test_validacao_e_constraints(self):
        aula = self.aula()
        responsavel = Responsavel.objects.create(nome='Resp', email='resp@test.com', telefone='123', cpf='123')
        invalidos = [
            (Aula, aula.pk, {'duracao_min': -1}), (Aula, aula.pk, {'valor': -1}),
            (Professor, self.professor.pk, {'valor_hora': 0}),
        ]
        for model, pk, values in invalidos:
            obj = model.objects.get(pk=pk)
            for name, value in values.items(): setattr(obj, name, value)
            with self.assertRaises(ValidationError): obj.full_clean()
            with self.assertRaises(IntegrityError), transaction.atomic(): model.objects.filter(pk=pk).update(**values)
        for obj in [Avaliacao(aula=aula, nota=99), Pagamento(aula=aula, responsavel=responsavel, valor=-1, metodo='PIX', status='PAGO'),
                    Disponibilidade(professor=self.professor, dia_semana=99, hora_inicio=time(9), hora_fim=time(18)),
                    Disponibilidade(professor=self.professor, dia_semana=0, hora_inicio=time(18), hora_fim=time(9))]:
            with self.assertRaises(ValidationError): obj.full_clean()
            with self.assertRaises(IntegrityError), transaction.atomic(): obj.save()

    def test_cabecalho_unico_em_todas_as_telas(self):
        for url in ('/', '/login/', '/cadastro/', f'/professor/{self.professor.pk}/'):
            response = self.client.get(url)
            self.assertTemplateUsed(response, 'base.html')
            self.assertTemplateUsed(response, 'includes/header.html')
            self.assertContains(response, '<header ', count=1)
        self.client.force_login(self.staff)
        for name in ('usuarios', 'editar_perfil', 'perfil_aluno', 'ambiente_aluno'):
            response = self.client.get(reverse(name))
            self.assertTemplateUsed(response, 'base.html')
            self.assertContains(response, '<header ', count=1)

    def test_collectstatic(self):
        with TemporaryDirectory() as root, override_settings(STATIC_ROOT=root):
            call_command('collectstatic', interactive=False, verbosity=0, stdout=StringIO())
            from pathlib import Path
            self.assertTrue((Path(root) / 'css/header.css').is_file())

from datetime import time
from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from .models import Usuario, Professor, Aluno, Responsavel, Disciplina, Aula, Avaliacao, Material, Disponibilidade


class ViewsBancoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.prof_user = Usuario.objects.create_user(username='prof', email='prof@example.com', nome='Professora Banco', password='SenhaTeste123!')
        cls.prof = Professor.objects.create(usuario=cls.prof_user, bio='Biografia do banco', formacao='Licenciatura', valor_hora=Decimal('85.50'), modalidade='ONLINE')
        cls.disc = Disciplina.objects.create(nome='Química')
        cls.prof.disciplinas.add(cls.disc)
        cls.staff = Usuario.objects.create_user(username='equipe', email='equipe@example.com', nome='Equipe', is_staff=True, password='SenhaTeste123!')
        cls.user = Usuario.objects.create_user(username='aluno', email='aluno@example.com', nome='Aluno do Banco', password='SenhaTeste123!')
        guardian = Responsavel.objects.create(nome='Responsável', email='resp@example.com', cpf='DEMO-1', telefone='000')
        cls.aluno = Aluno.objects.create(usuario=cls.user, responsavel=guardian, serie='9º ano', escola='Escola do Banco')
        cls.aula = Aula.objects.create(aluno=cls.aluno, professor=cls.prof, disciplina=cls.disc, data_hora=timezone.now(), duracao_min=60, modalidade='ONLINE', local_ou_link='https://example.com/', valor=85, status='REALIZADA')
        Avaliacao.objects.create(aula=cls.aula, nota=0, comentario='Comentário do banco')
        Material.objects.create(professor=cls.prof, disciplina=cls.disc, titulo='Material do Banco', tipo='PDF', url='https://example.com/material')
        Disponibilidade.objects.create(professor=cls.prof, dia_semana=0, hora_inicio=time(9), hora_fim=time(12))

    def test_home_and_search(self):
        response = self.client.get(reverse('principal'))
        self.assertContains(response, 'Professora Banco')
        self.assertContains(response, 'Biografia do banco')
        self.assertEqual(response.context['professores'][0].nota_media, 0)
        self.assertEqual(self.client.get('/', {'q': 'Química'}).context['professores'].paginator.count, 1)
        self.assertContains(self.client.get('/', {'q': 'inexistente'}), 'Nenhum professor encontrado')
        self.assertEqual(self.client.get('/', {'disciplina': self.disc.pk}).context['professores'].paginator.count, 1)

    def test_professor_detail_and_counts(self):
        response = self.client.get(reverse('professor_detalhe', args=[self.prof.pk]))
        self.assertContains(response, 'Material do Banco')
        self.assertContains(response, 'Comentário do banco')
        self.assertContains(response, 'Segunda-feira')
        self.assertEqual(response.context['professor'].total_avaliacoes, 1)
        self.assertEqual(response.context['professor'].aulas_realizadas, 1)
        self.assertEqual(self.client.get('/professor/999999/').status_code, 404)
        self.assertRedirects(self.client.get('/professor/'), reverse('professor_detalhe', args=[self.prof.pk]))

    def test_private_pages_require_login(self):
        self.assertEqual(self.client.get('/usuarios/').status_code, 302)
        self.assertEqual(self.client.get('/perfil-aluno/').status_code, 302)

    def test_student_cannot_read_user_list(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get('/usuarios/').status_code, 403)

    def test_staff_user_list_and_search(self):
        self.client.force_login(self.staff)
        response = self.client.get('/usuarios/', {'q': 'aluno@example.com'})
        self.assertContains(response, 'Aluno do Banco')
        self.assertEqual(response.context['usuarios'].paginator.count, 1)
        self.assertContains(response, reverse('admin:MentisDjango_usuario_change', args=[self.user.pk]))

    def test_profile_uses_logged_in_student(self):
        self.client.force_login(self.user)
        response = self.client.get('/perfil-aluno/', {'aluno': self.prof_user.pk})
        self.assertContains(response, 'Aluno do Banco')
        self.assertContains(response, 'Escola do Banco')
        self.assertEqual(response.context['aluno'].pk, self.user.pk)
        self.assertEqual(response.context['nota_media'], 0)

    def test_missing_student_profile(self):
        self.client.force_login(self.prof_user)
        self.assertContains(self.client.get('/perfil-aluno/'), 'não possui um perfil de aluno')

    def test_real_login_and_logout(self):
        response = self.client.post('/login/', {'username': 'aluno', 'password': 'SenhaTeste123!', 'next': '/perfil-aluno/'})
        self.assertRedirects(response, '/perfil-aluno/')
        self.assertEqual(self.client.get('/sair/').status_code, 405)
        self.assertRedirects(self.client.post('/sair/'), '/')

    def test_external_redirect_blocked(self):
        response = self.client.post('/login/', {'username': 'aluno', 'password': 'SenhaTeste123!', 'next': 'https://example.com/externo'})
        self.assertRedirects(response, '/')

    def test_invalid_login_and_csrf(self):
        response = self.client.post('/login/', {'username': 'aluno', 'password': 'errada'})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertEqual(Client(enforce_csrf_checks=True).post('/login/', {'username': 'aluno', 'password': 'x'}).status_code, 403)

    def test_empty_database(self):
        Material.objects.all().delete()
        Avaliacao.objects.all().delete()
        Aula.objects.all().delete()
        Disponibilidade.objects.all().delete()
        Professor.objects.all().delete()
        self.assertContains(self.client.get('/'), 'Nenhum professor encontrado')
        self.assertRedirects(self.client.get('/professor/'), '/')

    def test_pagination_invalid_page(self):
        self.assertEqual(self.client.get('/', {'page': 'invalida'}).status_code, 200)
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get('/usuarios/', {'page': '99999'}).status_code, 200)

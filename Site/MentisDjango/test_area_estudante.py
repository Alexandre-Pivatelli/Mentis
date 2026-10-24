from datetime import datetime
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.utils import timezone
from .forms import CadastroForm
from .models import Aluno, Usuario, Professor, Conversa, Mensagem, Aula, Disciplina


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class AreaEstudanteTests(TestCase):
    def setUp(self):
        self.user = Usuario.objects.create_user(username='aluno', nome='Aluno Teste', email='a@example.com')
        self.aluno = Aluno.objects.create(usuario=self.user)
        self.teacher = Usuario.objects.create_user(username='prof', nome='Ana Cristina', email='p@example.com')
        self.prof = Professor.objects.create(usuario=self.teacher, formacao='Licenciatura', valor_hora=50, modalidade='ONLINE')
        self.outro = Usuario.objects.create_user(username='outro', email='o@example.com')
        Aluno.objects.create(usuario=self.outro)
        self.conversa = Conversa.objects.create(aluno=self.aluno, professor=self.prof)
        self.client.force_login(self.user)

    def cadastro(self, **changes):
        data = dict(user_type='estudante', nome='Nova Pessoa', username='nova', email='n@example.com',
            password1='UmaSenha!82739', password2='UmaSenha!82739', nivel_estudo='MEDIO', serie='M2')
        data.update(changes)
        return CadastroForm(data)

    def test_niveis_series_e_periodos_validos_recebem_novato(self):
        for nivel, etapa, label in [('FUNDAMENTAL','F9','9º ano'),('MEDIO','M3','3º ano'),('GRADUACAO','G12','12º período')]:
            with self.subTest(nivel=nivel):
                form = self.cadastro(nivel_estudo=nivel, serie=etapa, username=nivel, email=nivel+'@example.com')
                self.assertTrue(form.is_valid(), form.errors)
                user = form.save()
                self.assertEqual(user.aluno.serie, label)
                self.assertEqual(user.aluno.nivel_estudo, nivel)
                self.assertTrue(user.aluno.novato)
                self.client.force_login(user)
                self.assertContains(self.client.get(reverse('perfil_aluno')), 'novato-tag')

    def test_estudos_obrigatorios_e_combinacoes_invalidas(self):
        for changes in [dict(nivel_estudo=''), dict(serie=''), dict(nivel_estudo='GRADUACAO',serie='M1'), dict(serie='M4'), dict(serie='F10'),dict(serie='G99'),dict(nivel_estudo='DOUTORADO')]:
            form = self.cadastro(**changes)
            self.assertFalse(form.is_valid())
        form = self.cadastro(user_type='professor',nivel_estudo='',serie='',formacao='Licenciatura',valor_hora='50',modalidade='ONLINE')
        self.assertTrue(form.is_valid(),form.errors)

    def test_aluno_e_professor_trocam_mensagens_e_marcam_leitura(self):
        url = reverse('mensagens_aluno')+f'?conversa={self.conversa.pk}'
        response = self.client.post(url, {'texto':'Olá professora! <script>teste</script>'})
        self.assertEqual(response.status_code,302)
        msg = Mensagem.objects.get()
        self.assertIsNone(msg.lida_em)
        self.client.force_login(self.teacher)
        response = self.client.get(url)
        self.assertContains(response,'&lt;script&gt;teste&lt;/script&gt;')
        msg.refresh_from_db(); self.assertIsNotNone(msg.lida_em)
        self.assertEqual(self.client.post(url, {'texto':'Olá, vamos estudar?'}).status_code,302)
        self.client.force_login(self.user)
        data = self.client.get(url+'&format=json&apos='+str(msg.pk)).json()
        self.assertEqual(len(data['mensagens']),1)
        self.assertFalse(data['mensagens'][0]['minha'])

    def test_conversas_privadas_e_limites(self):
        url = reverse('mensagens_aluno')+f'?conversa={self.conversa.pk}'
        self.client.force_login(self.outro)
        self.assertEqual(self.client.get(url).status_code,404)
        self.assertEqual(self.client.post(url,{'texto':'intruso'}).status_code,404)
        self.client.force_login(self.user)
        for texto in ['', '   ', 'a'*3001]:
            self.assertEqual(self.client.post(url,{'texto':texto}).status_code,200)
        self.assertFalse(Mensagem.objects.exists())
        for _ in range(2):
            self.assertEqual(self.client.post(reverse('mensagens_aluno'),{'acao':'nova','professor':self.prof.pk}).status_code,302)
        self.assertEqual(Conversa.objects.count(),1)
        self.assertEqual(Client(enforce_csrf_checks=True).post(url,{'texto':'x'}).status_code,403)

    def test_agenda_mes_dia_e_privacidade(self):
        disc = Disciplina.objects.create(nome='Matemática')
        Aula.objects.create(aluno=self.aluno,professor=self.prof,disciplina=disc,
            data_hora=timezone.make_aware(datetime(2026,10,23,14)),duracao_min=60,modalidade='ONLINE',local_ou_link='',valor=50)
        url=reverse('agenda_aluno')
        response=self.client.get(url,{'mes':'2026-10-01','dia':'2026-10-23'})
        self.assertContains(response,'Matemática')
        self.assertContains(response,'14:00')
        self.assertEqual(response.context['total_mes'],1)
        self.assertEqual(self.client.get(url,{'mes':'2026-11-01'}).context['total_mes'],0)
        self.assertEqual(self.client.get(url,{'mes':'invalido','dia':'invalido'}).status_code,200)
        self.client.force_login(self.outro)
        self.assertNotContains(self.client.get(url,{'mes':'2026-10-01','dia':'2026-10-23'}),'Matemática')
        self.client.logout()
        self.assertEqual(self.client.get(url).status_code,302)
        self.assertEqual(self.client.get(reverse('mensagens_aluno')).status_code,302)

    def test_historico_paginado_e_nova_conversa_sem_escrever_mensagem(self):
        Mensagem.objects.bulk_create([Mensagem(conversa=self.conversa,autor=self.teacher,texto=f'Mensagem {i}') for i in range(105)])
        url=reverse('mensagens_aluno')+f'?conversa={self.conversa.pk}'
        recent=self.client.get(url)
        self.assertEqual(len(recent.context['mensagens']),100)
        self.assertTrue(recent.context['tem_anteriores'])
        oldest=recent.context['mensagens'][0].pk
        previous=self.client.get(url+'&antes='+str(oldest))
        self.assertEqual(len(previous.context['mensagens']),5)
        self.assertFalse(previous.context['tem_anteriores'])
        self.assertEqual(len(self.client.get(url+'&format=json&apos='+str(oldest)).json()['mensagens']),99)
        self.assertEqual(self.client.get(reverse('mensagens_aluno')).status_code,200)

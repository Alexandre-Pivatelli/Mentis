from django.db import IntegrityError, transaction
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from .models import Aluno, Aula, Avaliacao, Disciplina, Favorito, Professor, Usuario
from django.utils import timezone


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class FavoritosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = Usuario.objects.create_user(username='aluna', nome='Aluna', email='aluna@test.com')
        cls.aluno = Aluno.objects.create(usuario=cls.user)
        cls.other = Usuario.objects.create_user(username='outro', email='outro@test.com')
        cls.outro_aluno = Aluno.objects.create(usuario=cls.other)
        cls.teacher = Usuario.objects.create_user(username='ana', nome='Ana Matemática', email='ana@test.com')
        cls.prof = Professor.objects.create(usuario=cls.teacher, formacao='Licenciatura',
                                           valor_hora=80, modalidade='ONLINE', bio='Álgebra e geometria')
        cls.disc = Disciplina.objects.create(nome='Matemática')
        cls.prof.disciplinas.add(cls.disc)
        cls.url = reverse('favorito_professor', args=[cls.prof.pk])
        cls.lista = reverse('favoritos_aluno')

    def setUp(self):
        self.client.force_login(self.user)

    def test_adicionar_remover_e_repetir_sao_idempotentes(self):
        for _ in range(2):
            self.assertRedirects(self.client.post(self.url, {'acao': 'adicionar'}), self.lista)
        self.assertEqual(Favorito.objects.filter(aluno=self.aluno, professor=self.prof).count(), 1)
        for _ in range(2):
            self.assertRedirects(self.client.post(self.url, {'acao': 'remover'}), self.lista)
        self.assertFalse(Favorito.objects.exists())

    def test_banco_impede_duplicatas(self):
        Favorito.objects.create(aluno=self.aluno, professor=self.prof)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Favorito.objects.create(aluno=self.aluno, professor=self.prof)

    def test_json_e_estado_nas_tres_telas(self):
        response = self.client.post(self.url, {'acao': 'adicionar'}, HTTP_ACCEPT='application/json')
        self.assertTrue(response.json()['favorito'])
        for url in ['/', reverse('professores'), reverse('professor_detalhe', args=[self.prof.pk])]:
            response = self.client.get(url)
            self.assertContains(response, 'data-favorite-form')
            self.assertContains(response, 'aria-pressed="true"')
        self.assertFalse(self.client.post(self.url, {'acao': 'remover'}, HTTP_ACCEPT='application/json').json()['favorito'])

    def test_alunos_nao_compartilham_favoritos(self):
        Favorito.objects.create(aluno=self.outro_aluno, professor=self.prof)
        self.assertEqual(self.client.get(self.lista).context['total_favoritos'], 0)
        self.client.post(self.url, {'acao': 'remover', 'aluno': self.outro_aluno.pk})
        self.assertTrue(Favorito.objects.filter(aluno=self.outro_aluno).exists())
        self.client.post(self.url, {'acao': 'adicionar', 'aluno': self.outro_aluno.pk})
        self.assertEqual(Favorito.objects.count(), 2)

    def test_exige_login_e_perfil_de_aluno(self):
        self.client.logout()
        self.assertRedirects(self.client.get(self.lista), reverse('login') + '?next=' + self.lista)
        self.assertEqual(self.client.post(self.url, {'acao': 'adicionar'}).status_code, 302)
        self.client.force_login(self.teacher)
        self.assertEqual(self.client.get(self.lista).status_code, 403)
        self.assertEqual(self.client.post(self.url, {'acao': 'adicionar'}).status_code, 403)
        self.assertNotContains(self.client.get(reverse('professores')), 'data-favorite-form')
        self.assertFalse(Favorito.objects.exists())

    def test_get_nao_altera_e_acao_invalida_nao_grava(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)
        for acao in ['', 'alternar', 'ADICIONAR']:
            self.assertEqual(self.client.post(self.url, {'acao': acao}).status_code, 400)
        self.assertFalse(Favorito.objects.exists())

    def test_csrf_obrigatorio(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        self.assertEqual(client.post(self.url, {'acao': 'adicionar'}).status_code, 403)
        client.get(reverse('professores'))
        token = client.cookies['csrftoken'].value
        self.assertEqual(client.post(self.url, {'acao': 'adicionar'}, HTTP_X_CSRFTOKEN=token).status_code, 302)

    def test_redirecionamento_preserva_filtros_e_rejeita_destino_externo(self):
        destino = reverse('professores') + '?q=Ana&disciplina=1&page=2'
        self.assertRedirects(self.client.post(self.url, {'acao': 'adicionar', 'next': destino}), destino)
        for destino in ['https://externo.test/', '//externo.test/', 'javascript:alert(1)']:
            self.assertRedirects(self.client.post(self.url, {'acao': 'remover', 'next': destino}), self.lista)

    def test_professor_inexistente_inativo_ou_proprio(self):
        self.assertEqual(self.client.post(reverse('favorito_professor', args=[999999]), {'acao': 'adicionar'}).status_code, 404)
        self.teacher.is_active = False
        self.teacher.save(update_fields=['is_active'])
        self.assertEqual(self.client.post(self.url, {'acao': 'adicionar'}).status_code, 404)
        propria = Professor.objects.create(usuario=self.user, formacao='Lic.', valor_hora=50, modalidade='ONLINE')
        self.assertEqual(self.client.post(reverse('favorito_professor', args=[propria.pk]), {'acao': 'adicionar'}).status_code, 403)

    def test_busca_filtros_e_estados_vazios(self):
        self.assertContains(self.client.get(self.lista), 'Seus próximos professores, por perto')
        Favorito.objects.create(aluno=self.aluno, professor=self.prof)
        for filtros in [{'q': 'Ana'}, {'q': 'Matemática'}, {'q': 'Álgebra'}, {'disciplina': self.disc.pk}]:
            response = self.client.get(self.lista, filtros)
            self.assertEqual(response.context['professores'].paginator.count, 1)
            self.assertContains(response, 'Ana Matemática')
        self.assertContains(self.client.get(self.lista, {'q': 'inexistente'}), 'Nenhum favorito com esses filtros')
        for disciplina in ['²', '9' * 80, '-1']:
            for url in [self.lista, reverse('professores')]:
                self.assertEqual(self.client.get(url, {'disciplina': disciplina}).status_code, 200)

    def test_paginacao_ordenacao_e_sem_duplicatas_por_disciplina(self):
        Favorito.objects.create(aluno=self.aluno, professor=self.prof)
        self.prof.disciplinas.add(Disciplina.objects.create(nome='Matemática aplicada'))
        self.assertEqual(self.client.get(self.lista, {'q': 'Matemática'}).context['professores'].paginator.count, 1)
        for i in range(13):
            user = Usuario.objects.create_user(username=f'prof{i}', email=f'p{i}@test.com', nome=f'Professor {i}')
            prof = Professor.objects.create(usuario=user, formacao='Lic.', valor_hora=50, modalidade='ONLINE')
            Favorito.objects.create(aluno=self.aluno, professor=prof)
        page = self.client.get(self.lista).context['professores']
        self.assertEqual(len(page), 12)
        self.assertEqual(page[0].nome_exibicao, 'Professor 12')
        self.assertEqual(len(self.client.get(self.lista, {'page': 2}).context['professores']), 2)
        self.assertEqual(self.client.get(self.lista, {'page': 'invalida'}).status_code, 200)

    def test_favoritos_nao_multiplicam_estatisticas_de_aulas(self):
        Favorito.objects.create(aluno=self.aluno, professor=self.prof)
        Favorito.objects.create(aluno=self.outro_aluno, professor=self.prof)
        for nota in [2, 4]:
            aula = Aula.objects.create(aluno=self.aluno, professor=self.prof, disciplina=self.disc,
                data_hora=timezone.now(), duracao_min=60, valor=80, modalidade='ONLINE', status='REALIZADA')
            Avaliacao.objects.create(aula=aula, nota=nota)
        prof = self.client.get(self.lista).context['professores'][0]
        self.assertEqual(prof.nota_media, 3)
        self.assertEqual(prof.total_avaliacoes, 2)
        self.assertEqual(prof.aulas_realizadas, 2)

    def test_professor_inativo_some_da_lista(self):
        Favorito.objects.create(aluno=self.aluno, professor=self.prof)
        self.teacher.is_active = False
        self.teacher.save(update_fields=['is_active'])
        self.assertEqual(self.client.get(self.lista).context['total_favoritos'], 0)

    def test_paginas_carregam_tema_e_controle_compartilhados(self):
        for url in ['/', '/professores/', self.lista, '/perfil-aluno/', '/perfil/editar/',
                    '/ambiente-aluno/', '/mensagens/', '/agenda/', f'/professor/{self.prof.pk}/']:
            response = self.client.get(url)
            self.assertContains(response, 'js/tema.js', count=1)
            self.assertContains(response, 'css/tema.css', count=1)
            self.assertContains(response, 'data-theme-toggle', count=1)
        self.client.logout()
        for url in ['/login/', '/cadastro/']:
            response = self.client.get(url)
            self.assertContains(response, 'js/tema.js', count=1)
            self.assertContains(response, 'data-theme-toggle', count=1)

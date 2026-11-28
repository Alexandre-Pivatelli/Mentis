from django.test import Client, TestCase, override_settings
from django.urls import reverse

from .models import Disciplina, Material, Professor, Usuario


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class EditarMaterialTests(TestCase):
    def setUp(self):
        self.usuario = Usuario.objects.create_user(username='prof', email='prof@example.com')
        self.professor = Professor.objects.create(
            usuario=self.usuario, formacao='Letras', valor_hora=50, modalidade='ONLINE',
        )
        self.material = Material.objects.create(
            professor=self.professor, titulo='Original', tipo='PDF',
            url='https://example.com/original', descricao='Descrição anterior',
        )
        self.url = reverse('painel_professor_material_editar', args=[self.material.pk])
        self.client.force_login(self.usuario)

    def test_edita_material_preservando_proprietario_e_publicacao(self):
        self.assertContains(self.client.get(self.url), 'Original')
        painel = self.client.get(reverse('painel_professor'))
        self.assertContains(painel, self.url)
        publicacao = self.material.data_publicacao
        disciplina = Disciplina.objects.create(nome='Português')
        resposta = self.client.post(self.url, {
            'titulo': 'Revisão', 'tipo': 'VIDEO', 'url': 'https://example.com/novo',
            'descricao': 'Novo conteúdo', 'disciplina': disciplina.pk, 'professor': '999',
        })
        self.assertRedirects(resposta, reverse('painel_professor') + '#materiais')
        self.material.refresh_from_db()
        self.assertEqual(self.material.titulo, 'Revisão')
        self.assertEqual(self.material.tipo, 'VIDEO')
        self.assertEqual(self.material.url, 'https://example.com/novo')
        self.assertEqual(self.material.descricao, 'Novo conteúdo')
        self.assertEqual(self.material.disciplina, disciplina)
        self.assertEqual(self.material.professor, self.professor)
        self.assertEqual(self.material.data_publicacao, publicacao)
        self.assertEqual(Material.objects.count(), 1)

    def test_campos_invalidos_preservam_dados_e_mostram_erros(self):
        for dados in [
            {'titulo': '', 'tipo': 'PDF', 'url': 'https://example.com'},
            {'titulo': 'Novo', 'tipo': 'INVALIDO', 'url': 'https://example.com'},
            {'titulo': 'Novo', 'tipo': 'PDF', 'url': 'javascript:alert(1)'},
            {'titulo': 'Novo', 'tipo': 'PDF', 'url': 'https://example.com', 'disciplina': 999},
        ]:
            resposta = self.client.post(self.url, dados)
            self.assertTrue(resposta.context['form'].errors)
            self.material.refresh_from_db()
            self.assertEqual(self.material.titulo, 'Original')

    def test_acesso_exige_dono_e_csrf(self):
        self.assertEqual(Client().get(self.url).status_code, 302)
        outro = Usuario.objects.create_user(username='outro', email='outro@example.com')
        self.client.force_login(outro)
        self.assertEqual(self.client.get(self.url).status_code, 403)
        Professor.objects.create(usuario=outro, formacao='Letras', valor_hora=50, modalidade='ONLINE')
        self.assertEqual(self.client.get(self.url).status_code, 404)
        self.assertEqual(self.client.post(self.url, {'titulo': 'Intruso'}).status_code, 404)
        csrf = Client(enforce_csrf_checks=True)
        csrf.force_login(self.usuario)
        self.assertEqual(csrf.post(self.url, {}).status_code, 403)

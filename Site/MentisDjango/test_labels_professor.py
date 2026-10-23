from django.template.loader import render_to_string
from django.test import TestCase

from .forms import CadastroForm


class LabelsProfessorTests(TestCase):
    def renderizar(self, dados=None):
        form = CadastroForm(dados)
        if dados:
            form.is_valid()
        return render_to_string('includes/campos_professor.html', {'form': form})

    def test_mostra_labels_e_campos_de_professor(self):
        html = self.renderizar()
        self.assertIn('Formação', html)
        self.assertIn('Valor da aula por hora (R$)', html)
        self.assertIn('Modalidade', html)
        for nome in ('formacao', 'valor_hora', 'modalidade'):
            self.assertIn(f'name="{nome}"', html)
        self.assertIn('Online e presencial', html)

    def test_mostra_erro_quando_professor_nao_preenche(self):
        html = self.renderizar({'user_type': 'professor', 'nome': 'Prof', 'username': 'prof',
                                'email': 'p@example.com', 'password1': 'SenhaForte123!',
                                'password2': 'SenhaForte123!'})
        self.assertIn('Preencha este campo para criar seu perfil de professor.', html)

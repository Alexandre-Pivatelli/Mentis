"""Popula o banco com professores fictícios e completos (Sprint 6).

Uso:
    python manage.py popular_professores            # grava
    python manage.py popular_professores --dry-run  # só testa, não grava

Reaproveita as funções seguras do popular_banco: não apaga nem altera
registros existentes e pode ser rodado várias vezes sem duplicar dados.
"""
from datetime import time
from decimal import Decimal

from MentisDjango.models import Disciplina, Disponibilidade, Material, Professor, TipoMaterial

from .popular_banco import Command as CargaBase


# Cada professor: (usuário, nome, disciplinas, formação, valor/hora, modalidade, verificado, bio, horários)
# Horários: (dia_semana, hora_início, hora_fim) — 0 = segunda ... 6 = domingo.
PROFESSORES = [
    ('demo_prof_helena', 'Helena Duarte', ['Química', 'Biologia'],
     'Mestrado em Química pela UFRJ', '90.00', 'HIBRIDA', True,
     'Professora há 9 anos, com foco em vestibular e ENEM. '
     'Explico química orgânica com exemplos do dia a dia e muitos exercícios resolvidos.',
     [(0, 14, 20), (2, 14, 20), (5, 9, 13)]),
    ('demo_prof_gustavo', 'Gustavo Nogueira', ['Matemática', 'Física'],
     'Engenharia Civil pela PUC-Rio', '80.00', 'ONLINE', True,
     'Engenheiro e monitor de cálculo. Ajudo alunos do ensino médio e da faculdade '
     'a perder o medo de funções, derivadas e cinemática.',
     [(1, 18, 22), (3, 18, 22)]),
    ('demo_prof_luiza', 'Luiza Carvalho', ['Português', 'Redação'],
     'Licenciatura em Letras pela UERJ', '70.00', 'ONLINE', True,
     'Corrijo redações no modelo ENEM com devolutiva detalhada. '
     'Também trabalho interpretação de texto e gramática.',
     [(0, 8, 12), (1, 8, 12), (4, 8, 12)]),
    ('demo_prof_rodrigo', 'Rodrigo Teixeira', ['História', 'Geografia'],
     'Licenciatura em História pela UFF', '65.00', 'PRESENCIAL', False,
     'Aulas presenciais na Zona Sul do Rio. Uso mapas, linhas do tempo e debates '
     'para tornar história e geografia mais fáceis de lembrar.',
     [(2, 9, 17), (4, 9, 17)]),
    ('demo_prof_carla', 'Carla Mendes', ['Inglês'],
     'Letras Português-Inglês pela USP, certificado CPE', '85.00', 'ONLINE', True,
     'Conversação e preparação para provas de proficiência. '
     'Aulas 100% em inglês para quem já tem o básico.',
     [(1, 13, 19), (3, 13, 19), (5, 10, 14)]),
    ('demo_prof_felipe', 'Felipe Antunes', ['Física', 'Matemática'],
     'Licenciatura em Física pela UFRJ (cursando mestrado)', '60.00', 'HIBRIDA', False,
     'Comecei a dar aula como monitor da faculdade. '
     'Gosto de explicar física com experimentos simples que dá para fazer em casa.',
     [(0, 19, 22), (2, 19, 22), (6, 10, 16)]),
]


class Command(CargaBase):
    help = 'Acrescenta professores fictícios completos, preservando registros existentes.'

    def populate(self):
        for (usuario, nome, nomes_disc, formacao, valor, modalidade,
             verificado, bio, horarios) in PROFESSORES:
            disciplinas = [self.create(Disciplina, nome=n) for n in nomes_disc]

            professor = self.create(
                Professor,
                usuario=self.user(usuario, nome),
                defaults={'bio': bio, 'formacao': formacao, 'valor_hora': Decimal(valor),
                          'modalidade': modalidade, 'verificado': verificado},
            )
            professor.disciplinas.add(*disciplinas)

            for dia, inicio, fim in horarios:
                self.create(Disponibilidade, professor=professor, dia_semana=dia,
                            hora_inicio=time(inicio), hora_fim=time(fim))

            # Um material de cada tipo para a primeira disciplina do professor.
            principal = disciplinas[0]
            for tipo, rotulo in TipoMaterial.choices:
                self.create(
                    Material,
                    url=f'https://example.com/mentis-demo/{usuario}/{tipo.lower()}',
                    defaults={'professor': professor, 'disciplina': principal, 'tipo': tipo,
                              'titulo': f'DEMO — {principal.nome}: {rotulo}',
                              'descricao': 'Material fictício. A URL é ilustrativa.'},
                )

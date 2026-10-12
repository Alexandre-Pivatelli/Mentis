"""Dados fictícios e repetíveis para desenvolvimento da plataforma Mentis."""
import os
from datetime import datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from MentisDjango.models import (
    Aluno, Aula, Avaliacao, Disciplina, Disponibilidade, Material,
    Pagamento, Professor, Responsavel, StatusAula, TipoMaterial, Usuario,
)


class Command(BaseCommand):
    help = "Acrescenta dados fictícios, preservando registros existentes."

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help='Valida toda a carga e desfaz as gravações no final.')

    def handle(self, *args, **options):
        self.created = {}
        self.password = os.environ.get('MENTIS_DEMO_PASSWORD')
        if self.password and len(self.password) < 12:
            raise CommandError('MENTIS_DEMO_PASSWORD deve ter pelo menos 12 caracteres.')
        with transaction.atomic():
            self.populate()
            if options['dry_run']:
                transaction.set_rollback(True)
        for model, count in sorted(self.created.items()):
            self.stdout.write(f'{model}: {count} novos registros')
        if options['dry_run']:
            self.stdout.write(self.style.WARNING('Simulação concluída: nada foi salvo.'))
        else:
            self.stdout.write(self.style.SUCCESS('Carga concluída sem apagar ou atualizar registros existentes.'))
            self.stdout.write('Contas demo_* não são administradores. Sem MENTIS_DEMO_PASSWORD, não permitem login por senha.')

    def create(self, model, defaults=None, **lookup):
        obj, created = model.objects.get_or_create(defaults=defaults or {}, **lookup)
        if created:
            obj.full_clean()
        self.created[model.__name__] = self.created.get(model.__name__, 0) + int(created)
        return obj

    def user(self, username, nome):
        email = f'{username}@example.com'
        existing = Usuario.objects.filter(username=username).first()
        if existing:
            if existing.email != email or existing.is_staff or existing.is_superuser:
                raise CommandError(f'O nome {username} já pertence a uma conta diferente. Nenhum dado foi salvo.')
            self.created.setdefault('Usuario', 0)
            return existing
        if Usuario.objects.filter(email=email).exists():
            raise CommandError(f'E-mail de demonstração já utilizado: {email}')
        # create_user aplica o hash do Django ou gera senha inutilizável quando None.
        user = Usuario.objects.create_user(
            username=username, email=email, password=self.password,
            nome=nome, first_name=nome.split()[0], last_name=' '.join(nome.split()[1:]),
            telefone='', is_staff=False, is_superuser=False,
        )
        user.full_clean()
        self.created['Usuario'] = self.created.get('Usuario', 0) + 1
        return user

    def populate(self):
        disciplinas = [self.create(Disciplina, nome=n) for n in
                       ['Matemática', 'Português', 'Química', 'Física', 'História', 'Biologia']]
        nomes = ['Marina Alves', 'Pedro Martins', 'Ana Lima', 'Rafael Costa',
                 'Beatriz Santos', 'Lucas Ribeiro', 'Camila Souza', 'Bruno Oliveira']
        professores = []
        for i, nome in enumerate(nomes):
            professor = self.create(Professor,
                usuario=self.user(f'demo_professor_{i + 1:02}', nome),
                defaults={'bio': 'Perfil fictício para demonstração. Aulas com exercícios e acompanhamento.',
                          'formacao': f'Licenciatura em {disciplinas[i % 6].nome}',
                          'valor_hora': Decimal(60 + i * 5), 'modalidade': 'ONLINE', 'verificado': i % 2 == 0})
            # add() só acrescenta vínculos ausentes, sem remover os existentes.
            professor.disciplinas.add(disciplinas[i % 6])
            professores.append(professor)
            for dia in [0, 2, 4]:  # Modelo do projeto: 0 = segunda-feira.
                self.create(Disponibilidade, professor=professor, dia_semana=dia,
                            hora_inicio=time(9), hora_fim=time(18))
            for j, tipo in enumerate(TipoMaterial.values):
                self.create(Material, url=f'https://example.com/mentis-demo/materiais/{i + 1}/{j + 1}',
                    defaults={'professor': professor, 'disciplina': disciplinas[i % 6],
                              'titulo': f'DEMO — {disciplinas[i % 6].nome}: módulo {j + 1}',
                              'descricao': 'Material fictício. A URL é ilustrativa e não contém arquivo para download.',
                              'tipo': tipo})
        alunos = []
        for i in range(16):
            familia = i // 2 + 1
            responsavel = self.create(Responsavel, cpf=f'DEMO-{familia:06}',
                defaults={'nome': f'Responsável fictício {familia:02}',
                          'email': f'demo_responsavel_{familia:02}@example.com', 'telefone': '00000000000'})
            alunos.append(self.create(Aluno, usuario=self.user(f'demo_aluno_{i + 1:02}', f'Aluno Exemplo {i + 1:02}'),
                defaults={'responsavel': responsavel, 'serie': ['9º ano', '1º ano EM', '2º ano EM', '3º ano EM'][i % 4],
                          'escola': 'Escola fictícia Mentis'}))
        # Âncora fixa garante que reexecuções encontrem as mesmas aulas.
        segunda = datetime(2026, 10, 12, 9, tzinfo=ZoneInfo('America/Sao_Paulo'))
        for i, professor in enumerate(professores):
            for j in range(6):
                aluno = alunos[(i * 2 + j % 2) % len(alunos)]
                realizada = j < 3
                data = segunda + timedelta(days=(-7 + 2 * j) if realizada else 2 * (j - 3), hours=i)
                status = StatusAula.REALIZADA if realizada else [StatusAula.AGENDADA, StatusAula.CONFIRMADA, StatusAula.CANCELADA][j - 3]
                aula = self.create(Aula, local_ou_link=f'https://example.com/mentis-demo/aulas/{i + 1:02}-{j + 1:02}',
                    defaults={'aluno': aluno, 'professor': professor, 'disciplina': disciplinas[i % 6],
                              'data_hora': data, 'duracao_min': 60, 'modalidade': 'ONLINE',
                              'valor': professor.valor_hora, 'status': status})
                if realizada or j == 4:
                    self.create(Pagamento, aula=aula,
                        defaults={'responsavel': aluno.responsavel, 'valor': aula.valor,
                                  'metodo': ['PIX', 'CARTAO', 'BOLETO'][j % 3],
                                  'status': 'PAGO' if realizada else 'PENDENTE'})
                if realizada:
                    self.create(Avaliacao, aula=aula,
                        defaults={'nota': (i + j) % 6,
                                  'comentario': 'Avaliação fictícia de uma aula de demonstração.'})

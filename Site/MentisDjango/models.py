from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db.models.functions import Lower
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
from uuid import uuid4
from pathlib import Path


def foto_perfil_path(instance, filename):
    return f'perfis/{uuid4().hex}{Path(filename).suffix.lower()}'


# ---------- Enumerações ----------
class TentativaAutenticacao(models.Model):
    """Contador por endereço e operação; a chave não armazena o IP em claro."""
    chave = models.CharField(max_length=64, unique=True)
    inicio = models.DateTimeField()
    quantidade = models.PositiveIntegerField(default=0)


class StatusAula(models.TextChoices):
    AGENDADA = 'AGENDADA', 'Agendada'
    CONFIRMADA = 'CONFIRMADA', 'Confirmada'
    REALIZADA = 'REALIZADA', 'Realizada'
    CANCELADA = 'CANCELADA', 'Cancelada'


class TipoMaterial(models.TextChoices):
    PDF = 'PDF', 'PDF'
    VIDEO = 'VIDEO', 'Vídeo'
    LINK = 'LINK', 'Link'
    LISTA_EXERCICIOS = 'LISTA_EXERCICIOS', 'Lista de exercícios'


# ---------- Pessoas ----------
class Usuario(AbstractUser):
    # senhaHash -> o campo "password" do AbstractUser (já guarda a senha como hash)
    # dataCadastro -> o campo "date_joined" do AbstractUser
    nome = models.CharField(max_length=150)
    email = models.EmailField(unique=True)
    telefone = models.CharField(max_length=20, blank=True)
    bio = models.TextField('Sobre você', blank=True, max_length=5000)
    foto = models.ImageField('Foto de perfil', upload_to=foto_perfil_path, blank=True)

    class Meta(AbstractUser.Meta):
        abstract = False
        constraints = [models.UniqueConstraint(Lower('email'), name='usuario_email_ci_unique')]

    def __str__(self):
        return self.nome or self.username


class Responsavel(models.Model):
    nome = models.CharField(max_length=150)
    email = models.EmailField()
    telefone = models.CharField(max_length=20)
    cpf = models.CharField(max_length=14, unique=True)

    def __str__(self):
        return self.nome


class Aluno(models.Model):
    class NivelEstudo(models.TextChoices):
        FUNDAMENTAL = 'FUNDAMENTAL', 'Ensino fundamental'
        MEDIO = 'MEDIO', 'Ensino médio'
        GRADUACAO = 'GRADUACAO', 'Graduação'

    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE, primary_key=True)
    responsavel = models.ForeignKey(Responsavel, on_delete=models.PROTECT,
                                    related_name='alunos', null=True, blank=True)
    serie = models.CharField(max_length=50, blank=True)
    escola = models.CharField(max_length=150, blank=True)
    nivel_estudo = models.CharField(max_length=20, choices=NivelEstudo.choices, blank=True)
    novato = models.BooleanField(default=True)

    def __str__(self):
        return str(self.usuario)


class Disciplina(models.Model):
    nome = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.nome


class Professor(models.Model):
    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE, primary_key=True)
    bio = models.TextField(blank=True)
    formacao = models.CharField(max_length=200)
    valor_hora = models.DecimalField(max_digits=8, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    modalidade = models.CharField(max_length=50)
    verificado = models.BooleanField(default=False)
    disciplinas = models.ManyToManyField(Disciplina, related_name='professores')  # leciona * — *

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(valor_hora__gt=0), name='professor_valor_positivo')]

    def __str__(self):
        return str(self.usuario)


class Disponibilidade(models.Model):
    professor = models.ForeignKey(Professor, on_delete=models.CASCADE,
                                  related_name='disponibilidades')  # define 1 — 0..*
    dia_semana = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(6)])  # 0 = segunda ... 6 = domingo
    hora_inicio = models.TimeField()
    hora_fim = models.TimeField()

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(dia_semana__gte=0, dia_semana__lte=6), name='disponibilidade_dia_valido'),
            models.CheckConstraint(condition=models.Q(hora_fim__gt=models.F('hora_inicio')), name='disponibilidade_intervalo_valido'),
        ]


# ---------- Aula, transações e conteúdo ----------
class Aula(models.Model):
    aluno = models.ForeignKey(Aluno, on_delete=models.PROTECT, related_name='aulas')
    professor = models.ForeignKey(Professor, on_delete=models.PROTECT, related_name='aulas')
    disciplina = models.ForeignKey(Disciplina, on_delete=models.PROTECT, related_name='aulas')
    data_hora = models.DateTimeField()
    duracao_min = models.IntegerField(validators=[MinValueValidator(1)])
    modalidade = models.CharField(max_length=50)
    local_ou_link = models.CharField(max_length=255)
    valor = models.DecimalField(max_digits=8, decimal_places=2, validators=[MinValueValidator(0)])
    status = models.CharField(max_length=20, choices=StatusAula.choices,
                              default=StatusAula.AGENDADA)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(duracao_min__gt=0), name='aula_duracao_positiva'),
            models.CheckConstraint(condition=models.Q(valor__gte=0), name='aula_valor_nao_negativo'),
        ]


class Pagamento(models.Model):
    responsavel = models.ForeignKey(Responsavel, on_delete=models.PROTECT,
                                    related_name='pagamentos')      # paga 1 — 0..*
    aula = models.OneToOneField(Aula, on_delete=models.PROTECT, null=True, blank=True,
                                related_name='pagamento')           # gera 1 — 0..1
    valor = models.DecimalField(max_digits=8, decimal_places=2, validators=[MinValueValidator(0)])
    metodo = models.CharField(max_length=50)
    status = models.CharField(max_length=50)
    data = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(valor__gte=0), name='pagamento_valor_nao_negativo')]


class Avaliacao(models.Model):
    aula = models.OneToOneField(Aula, on_delete=models.CASCADE,
                                related_name='avaliacao')           # recebe 1 — 0..1
    nota = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(5)])
    comentario = models.TextField(blank=True)
    data = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(nota__gte=0, nota__lte=5), name='avaliacao_nota_valida')]


class Material(models.Model):
    professor = models.ForeignKey(Professor, on_delete=models.CASCADE,
                                  related_name='materiais')         # disponibiliza 1 — 0..*
    disciplina = models.ForeignKey(Disciplina, on_delete=models.SET_NULL, null=True,
                                   blank=True, related_name='materiais')  # é sobre * — 0..1
    titulo = models.CharField(max_length=200)
    descricao = models.TextField(blank=True)
    tipo = models.CharField(max_length=20, choices=TipoMaterial.choices)
    url = models.URLField()
    data_publicacao = models.DateTimeField(auto_now_add=True)


class Conversa(models.Model):
    aluno = models.ForeignKey(Aluno, on_delete=models.CASCADE, related_name='conversas')
    professor = models.ForeignKey(Professor, on_delete=models.CASCADE, related_name='conversas')
    atualizada_em = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['aluno', 'professor'], name='conversa_participantes_unicos')]
        ordering = ['-atualizada_em', '-pk']


class Mensagem(models.Model):
    conversa = models.ForeignKey(Conversa, on_delete=models.CASCADE, related_name='mensagens')
    autor = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    texto = models.TextField(max_length=3000)
    enviada_em = models.DateTimeField(auto_now_add=True)
    lida_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['enviada_em', 'pk']


class AvaliacaoSite(models.Model):
    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE, related_name='avaliacao_site')
    nota = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comentario = models.TextField(max_length=1500)
    criada_em = models.DateTimeField(auto_now_add=True)
    atualizada_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-criada_em', '-pk']
        verbose_name = 'avaliação do site'
        verbose_name_plural = 'avaliações do site'
        constraints = [models.CheckConstraint(condition=models.Q(nota__gte=1, nota__lte=5), name='avaliacao_site_nota_valida')]

    def __str__(self):
        return f'{self.usuario} — {self.nota}/5'

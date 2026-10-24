from django.db import models

from django.db import models

class Disciplina(models.Model):
    nome = models.CharField(max_length=100)

    def __str__(self):
        return self.nome

class Professor(models.Model):
    nome = models.CharField(max_length=100)
    titulo = models.CharField(max_length=150)
    experiencia = models.CharField(max_length=100)
    biografia = models.TextField()
    preco_aula = models.DecimalField(max_digits=6, decimal_places=2)
    avaliacao = models.FloatField(default=5.0)
    disciplinas = models.ManyToManyField(Disciplina)

    def __str__(self):
        return self.nome

class Material(models.Model):
    TIPO_CHOICES = [
        ('VIDEO', 'Vídeo'),
        ('APRESENTACAO', 'Apresentação'),
        ('FLASHCARD', 'Flashcard'),
        ('RESUMO', 'Resumo'),
    ]

    titulo = models.CharField(max_length=200)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    professor = models.ForeignKey(Professor, on_delete=models.CASCADE)
    disciplina = models.ForeignKey(Disciplina, on_delete=models.CASCADE)
    gratuito = models.BooleanField(default=True)
    preco = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)
    descricao = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.titulo

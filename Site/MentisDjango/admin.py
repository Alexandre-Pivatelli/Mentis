from django.contrib import admin
from . import models

for m in [models.Usuario, models.Responsavel, models.Aluno, models.Professor,
          models.Disciplina, models.Disponibilidade, models.Aula,
          models.Pagamento, models.Avaliacao, models.Material]:
    admin.site.register(m)
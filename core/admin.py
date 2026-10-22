from django.contrib import admin

from .models import Disciplina, Professor, Material

# Registrando os modelos para aparecerem no painel de administração
admin.site.register(Disciplina)
admin.site.register(Professor)
admin.site.register(Material)

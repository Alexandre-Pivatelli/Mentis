from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserChangeForm, AdminUserCreationForm
from . import models


class UsuarioCreationForm(AdminUserCreationForm):
    class Meta(AdminUserCreationForm.Meta):
        model = models.Usuario
        fields = ('username', 'nome', 'email')


class UsuarioChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = models.Usuario
        fields = '__all__'


@admin.register(models.Usuario)
class UsuarioAdmin(UserAdmin):
    add_form = UsuarioCreationForm
    form = UsuarioChangeForm
    fieldsets = UserAdmin.fieldsets + (('Perfil Mentis', {'fields': ('nome', 'telefone', 'bio', 'foto')}),)
    add_fieldsets = UserAdmin.add_fieldsets + (('Perfil Mentis', {'fields': ('nome', 'email')}),)
    list_display = ('username', 'nome', 'email', 'is_staff', 'is_active')
    search_fields = ('username', 'nome', 'email')


for m in [models.Responsavel, models.Aluno, models.Professor,
          models.Disciplina, models.Disponibilidade, models.Aula,
          models.Pagamento, models.Avaliacao, models.Material]:
    admin.site.register(m)

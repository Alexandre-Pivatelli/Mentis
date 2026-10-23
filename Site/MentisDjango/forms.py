from decimal import Decimal

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.db import transaction

from .models import Aluno, Professor, Usuario


class CadastroForm(UserCreationForm):
    user_type = forms.ChoiceField(label='Quero participar como', choices=[
        ('estudante', 'Estudante'), ('professor', 'Professor')], widget=forms.RadioSelect)
    nome = forms.CharField(label='Nome completo', max_length=150,
                           widget=forms.TextInput(attrs={'autocomplete': 'name'}))
    email = forms.EmailField(label='E-mail', max_length=254,
                             widget=forms.EmailInput(attrs={'autocomplete': 'email'}))
    serie = forms.CharField(label='Série ou nível de ensino (opcional)', max_length=50, required=False)
    escola = forms.CharField(label='Escola ou instituição (opcional)', max_length=150, required=False)
    formacao = forms.CharField(label='Formação', max_length=200, required=False)
    valor_hora = forms.DecimalField(label='Valor da aula por hora (R$)', max_digits=8,
        decimal_places=2, min_value=Decimal('0.01'), required=False,
        widget=forms.NumberInput(attrs={'step': '0.01', 'min': '0.01', 'inputmode': 'decimal'}))
    modalidade = forms.ChoiceField(label='Modalidade', required=False, choices=[
        ('', 'Selecione'), ('ONLINE', 'Online'), ('PRESENCIAL', 'Presencial'), ('HIBRIDA', 'Online e presencial')])

    class Meta(UserCreationForm.Meta):
        model = Usuario
        fields = ('user_type', 'nome', 'username', 'email', 'password1', 'password2',
                  'serie', 'escola', 'formacao', 'valor_hora', 'modalidade')
        labels = {'username': 'Nome de usuário'}
        widgets = {'username': forms.TextInput(attrs={'autocomplete': 'username', 'autocapitalize': 'none'})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.pop('autofocus', None)
        self.fields['username'].help_text = 'Use letras, números e os caracteres @ . + - _.'
        self.fields['password1'].label = 'Senha'
        self.fields['password1'].help_text = 'Use pelo menos 8 caracteres. Evite senhas comuns, só números ou parecidas com seus dados.'
        self.fields['password2'].label = 'Confirmar senha'
        self.fields['password2'].help_text = ''
        for name in ('password1', 'password2'):
            self.fields[name].widget.attrs['autocomplete'] = 'new-password'

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if Usuario.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('Este e-mail já está cadastrado. Entre com sua conta.')
        return email

    def clean(self):
        data = super().clean()
        if data.get('user_type') == 'professor':
            for field in ('formacao', 'valor_hora', 'modalidade'):
                if not data.get(field) and field not in self.errors:
                    self.add_error(field, 'Preencha este campo para criar seu perfil de professor.')
        return data

    @transaction.atomic
    def save(self):
        user = super().save()
        if self.cleaned_data['user_type'] == 'professor':
            Professor.objects.create(usuario=user, formacao=self.cleaned_data['formacao'],
                valor_hora=self.cleaned_data['valor_hora'], modalidade=self.cleaned_data['modalidade'])
        else:
            Aluno.objects.create(usuario=user, serie=self.cleaned_data.get('serie', ''),
                                 escola=self.cleaned_data.get('escola', ''))
        return user


class LoginForm(AuthenticationForm):
    error_messages = {
        'invalid_login': 'Usuário ou senha incorretos. Confira os dados e tente novamente.',
        'inactive': 'Usuário ou senha incorretos. Confira os dados e tente novamente.',
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = 'Nome de usuário'
        self.fields['username'].widget.attrs.update({'autocomplete': 'username', 'autocapitalize': 'none'})
        self.fields['password'].label = 'Senha'
        self.fields['password'].widget.attrs['autocomplete'] = 'current-password'


class EditarPerfilForm(forms.ModelForm):
    class Meta:
        model = Usuario
        fields = ('nome', 'username', 'email', 'bio', 'foto')
        labels = {'nome': 'Nome completo', 'username': 'Nome de usuário', 'email': 'E-mail'}
        widgets = {'bio': forms.Textarea(attrs={'rows': 4}),
                   'foto': forms.ClearableFileInput(attrs={'accept': 'image/png,image/jpeg,image/webp'})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.professor = Professor.objects.filter(usuario=self.instance).first() if self.instance.pk else None
        if self.professor:
            self.initial['bio'] = self.professor.bio

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if Usuario.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('Este e-mail já está cadastrado em outra conta.')
        return email

    def clean_foto(self):
        foto = self.cleaned_data.get('foto')
        if foto and hasattr(foto, 'image'):
            if foto.size > 5 * 1024 * 1024:
                raise forms.ValidationError('Escolha uma imagem de até 5 MB.')
            if foto.image.format not in {'JPEG', 'PNG', 'WEBP'}:
                raise forms.ValidationError('Use uma imagem PNG, JPEG ou WebP.')
        return foto

    @transaction.atomic
    def save(self):
        user = super().save()
        if self.professor:
            self.professor.bio = self.cleaned_data['bio']
            self.professor.save(update_fields=['bio'])
        return user

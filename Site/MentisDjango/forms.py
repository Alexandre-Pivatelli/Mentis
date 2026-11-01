from decimal import Decimal

from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm, UserCreationForm
from django.db import transaction

from .models import Aluno, Professor, Usuario, AvaliacaoSite


class FotoPerfilInput(forms.ClearableFileInput):
    template_name = 'includes/foto_input.html'


class FotoPerfilField(forms.ImageField):
    def __init__(self, **kwargs):
        super().__init__(
            label='Foto de perfil (opcional)', required=False,
            help_text='PNG, JPEG ou WebP, até 5 MB.',
            widget=FotoPerfilInput(attrs={'accept': 'image/png,image/jpeg,image/webp'}),
            **kwargs,
        )

    def to_python(self, data):
        if data and data.size > 5 * 1024 * 1024:
            raise forms.ValidationError('Escolha uma imagem de até 5 MB.')
        foto = super().to_python(data)
        if foto and foto.image.format not in {'JPEG', 'PNG', 'WEBP'}:
            raise forms.ValidationError('Use uma imagem PNG, JPEG ou WebP.')
        return foto


class CadastroForm(UserCreationForm):
    foto = FotoPerfilField()
    user_type = forms.ChoiceField(label='Quero participar como', choices=[
        ('estudante', 'Estudante'), ('professor', 'Professor')], widget=forms.RadioSelect)
    nome = forms.CharField(label='Nome completo', max_length=150,
                           widget=forms.TextInput(attrs={'autocomplete': 'name'}))
    email = forms.EmailField(label='E-mail', max_length=254,
                             widget=forms.EmailInput(attrs={'autocomplete': 'email'}))
    nivel_estudo = forms.ChoiceField(label='Nível de estudo', required=False,
        choices=[('', 'Selecione seu nível de estudo'), *Aluno.NivelEstudo.choices])
    serie = forms.ChoiceField(label='Série ou período', required=False, choices=[
        ('', 'Selecione sua série ou período'),
        ('Ensino fundamental', [(f'F{i}', f'{i}º ano') for i in range(1, 10)]),
        ('Ensino médio', [(f'M{i}', f'{i}º ano') for i in range(1, 4)]),
        ('Graduação', [(f'G{i}', f'{i}º período') for i in range(1, 21)]),
    ])
    escola = forms.CharField(label='Escola ou instituição (opcional)', max_length=150, required=False)
    formacao = forms.CharField(label='Formação', max_length=200, required=False)
    valor_hora = forms.DecimalField(label='Valor da aula por hora (R$)', max_digits=8,
        decimal_places=2, min_value=Decimal('0.01'), required=False,
        widget=forms.NumberInput(attrs={'step': '0.01', 'min': '0.01', 'inputmode': 'decimal'}))
    modalidade = forms.ChoiceField(label='Modalidade', required=False, choices=[
        ('', 'Selecione'), ('ONLINE', 'Online'), ('PRESENCIAL', 'Presencial'), ('HIBRIDA', 'Online e presencial')])

    class Meta(UserCreationForm.Meta):
        model = Usuario
        fields = ('user_type', 'nome', 'foto', 'username', 'email', 'password1', 'password2',
                  'nivel_estudo', 'serie', 'escola', 'formacao', 'valor_hora', 'modalidade')
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
        if data.get('user_type') == 'estudante':
            for field in ('nivel_estudo', 'serie'):
                if not data.get(field) and field not in self.errors:
                    self.add_error(field, 'Selecione este campo para criar seu perfil de estudante.')
            nivel, serie = data.get('nivel_estudo'), data.get('serie')
            prefix = {'FUNDAMENTAL': 'F', 'MEDIO': 'M', 'GRADUACAO': 'G'}.get(nivel)
            if prefix and serie:
                if not serie.startswith(prefix):
                    self.add_error('serie', 'Escolha uma série ou período correspondente ao nível de estudo.')
                else:
                    data['serie'] = f"{int(serie[1:])}º {'período' if prefix == 'G' else 'ano'}"
        return data

    @transaction.atomic
    def save(self):
        user = super().save()
        if self.cleaned_data['user_type'] == 'professor':
            Professor.objects.create(usuario=user, formacao=self.cleaned_data['formacao'],
                valor_hora=self.cleaned_data['valor_hora'], modalidade=self.cleaned_data['modalidade'])
        else:
            Aluno.objects.create(usuario=user, nivel_estudo=self.cleaned_data['nivel_estudo'],
                                 serie=self.cleaned_data['serie'], novato=True,
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
    foto = FotoPerfilField()

    class Meta:
        model = Usuario
        fields = ('nome', 'username', 'email', 'bio', 'foto')
        labels = {'nome': 'Nome completo', 'username': 'Nome de usuário', 'email': 'E-mail'}
        widgets = {'bio': forms.Textarea(attrs={'rows': 4})}

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

    @transaction.atomic
    def save(self):
        user = super().save()
        if self.professor:
            self.professor.bio = self.cleaned_data['bio']
            self.professor.save(update_fields=['bio'])
        return user


class RedefinirSenhaForm(PasswordChangeForm):
    error_messages = {
        **PasswordChangeForm.error_messages,
        'password_incorrect': 'Sua senha atual está incorreta. Confira e tente novamente.',
        'password_mismatch': 'As duas senhas não coincidem.',
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['old_password'].label = 'Senha atual'
        self.fields['old_password'].widget.attrs.update({
            'placeholder': 'Digite sua senha atual',
            'autocomplete': 'current-password',
        })
        self.fields['old_password'].widget.attrs.pop('autofocus', None)
        self.fields['new_password1'].label = 'Nova senha'
        self.fields['new_password1'].widget.attrs.update({
            'placeholder': 'Digite sua nova senha',
            'autocomplete': 'new-password',
        })
        self.fields['new_password2'].label = 'Confirmar nova senha'
        self.fields['new_password2'].widget.attrs.update({
            'placeholder': 'Repita sua nova senha',
            'autocomplete': 'new-password',
        })


class AvaliacaoSiteForm(forms.ModelForm):
    nota = forms.TypedChoiceField(label='Sua nota para a Mentis', coerce=int,
        choices=[(i, str(i)) for i in range(1, 6)], widget=forms.RadioSelect,
        help_text='1 = muito ruim · 5 = excelente')
    comentario = forms.CharField(label='Como foi sua experiência?', max_length=1500,
        widget=forms.Textarea(attrs={'rows': 4, 'placeholder': 'Conte o que funcionou bem e o que podemos melhorar…'}),
        help_text='Até 1.500 caracteres. Seu nome e a data ficarão visíveis na página principal.')

    class Meta:
        model = AvaliacaoSite
        fields = ('nota', 'comentario')

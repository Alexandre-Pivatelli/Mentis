from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.db.models import Avg, Count, Q
from django.http import HttpResponseForbidden, JsonResponse
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils import timezone
from django.views.decorators.http import require_POST, require_http_methods, require_GET
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters

from .auth_limits import permitir_tentativa
from .forms import CadastroForm, LoginForm, EditarPerfilForm

from .models import Aluno, Aula, Avaliacao, Disciplina, Professor, StatusAula, Usuario


def professores_queryset():
    return Professor.objects.select_related('usuario').prefetch_related('disciplinas').annotate(
        nota_media=Avg('aulas__avaliacao__nota'),
        total_avaliacoes=Count('aulas__avaliacao', distinct=True),
        aulas_realizadas=Count('aulas', filter=Q(aulas__status=StatusAula.REALIZADA), distinct=True),
        total_materiais=Count('materiais', distinct=True),
    )


def identificar(professor):
    nome = professor.usuario.nome or professor.usuario.get_full_name() or professor.usuario.username
    professor.nome_exibicao = nome
    professor.iniciais = ''.join(parte[0] for parte in nome.split()[:2]).upper()
    return professor


def principal_view(request):
    busca = request.GET.get('q', '').strip()[:200]
    disciplina = request.GET.get('disciplina', '')
    professores = professores_queryset().order_by('usuario__nome', 'pk')
    if busca:
        professores = professores.filter(Q(usuario__nome__icontains=busca)
            | Q(usuario__username__icontains=busca) | Q(disciplinas__nome__icontains=busca)
            | Q(bio__icontains=busca)).distinct()
    if (disciplina.isascii() and disciplina.isdecimal() and len(disciplina) <= 19
            and 0 < int(disciplina) <= 9223372036854775807):
        disciplina = str(int(disciplina))
        professores = professores.filter(disciplinas__pk=int(disciplina))
    else:
        disciplina = ''
    pagina = Paginator(professores, 15).get_page(request.GET.get('page'))
    for professor in pagina:
        identificar(professor)
    return render(request, 'principal.html', {'professores': pagina, 'busca': busca,
        'disciplina_selecionada': disciplina, 'disciplinas': Disciplina.objects.order_by('nome'),
        'total_professores': Professor.objects.count()})


@sensitive_post_parameters('password')
@never_cache
@require_http_methods(['GET', 'POST'])
def login_view(request):
    if request.user.is_authenticated:
        return redirect('principal')
    destino = request.POST.get('next') or request.GET.get('next', '')
    if not url_has_allowed_host_and_scheme(destino, {request.get_host()}, require_https=request.is_secure()):
        destino = reverse('principal')
    form = LoginForm(request, data=request.POST if request.method == 'POST' else None)
    if request.method == 'POST':
        permitido, espera = permitir_tentativa(request, 'login')
        if not permitido:
            form = LoginForm(request, data={})
            form.full_clean()
            form.add_error(None, 'Muitas tentativas. Aguarde 15 minutos antes de tentar novamente.')
            response = render(request, 'login.html', {'form': form, 'next': destino}, status=429)
            response['Retry-After'] = str(espera)
            return response
        if form.is_valid():
            login(request, form.get_user())
            return redirect(destino or reverse('principal'))
    return render(request, 'login.html', {'form': form, 'next': destino})


@require_POST
def logout_view(request):
    logout(request)
    return redirect('principal')


@login_required(login_url='login')
def usuarios_view(request):
    if not request.user.is_staff:
        return HttpResponseForbidden('Acesso restrito à equipe administrativa.')
    busca = request.GET.get('q', '').strip()[:200]
    usuarios = Usuario.objects.select_related('aluno', 'professor').order_by('nome', 'pk')
    if busca:
        usuarios = usuarios.filter(Q(nome__icontains=busca) | Q(email__icontains=busca) | Q(username__icontains=busca))
    pagina = Paginator(usuarios, 10).get_page(request.GET.get('page'))
    for usuario in pagina:
        usuario.nome_exibicao = usuario.nome or usuario.username
        usuario.iniciais = ''.join(p[0] for p in usuario.nome_exibicao.split()[:2]).upper()
        papeis = []
        if hasattr(usuario, 'professor'):
            papeis.append('Professor')
        if hasattr(usuario, 'aluno'):
            papeis.append('Aluno')
        usuario.tipo_exibicao = ' / '.join(papeis) or 'Usuário'
    return render(request, 'usuarios.html', {'usuarios': pagina, 'busca': busca})


@login_required(login_url='login')
def perfil_aluno_view(request):
    aluno = Aluno.objects.select_related('usuario').filter(usuario=request.user).first()
    if aluno is None:
        return render(request, 'perfil_usuario.html', {'aluno': None})
    aulas = Aula.objects.filter(aluno=aluno).select_related('professor__usuario', 'disciplina')
    avaliacoes = Avaliacao.objects.filter(aula__aluno=aluno).select_related('aula__professor__usuario', 'aula__disciplina').order_by('-data', '-pk')
    return render(request, 'perfil_usuario.html', {'aluno': aluno,
        'aulas_realizadas': aulas.filter(status=StatusAula.REALIZADA).count(),
        'avaliacoes': avaliacoes[:10], 'nota_media': avaliacoes.aggregate(media=Avg('nota'))['media'],
        'disciplinas': Disciplina.objects.filter(aulas__aluno=aluno).distinct().order_by('nome'),
        'agenda': aulas.filter(status__in=[StatusAula.AGENDADA, StatusAula.CONFIRMADA], data_hora__gte=timezone.now()).order_by('data_hora', 'pk')[:10]})


def professor_view(request, pk=None):
    if pk is None:
        primeiro = Professor.objects.order_by('pk').first()
        return redirect('professor_detalhe', pk=primeiro.pk) if primeiro else redirect('principal')
    professor = identificar(get_object_or_404(professores_queryset(), pk=pk))
    avaliacoes = Avaliacao.objects.filter(aula__professor=professor).select_related('aula__aluno__usuario', 'aula__disciplina').order_by('-data', '-pk')
    return render(request, 'professor.html', {'professor': professor,
        'materiais': professor.materiais.select_related('disciplina').order_by('-data_publicacao', '-pk')[:12],
        'avaliacoes': avaliacoes[:10], 'disponibilidades': professor.disponibilidades.order_by('dia_semana', 'hora_inicio')})

@sensitive_post_parameters('password1', 'password2')
@never_cache
@require_http_methods(['GET', 'POST'])
def cadastro_view(request):
    if request.user.is_authenticated:
        return redirect('principal')
    tipo = 'professor' if request.GET.get('tipo') == 'professor' else 'estudante'
    form = CadastroForm(request.POST if request.method == 'POST' else None,
                        request.FILES if request.method == 'POST' else None,
                        initial={'user_type': tipo})
    if request.method == 'POST':
        permitido, espera = permitir_tentativa(request, 'cadastro')
        if not permitido:
            form.full_clean()
            form.add_error(None, 'Muitas tentativas de cadastro. Aguarde uma hora antes de tentar novamente.')
            response = render(request, 'cadastro.html', {'form': form}, status=429)
            response['Retry-After'] = str(espera)
            return response
        if form.is_valid():
            try:
                usuario = form.save()
            except IntegrityError:
                form.add_error(None, 'Não foi possível criar a conta com estes dados. Confira o usuário e o e-mail.')
            else:
                login(request, usuario)
                return redirect('principal')
    return render(request, 'cadastro.html', {'form': form})


@never_cache
@login_required(login_url='login')
@require_GET
def sessao_perfil_view(request):
    return JsonResponse({'csrfToken': get_token(request), 'userId': request.user.pk})


@never_cache
@login_required(login_url='login')
@require_http_methods(['GET', 'POST'])
def editar_perfil_view(request):
    perfil_url = (reverse('professor_detalhe', args=[request.user.pk])
                  if hasattr(request.user, 'professor') else reverse('perfil_aluno'))
    form = EditarPerfilForm(request.POST if request.method == 'POST' else None,
                           request.FILES if request.method == 'POST' else None, instance=request.user)
    if request.method == 'POST' and form.is_valid():
        try:
            form.save()
        except IntegrityError:
            form.add_error(None, 'Não foi possível salvar. Confira se o usuário e o e-mail já estão em uso.')
        else:
            return redirect(perfil_url)
    return render(request, 'editar_perfil.html', {'form': form, 'perfil_url': perfil_url})

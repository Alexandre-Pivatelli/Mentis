from datetime import time

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.db.models import Avg, BooleanField, Count, Exists, OuterRef, Q, Value
from django.http import HttpResponseForbidden, JsonResponse
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from .auth_limits import permitir_tentativa
from .forms import AvaliacaoSiteForm, CadastroForm, EditarPerfilForm, LoginForm, RedefinirSenhaForm
from .models import (Aluno, Aula, Avaliacao, AvaliacaoSite, Disciplina,
                     Material, Professor, StatusAula, Usuario)


DIAS = [(0, 'Segunda'), (1, 'Terça'), (2, 'Quarta'), (3, 'Quinta'),
        (4, 'Sexta'), (5, 'Sábado'), (6, 'Domingo')]


def professores_queryset(usuario=None):
    favorito = (Exists(Favorito.objects.filter(aluno_id=usuario.pk, professor_id=OuterRef('pk')))
                if usuario and usuario.is_authenticated and hasattr(usuario, 'aluno')
                else Value(False, output_field=BooleanField()))
    return Professor.objects.select_related('usuario').prefetch_related('disciplinas').annotate(
        favorito=favorito,
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


def _professor_logado(request):
    return Professor.objects.filter(usuario=request.user).first()


@never_cache
def principal_view(request, avaliacao_form=None, status=200):
    busca = request.GET.get('q', '').strip()[:200]
    disciplina = request.GET.get('disciplina', '')
    professores = professores_queryset(request.user).order_by('usuario__nome', 'pk')
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
    avaliacoes_site = AvaliacaoSite.objects.select_related('usuario')
    resumo = avaliacoes_site.aggregate(media=Avg('nota'), total=Count('pk'))
    reviews = Paginator(avaliacoes_site, 6).get_page(request.GET.get('review_page'))
    propria = avaliacoes_site.filter(usuario=request.user).first() if request.user.is_authenticated else None
    if avaliacao_form is None:
        avaliacao_form = AvaliacaoSiteForm(instance=propria)
    return render(request, 'principal.html', {'professores': pagina, 'busca': busca,
        'avaliacoes_site': reviews, 'resumo_site': resumo, 'avaliacao_site_form': avaliacao_form,
        'propria_avaliacao': propria, 'avaliacao_status': status,
        'avaliacao_login_next': reverse('principal') + '#avaliacoes',
        'disciplina_selecionada': disciplina, 'disciplinas': Disciplina.objects.order_by('nome'),
        'total_professores': Professor.objects.count()}, status=status)


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
    avaliacoes = Avaliacao.objects.filter(aula__aluno=aluno).select_related(
        'aula__professor__usuario', 'aula__disciplina').order_by('-data', '-pk')
    return render(request, 'perfil_usuario.html', {'aluno': aluno,
        'aulas_realizadas': aulas.filter(status=StatusAula.REALIZADA).count(),
        'avaliacoes': avaliacoes[:10], 'nota_media': avaliacoes.aggregate(media=Avg('nota'))['media'],
        'disciplinas': Disciplina.objects.filter(aulas__aluno=aluno).distinct().order_by('nome'),
        'agenda': aulas.filter(status__in=[StatusAula.AGENDADA, StatusAula.CONFIRMADA],
                               data_hora__gte=timezone.now()).order_by('data_hora', 'pk')[:10]})


@never_cache
def professor_view(request, pk=None):
    if pk is None:
        primeiro = Professor.objects.order_by('pk').first()
        return redirect('professor_detalhe', pk=primeiro.pk) if primeiro else redirect('principal')
    professor = identificar(get_object_or_404(professores_queryset(request.user), pk=pk))
    avaliacoes = Avaliacao.objects.filter(aula__professor=professor).select_related(
        'aula__aluno__usuario', 'aula__disciplina').order_by('-data', '-pk')
    eh_dono = request.user.is_authenticated and request.user.pk == professor.usuario_id
    return render(request, 'professor.html', {
        'professor': professor,
        'eh_dono': eh_dono,
        'materiais': professor.materiais.select_related('disciplina').order_by('-data_publicacao')[:12],
        'avaliacoes': avaliacoes[:10],
        'disponibilidades': professor.disponibilidades.order_by('dia_semana', 'hora_inicio'),
    })


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
    if hasattr(request.user, 'professor'):
        perfil_url = reverse('professor_detalhe', args=[request.user.professor.pk])
    else:
        perfil_url = reverse('perfil_aluno')
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


@sensitive_post_parameters('old_password', 'new_password1', 'new_password2')
@never_cache
@login_required(login_url='login')
@require_http_methods(['GET', 'POST'])
def redefinir_senha_view(request):
    perfil_url = (reverse('professor_detalhe', args=[request.user.pk])
                  if hasattr(request.user, 'professor') else reverse('perfil_aluno'))
    form = RedefinirSenhaForm(user=request.user, data=request.POST if request.method == 'POST' else None)
    if request.method == 'POST' and form.is_valid():
        usuario = form.save()
        update_session_auth_hash(request, usuario)
        messages.success(request, 'Sua senha foi redefinida com sucesso.')
        return redirect(perfil_url)
    return render(request, 'redefinir_senha.html', {'form': form, 'perfil_url': perfil_url})


@never_cache
def professores_view(request):
    busca = request.GET.get('q', '').strip()[:200]
    disciplina_id = request.GET.get('disciplina', '')
    tipo_material = request.GET.get('tipo', '')

    professores = professores_queryset(request.user).order_by('usuario__nome', 'pk')

    # 1. Busca geral (nome, username, disciplina, biografia)
    if busca:
        professores = professores.filter(
            Q(usuario__nome__icontains=busca) |
            Q(usuario__username__icontains=busca) |
            Q(disciplinas__nome__icontains=busca) |
            Q(bio__icontains=busca)
        ).distinct()

    # 2. Filtro por disciplina
    if (disciplina_id.isascii() and disciplina_id.isdecimal() and len(disciplina_id) <= 19
            and 0 < int(disciplina_id) <= 9223372036854775807):
        disciplina_id = str(int(disciplina_id))
        professores = professores.filter(disciplinas__pk=int(disciplina_id))
    else:
        disciplina_id = ''

    # 3. Filtro por tipo de material oferecido pelo professor
    if tipo_material:
        professores = professores.filter(materiais__tipo__icontains=tipo_material).distinct()

    pagina = Paginator(professores, 8).get_page(request.GET.get('page'))
    for professor in pagina:
        identificar(professor)

    return render(request, 'professores.html', {
        'professores': pagina,
        'busca': busca,
        'disciplina_selecionada': disciplina_id,
        'tipo_selecionado': tipo_material,
        'disciplinas': Disciplina.objects.order_by('nome'),
    })


@never_cache
@login_required(login_url='login')
@require_POST
def avaliar_site_view(request):
    propria = AvaliacaoSite.objects.filter(usuario=request.user).first()
    form = AvaliacaoSiteForm(request.POST, instance=propria)
    if not form.is_valid():
        return principal_view(request, avaliacao_form=form, status=400)
    AvaliacaoSite.objects.update_or_create(usuario=request.user, defaults={
        'nota': form.cleaned_data['nota'], 'comentario': form.cleaned_data['comentario']})
    return redirect(reverse('principal') + '?avaliacao=salva#avaliacoes')


def sobre_view(request):
    return render(request, 'sobre.html')


def materiais_view(request):
    aluno = None
    materiais = []
    if request.user.is_authenticated:
        aluno = Aluno.objects.filter(usuario=request.user).first()
        if aluno:
            materiais = (Material.objects.filter(professor__aulas__aluno=aluno)
                         .select_related('professor__usuario', 'disciplina')
                         .distinct()
                         .order_by('professor__usuario__nome', '-data_publicacao'))
    return render(request, 'materiais.html', {'materiais': materiais, 'aluno': aluno})


# ===== PAINEL DO PROFESSOR =====

@login_required(login_url='login')
def painel_professor_view(request):
    professor = _professor_logado(request)
    if professor is None:
        messages.error(request, 'Esta área é só para professores.')
        return redirect('principal')

    disponibilidades = {d.dia_semana: d for d in professor.disponibilidades.all()}
    dias = []
    for codigo, nome in DIAS:
        d = disponibilidades.get(codigo)
        dias.append({
            'codigo': codigo,
            'nome': nome,
            'ativo': d is not None,
            'inicio': d.hora_inicio if d else time(8, 0),
            'fim': d.hora_fim if d else time(18, 0),
        })

    return render(request, 'painel_professor.html', {
        'professor': professor,
        'dias': dias,
        'disciplinas': professor.disciplinas.all(),
        'materiais': professor.materiais.select_related('disciplina').order_by('-data_publicacao'),
    })


@login_required(login_url='login')
@require_POST
def painel_professor_agenda(request):
    professor = _professor_logado(request)
    if professor is None:
        messages.error(request, 'Esta área é só para professores.')
        return redirect('principal')

    horarios = []
    for codigo, nome in DIAS:
        if not request.POST.get(f'ativo_{codigo}'):
            continue
        try:
            inicio = time.fromisoformat(request.POST.get(f'inicio_{codigo}', ''))
            fim = time.fromisoformat(request.POST.get(f'fim_{codigo}', ''))
        except ValueError:
            messages.error(request, f'Horário inválido em {nome}.')
            return redirect(reverse('painel_professor') + '#agenda')
        if inicio >= fim:
            messages.error(request, f'Em {nome}, o término deve ser depois do início.')
            return redirect(reverse('painel_professor') + '#agenda')
        horarios.append((codigo, inicio, fim))

    professor.disponibilidades.all().delete()
    for codigo, inicio, fim in horarios:
        professor.disponibilidades.create(dia_semana=codigo, hora_inicio=inicio, hora_fim=fim)

    messages.success(request, 'Agenda atualizada.')
    return redirect(reverse('painel_professor') + '#agenda')


@login_required(login_url='login')
@require_POST
def painel_professor_material_criar(request):
    professor = _professor_logado(request)
    if professor is None:
        messages.error(request, 'Esta área é só para professores.')
        return redirect('principal')

    titulo = request.POST.get('titulo', '').strip()
    url = request.POST.get('link', '').strip()
    disciplina = Disciplina.objects.filter(pk=request.POST.get('disciplina') or None).first()

    if disciplina is None:
        messages.error(request, 'Selecione uma disciplina.')
        return redirect(reverse('painel_professor') + '#materiais')
    if not titulo:
        messages.error(request, 'Informe um título para o material.')
        return redirect(reverse('painel_professor') + '#materiais')
    if not url:
        messages.error(request, 'Informe o link do material.')
        return redirect(reverse('painel_professor') + '#materiais')

    Material.objects.create(
        professor=professor,
        disciplina=disciplina,
        titulo=titulo,
        tipo=request.POST.get('tipo', ''),
        descricao=request.POST.get('descricao', '').strip(),
        url=url,
        data_publicacao=timezone.now(),
    )
    messages.success(request, 'Material publicado.')
    return redirect(reverse('painel_professor') + '#materiais')


@login_required(login_url='login')
@require_POST
def painel_professor_material_excluir(request, pk):
    professor = _professor_logado(request)
    if professor is None:
        messages.error(request, 'Esta área é só para professores.')
        return redirect('principal')
    get_object_or_404(Material, pk=pk, professor=professor).delete()
    messages.success(request, 'Material excluído.')
    return redirect(reverse('painel_professor') + '#materiais')
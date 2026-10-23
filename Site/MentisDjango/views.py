from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.core.paginator import Paginator
from django.db.models import Avg, Count, Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

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
    if disciplina.isdigit():
        professores = professores.filter(disciplinas__pk=int(disciplina))
    pagina = Paginator(professores, 8).get_page(request.GET.get('page'))
    for professor in pagina:
        identificar(professor)
    return render(request, 'principal.html', {'professores': pagina, 'busca': busca,
        'disciplina_selecionada': disciplina, 'disciplinas': Disciplina.objects.order_by('nome'),
        'total_professores': Professor.objects.count()})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('principal')
    form = AuthenticationForm(request, data=request.POST if request.method == 'POST' else None)
    if request.method == 'POST' and form.is_valid():
        login(request, form.get_user())
        destino = request.POST.get('next') or request.GET.get('next', '')
        if not url_has_allowed_host_and_scheme(destino, {request.get_host()}, require_https=request.is_secure()):
            destino = reverse('principal')
        return redirect(destino or reverse('principal'))
    return render(request, 'login.html', {'form': form, 'next': request.GET.get('next', '')})


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
        'agenda': aulas.filter(status__in=[StatusAula.AGENDADA, StatusAula.CONFIRMADA]).order_by('data_hora')[:10]})


def professor_view(request, pk=None):
    if pk is None:
        primeiro = Professor.objects.order_by('pk').first()
        return redirect('professor_detalhe', pk=primeiro.pk) if primeiro else redirect('principal')
    professor = identificar(get_object_or_404(professores_queryset(), pk=pk))
    avaliacoes = Avaliacao.objects.filter(aula__professor=professor).select_related('aula__aluno__usuario', 'aula__disciplina').order_by('-data', '-pk')
    return render(request, 'professor.html', {'professor': professor,
        'materiais': professor.materiais.select_related('disciplina').order_by('-data_publicacao', '-pk')[:12],
        'avaliacoes': avaliacoes[:10], 'disponibilidades': professor.disponibilidades.order_by('dia_semana', 'hora_inicio')})


def cadastro_view(request):
    if request.user.is_authenticated:
        return redirect('principal')

    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        tipo_usuario = request.POST.get('user_type', 'estudante')

        if form.is_valid():
            usuario = form.save()
            
            nome_completo = request.POST.get('nome', '')
            if nome_completo:
                usuario.nome = nome_completo
                usuario.email = request.POST.get('email', '')
                usuario.save()

            if tipo_usuario == 'professor':
                Professor.objects.create(usuario=usuario)
            else:
                Aluno.objects.create(usuario=usuario)

            login(request, usuario)
            return redirect('principal')
    else:
        form = UserCreationForm()

    return render(request, 'cadastro.html', {'form': form})


@login_required(login_url='login')
def editar_perfil_view(request):
    if request.method == 'POST':
        request.user.nome = request.POST.get('nome')
        request.user.username = request.POST.get('username')
        request.user.email = request.POST.get('email')
        request.user.save()
        return redirect('perfil_aluno')

    return render(request, 'editar_perfil.html')


def professores_view(request):
    busca = request.GET.get('q', '').strip()[:200]
    disciplina_id = request.GET.get('disciplina', '')
    tipo_material = request.GET.get('tipo', '')
    
    # Pega o queryset base de professores
    professores = professores_queryset().order_by('usuario__nome', 'pk')
    
    # 1. Filtro de busca geral (nome, username, disciplina, biografia)
    if busca:
        professores = professores.filter(
            Q(usuario__nome__icontains=busca) |
            Q(usuario__username__icontains=busca) |
            Q(disciplinas__nome__icontains=busca) |
            Q(bio__icontains=busca)
        ).distinct()
        
    # 2. Filtro por Matéria (Disciplina) específica
    if disciplina_id.isdigit():
        professores = professores.filter(disciplinas__pk=int(disciplina_id))
        
    # 3. Filtro por Tipo de Material oferecido pelo professor
    # (Certifica-te de que o teu modelo Material possui um campo correspondente, ex: 'tipo')
    if tipo_material:
        professores = professores.filter(materiais__tipo__icontains=tipo_material).distinct()

    # Paginação (8 professores por página)
    pagina = Paginator(professores, 8).get_page(request.GET.get('page'))
    for professor in pagina:
        identificar(professor)
        
    return render(request, 'professores.html', {
        'professores': pagina,
        'busca': busca,
        'disciplina_selecionada': disciplina_id,
        'tipo_selecionado': tipo_material,
        'disciplinas': Disciplina.objects.order_by('nome'), # Passa as disciplinas para o select do HTML
    })
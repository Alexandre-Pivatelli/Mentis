from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponseBadRequest, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_POST

from .models import Aluno, Disciplina, Favorito, Professor
from .views import identificar, professores_queryset


@never_cache
@login_required(login_url='login')
@require_GET
def favoritos_view(request):
    aluno = Aluno.objects.filter(usuario=request.user).first()
    if aluno is None:
        return HttpResponseForbidden('Os favoritos estão disponíveis para contas de aluno.')
    busca = request.GET.get('q', '').strip()[:200]
    disciplina = request.GET.get('disciplina', '')
    professores = professores_queryset(request.user).filter(
        favoritos__aluno=aluno, usuario__is_active=True)
    total = professores.count()
    if busca:
        professores = professores.filter(
            Q(usuario__nome__icontains=busca) | Q(usuario__username__icontains=busca)
            | Q(disciplinas__nome__icontains=busca) | Q(bio__icontains=busca)).distinct()
    if (disciplina.isascii() and disciplina.isdecimal() and len(disciplina) <= 19
            and 0 < int(disciplina) <= 9223372036854775807):
        disciplina = str(int(disciplina))
        professores = professores.filter(disciplinas__pk=int(disciplina))
    else:
        disciplina = ''
    pagina = Paginator(professores.order_by('-favoritos__criado_em', '-pk'), 12).get_page(request.GET.get('page'))
    for professor in pagina:
        identificar(professor)
    return render(request, 'favoritos.html', {
        'professores': pagina, 'busca': busca, 'total_favoritos': total, 'somente_favoritos': True,
        'disciplina_selecionada': disciplina,
        'disciplinas': Disciplina.objects.filter(
            professores__favoritos__aluno=aluno, professores__usuario__is_active=True).distinct().order_by('nome'),
    })


@never_cache
@login_required(login_url='login')
@require_POST
def favorito_professor_view(request, pk):
    aluno = Aluno.objects.filter(usuario=request.user).first()
    if aluno is None:
        return HttpResponseForbidden('Apenas alunos podem favoritar professores.')
    professor = get_object_or_404(Professor, pk=pk, usuario__is_active=True)
    if professor.usuario_id == request.user.pk:
        return HttpResponseForbidden('Escolha outro professor para favoritar.')
    acao = request.POST.get('acao')
    if acao not in {'adicionar', 'remover'}:
        return HttpResponseBadRequest('Escolha adicionar ou remover dos favoritos.')
    if acao == 'adicionar':
        Favorito.objects.get_or_create(aluno=aluno, professor=professor)
    else:
        Favorito.objects.filter(aluno=aluno, professor=professor).delete()
    nome = professor.usuario.nome or professor.usuario.username
    mensagem = f'{nome} foi adicionado aos favoritos.' if acao == 'adicionar' else f'{nome} foi removido dos favoritos.'
    if request.headers.get('Accept') == 'application/json':
        return JsonResponse({'favorito': acao == 'adicionar', 'mensagem': mensagem})
    messages.success(request, mensagem)
    destino = request.POST.get('next', '')
    if not url_has_allowed_host_and_scheme(destino, {request.get_host()}, require_https=request.is_secure()):
        destino = reverse('favoritos_aluno')
    return redirect(destino or reverse('favoritos_aluno'))

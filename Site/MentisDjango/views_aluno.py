"""Views do ambiente do aluno (Sprint 6) e avaliação de aulas (Sprint 8).

Fica num arquivo separado para não alterar o views.py do grupo.
Busca os mesmos dados que a página de perfil do aluno já usa.
"""
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Avg
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import Aluno, Aula, Avaliacao, Disciplina, StatusAula


def aula_ja_aconteceu(aula):
    '''A aula termina em data_hora + duração; só depois disso dá para avaliar.'''
    return aula.data_hora + timedelta(minutes=aula.duracao_min) <= timezone.now()


def aulas_para_avaliar(aluno):
    '''Aulas do aluno que já terminaram, não foram canceladas e ainda não têm avaliação.'''
    aulas = (Aula.objects.filter(aluno=aluno, avaliacao__isnull=True, data_hora__lte=timezone.now())
             .exclude(status=StatusAula.CANCELADA)
             .select_related('professor__usuario', 'disciplina')
             .order_by('-data_hora', '-pk'))
    return [aula for aula in aulas if aula_ja_aconteceu(aula)]


@login_required(login_url='login')
def ambiente_aluno_view(request):
    aluno = Aluno.objects.select_related('usuario').filter(usuario=request.user).first()
    if aluno is None:
        return render(request, 'ambiente_aluno.html', {'aluno': None})

    aulas = Aula.objects.filter(aluno=aluno).select_related('professor__usuario', 'disciplina')
    avaliacoes = (Avaliacao.objects.filter(aula__aluno=aluno)
                  .select_related('aula__professor__usuario', 'aula__disciplina')
                  .order_by('-data', '-pk'))

    agenda = aulas.filter(status__in=[StatusAula.AGENDADA, StatusAula.CONFIRMADA],
                          data_hora__gte=timezone.now()).order_by('data_hora', 'pk')
    return render(request, 'ambiente_aluno.html', {
        'aluno': aluno,
        'aulas_realizadas': aulas.filter(status=StatusAula.REALIZADA).count(),
        'avaliacoes': avaliacoes[:10],
        'nota_media': avaliacoes.aggregate(media=Avg('nota'))['media'],
        'disciplinas': Disciplina.objects.filter(aulas__aluno=aluno).distinct().order_by('nome'),
        'agenda': agenda[:10], 'total_proximas_aulas': agenda.count(),
        'para_avaliar': aulas_para_avaliar(aluno)[:10],
        'notas': [5, 4, 3, 2, 1],
    })


@login_required(login_url='login')
@require_POST
def avaliar_aula_view(request, pk):
    '''O aluno dá uma nota de 1 a 5 (e um comentário opcional) para uma aula que já aconteceu.'''
    destino = reverse('ambiente_aluno') + '#avaliar'
    aluno = Aluno.objects.filter(usuario=request.user).first()
    if aluno is None:
        messages.error(request, 'Só estudantes podem avaliar aulas.')
        return redirect('principal')

    # Só encontra aulas do próprio aluno; aula de outra pessoa dá 404.
    aula = get_object_or_404(Aula, pk=pk, aluno=aluno)

    if aula.status == StatusAula.CANCELADA:
        messages.error(request, 'Aulas canceladas não podem ser avaliadas.')
        return redirect(destino)
    if not aula_ja_aconteceu(aula):
        messages.error(request, 'Você só pode avaliar a aula depois que ela acontecer.')
        return redirect(destino)
    if Avaliacao.objects.filter(aula=aula).exists():
        messages.error(request, 'Você já avaliou esta aula.')
        return redirect(destino)

    try:
        nota = int(request.POST.get('nota', ''))
    except ValueError:
        nota = 0
    if nota < 1 or nota > 5:
        messages.error(request, 'Escolha uma nota de 1 a 5.')
        return redirect(destino)
    comentario = request.POST.get('comentario', '').strip()[:1000]

    Avaliacao.objects.create(aula=aula, nota=nota, comentario=comentario)
    # Se a aula foi avaliada é porque aconteceu: passa a contar como realizada.
    if aula.status in (StatusAula.AGENDADA, StatusAula.CONFIRMADA):
        aula.status = StatusAula.REALIZADA
        aula.save(update_fields=['status'])

    messages.success(request, 'Obrigado! Sua avaliação foi registrada.')
    return redirect(reverse('ambiente_aluno') + '#avaliacoes')

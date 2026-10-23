"""View do ambiente do aluno (Sprint 6).

Fica num arquivo separado para não alterar o views.py do grupo.
Busca os mesmos dados que a página de perfil do aluno já usa.
"""
from django.contrib.auth.decorators import login_required
from django.db.models import Avg
from django.shortcuts import render
from django.utils import timezone

from .models import Aluno, Aula, Avaliacao, Disciplina, StatusAula


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
    })

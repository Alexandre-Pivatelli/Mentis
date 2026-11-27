from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import Aula, Professor, StatusAula


@login_required(login_url='login')
def aulas_professor(request):
    '''
    Mostra ao professor os pedidos de aula e as aulas já confirmadas.
    '''
    professor = Professor.objects.filter(usuario=request.user).first()
    if professor is None:
        messages.error(request, 'Esta área é só para professores.')
        return redirect('principal')

    agora = timezone.now()
    aulas = Aula.objects.filter(professor=professor, data_hora__gte=agora).order_by('data_hora')    # gte = maior ou igual

    pedidos = aulas.filter(status=StatusAula.AGENDADA)
    confirmadas = aulas.filter(status=StatusAula.CONFIRMADA)

    contexto = {
        'professor': professor,
        'pedidos': pedidos,
        'confirmadas': confirmadas,
    }
    return render(request, 'aulas_professor.html', contexto)


@login_required(login_url='login')
@require_POST
def responder_aula(request, aula_id):
    '''
    Confirma ou recusa (cancela) um pedido de aula, conforme o botão clicado.
    '''
    professor = Professor.objects.filter(usuario=request.user).first()
    if professor is None:
        messages.error(request, 'Esta área é só para professores.')
        return redirect('principal')

    aula = get_object_or_404(Aula, pk=aula_id, professor=professor)    # só aulas deste professor

    if aula.status != StatusAula.AGENDADA:
        messages.error(request, 'Esta aula já foi respondida.')
        return redirect('aulas_professor')

    acao = request.POST.get('acao')
    if acao == 'confirmar':
        aula.status = StatusAula.CONFIRMADA
        aula.save()
        messages.success(request, 'Aula confirmada.')
    elif acao == 'recusar':
        aula.status = StatusAula.CANCELADA
        aula.save()
        messages.success(request, 'Aula recusada.')
    else:
        messages.error(request, 'Escolha confirmar ou recusar.')

    return redirect('aulas_professor')

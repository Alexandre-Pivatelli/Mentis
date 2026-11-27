from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import Aluno, Aula, StatusAula


@login_required(login_url='login')
@require_POST
def cancelar_aula(request, aula_id):
    '''
    Cancela uma aula do aluno que ainda não aconteceu.
    '''
    aluno = get_object_or_404(Aluno, usuario=request.user)
    aula = get_object_or_404(Aula, pk=aula_id, aluno=aluno)    # só aulas deste aluno

    ainda_vai_acontecer = aula.data_hora > timezone.now()
    if aula.status in [StatusAula.AGENDADA, StatusAula.CONFIRMADA] and ainda_vai_acontecer:
        aula.status = StatusAula.CANCELADA
        aula.save()

    # Volta para a agenda, no dia da aula
    dia = timezone.localtime(aula.data_hora).date()
    return redirect(reverse('agenda_aluno') + '?mes=' + dia.replace(day=1).isoformat() + '&dia=' + dia.isoformat())

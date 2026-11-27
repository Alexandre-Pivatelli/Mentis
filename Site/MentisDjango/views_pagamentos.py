"""Histórico de pagamento do aluno e cancelamento de assinatura (Sprint 10).

Fica num arquivo separado para não alterar o views.py do grupo.
"""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .models import Aluno, Assinatura, Pagamento, Professor

# Os status de Pagamento são texto livre no banco; estes são os que o site usa.
STATUS_PAGO = 'PAGO'
STATUS_PENDENTE = 'PENDENTE'
FILTROS = {'pago': STATUS_PAGO, 'pendente': STATUS_PENDENTE}


def _aluno_logado(request):
    return Aluno.objects.filter(usuario=request.user).first()


@login_required(login_url='login')
def historico_pagamentos_view(request):
    '''Lista os pagamentos das aulas do aluno, com totais pagos e pendentes, e as assinaturas dele.'''
    aluno = _aluno_logado(request)
    if aluno is None:
        if Professor.objects.filter(usuario=request.user).exists():
            return redirect(reverse('painel_professor') + '#resumo')
        messages.error(request, 'O histórico de pagamentos é só para estudantes.')
        return redirect('principal')

    todos = (Pagamento.objects.filter(aula__aluno=aluno)
             .select_related('aula__professor__usuario', 'aula__disciplina')
             .order_by('-data', '-pk'))

    filtro = request.GET.get('status', '').lower()
    pagamentos = todos.filter(status=FILTROS[filtro]) if filtro in FILTROS else todos
    if filtro not in FILTROS:
        filtro = ''

    def soma(status):
        return todos.filter(status=status).aggregate(total=Sum('valor'))['total'] or 0

    assinaturas = (Assinatura.objects.filter(aluno=aluno)
                   .exclude(status=Assinatura.Status.CANCELADA)
                   .select_related('professor__usuario')
                   .order_by('-atualizado_em'))

    return render(request, 'pagamentos.html', {
        'aluno': aluno,
        'pagamentos': pagamentos,
        'filtro': filtro,
        'total_pago': soma(STATUS_PAGO),
        'total_pendente': soma(STATUS_PENDENTE),
        'quantidade': todos.count(),
        'assinaturas': assinaturas,
    })


@login_required(login_url='login')
@require_POST
def cancelar_assinatura_view(request, pk):
    '''O aluno cancela a própria assinatura (ativa ou aguardando pagamento) de um professor.'''
    destino = reverse('assinatura_professor', args=[pk])
    aluno = _aluno_logado(request)
    if aluno is None:
        messages.error(request, 'Só estudantes podem cancelar assinaturas.')
        return redirect(destino)

    professor = get_object_or_404(Professor, pk=pk)
    assinatura = (Assinatura.objects.filter(aluno=aluno, professor=professor)
                  .exclude(status=Assinatura.Status.CANCELADA).first())
    if assinatura is None:
        messages.error(request, 'Você não tem uma assinatura com este professor.')
        return redirect(destino)

    estava_ativa = assinatura.status == Assinatura.Status.ATIVA
    assinatura.status = Assinatura.Status.CANCELADA
    assinatura.save(update_fields=['status', 'atualizado_em'])
    if estava_ativa:
        messages.success(request, 'Assinatura cancelada. Você não terá mais acesso aos materiais deste professor.')
    else:
        messages.success(request, 'Pedido de assinatura cancelado.')
    return redirect(destino)

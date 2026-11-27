"""Números do painel de informações do professor (ganhos e horas) — Sprint 10.

O painel do professor só chama resumo_professor(); quem pegar o card de
URLS + VIEWS do painel de informações pode reaproveitar esta função numa página própria.
"""
from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, Sum
from django.utils import timezone

from .models import Assinatura, StatusAula


def _somar(aulas):
    dados = aulas.aggregate(ganhos=Sum('valor'), minutos=Sum('duracao_min'), quantidade=Count('pk'))
    return {
        'ganhos': dados['ganhos'] or Decimal('0'),
        'horas': (dados['minutos'] or 0) / 60,
        'aulas': dados['quantidade'],
    }


def resumo_professor(professor, agora=None):
    '''
    Ganhos e horas do professor.
    - "Ganhos" somam o valor das aulas marcadas como realizadas.
    - "Mês" é o mês do calendário atual (fuso do site).
    - "Próximas" são aulas agendadas ou confirmadas que ainda vão acontecer.
    '''
    agora = agora or timezone.now()
    local = timezone.localtime(agora)
    inicio_mes = local.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    inicio_mes_passado = (inicio_mes - timedelta(days=1)).replace(day=1)

    realizadas = professor.aulas.filter(status=StatusAula.REALIZADA)
    mes = _somar(realizadas.filter(data_hora__gte=inicio_mes, data_hora__lte=agora))
    mes_passado = _somar(realizadas.filter(data_hora__gte=inicio_mes_passado, data_hora__lt=inicio_mes))
    total = _somar(realizadas)
    proximas = _somar(professor.aulas.filter(
        status__in=[StatusAula.AGENDADA, StatusAula.CONFIRMADA], data_hora__gt=agora))

    assinantes = professor.assinaturas.filter(status=Assinatura.Status.ATIVA).count()
    receita_assinaturas = (professor.valor_assinatura or Decimal('0')) * assinantes

    return {
        'nome_mes': local.strftime('%m/%Y'),
        'mes': mes,
        'mes_passado': mes_passado,
        'total': total,
        'proximas': proximas,
        'assinantes': assinantes,
        'receita_assinaturas': receita_assinaturas,
        'tem_preco_assinatura': bool(professor.valor_assinatura),
    }

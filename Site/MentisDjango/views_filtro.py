from datetime import time
from decimal import Decimal, InvalidOperation

from django.db.models import Q
from django.shortcuts import render

from .models import Disciplina, Disponibilidade
from .views import identificar, professores_queryset

# 0 = segunda ... 6 = domingo, como no banco.
DIAS_DA_SEMANA = [('0', 'Segunda-feira'), ('1', 'Terça-feira'), ('2', 'Quarta-feira'),
                  ('3', 'Quinta-feira'), ('4', 'Sexta-feira'), ('5', 'Sábado'), ('6', 'Domingo')]

# Começo e fim de cada período do dia.
PERIODOS = {
    'manha': (time(6, 0), time(12, 0)),
    'tarde': (time(12, 0), time(18, 0)),
    'noite': (time(18, 0), time(23, 59)),
}


def texto_para_preco(texto):
    '''
    Converte o preço digitado em número. Devolve None se não for válido.
    '''
    try:
        preco = Decimal(texto.replace(',', '.'))
    except InvalidOperation:
        return None
    if not preco.is_finite():    # recusa "NaN" e "Infinity"
        return None
    return preco


def filtro_professores(request):
    '''
    Lista os professores aplicando os filtros escolhidos no formulário.
    '''
    busca = request.GET.get('q', '').strip()
    disciplina = request.GET.get('disciplina', '')
    modalidade = request.GET.get('modalidade', '')
    preco_min = request.GET.get('preco_min', '')
    preco_max = request.GET.get('preco_max', '')
    dia = request.GET.get('dia', '')
    periodo = request.GET.get('periodo', '')
    nota_min = request.GET.get('nota_min', '')
    so_verificados = request.GET.get('verificado') == '1'
    ordem = request.GET.get('ordem', 'nome')

    professores = professores_queryset(request.user)

    # Nome ou disciplina
    if busca:
        professores = professores.filter(
            Q(usuario__nome__icontains=busca) | Q(disciplinas__nome__icontains=busca)
        ).distinct()

    # Disciplina
    if disciplina.isdecimal() and len(disciplina) < 10:
        professores = professores.filter(disciplinas__pk=disciplina)

    # Modalidade (HIBRIDA entra nas duas)
    if modalidade == 'ONLINE':
        professores = professores.filter(modalidade__in=['ONLINE', 'HIBRIDA'])
    elif modalidade == 'PRESENCIAL':
        professores = professores.filter(modalidade__in=['PRESENCIAL', 'HIBRIDA'])

    # Faixa de preço
    preco = texto_para_preco(preco_min)
    if preco is not None:
        professores = professores.filter(valor_hora__gte=preco)    # gte = maior ou igual
    preco = texto_para_preco(preco_max)
    if preco is not None:
        professores = professores.filter(valor_hora__lte=preco)    # lte = menor ou igual

    # Dia e período: busca os horários que servem e depois os professores donos deles
    if dia in dict(DIAS_DA_SEMANA) or periodo in PERIODOS:
        horarios = Disponibilidade.objects.all()
        if dia in dict(DIAS_DA_SEMANA):
            horarios = horarios.filter(dia_semana=dia)
        if periodo in PERIODOS:
            comeco, fim = PERIODOS[periodo]
            horarios = horarios.filter(hora_inicio__lt=fim, hora_fim__gt=comeco)    # lt = menor, gt = maior
        professores = professores.filter(pk__in=horarios.values('professor'))

    # Nota mínima
    if nota_min in ['3', '4', '4.5']:
        professores = professores.filter(nota_media__gte=nota_min)

    # Só verificados
    if so_verificados:
        professores = professores.filter(verificado=True)

    # Ordem da lista
    if ordem == 'menor_preco':
        professores = professores.order_by('valor_hora')
    elif ordem == 'maior_preco':
        professores = professores.order_by('-valor_hora')    # "-" = do maior para o menor
    elif ordem == 'melhor_nota':
        professores = professores.order_by('-nota_media')
    else:
        professores = professores.order_by('usuario__nome')

    # Nome e iniciais usados no card
    for professor in professores:
        identificar(professor)

    contexto = {
        'professores': professores,
        'disciplinas': Disciplina.objects.order_by('nome'),
        'dias_da_semana': DIAS_DA_SEMANA,
        'filtros': request.GET,    # mantém o formulário preenchido
        'ordem': ordem,
    }
    return render(request, 'filtro_professores.html', contexto)

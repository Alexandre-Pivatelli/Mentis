from datetime import time
from decimal import Decimal, InvalidOperation

from django.db.models import Q
from django.shortcuts import render

from .models import Disciplina, Disponibilidade
from .views import identificar, professores_queryset

# Sprint 9 - Filtro mais abrangente de professores.
# Esta página não substitui a busca simples (/professores/): ela é uma busca
# com mais opções. Ela reaproveita o card de professor que já existe no site.

# Dias da semana no mesmo formato do banco: 0 = segunda ... 6 = domingo.
# O código fica como texto ('0', '1'...) porque é assim que ele chega pelo endereço (GET).
DIAS_DA_SEMANA = [('0', 'Segunda-feira'), ('1', 'Terça-feira'), ('2', 'Quarta-feira'),
                  ('3', 'Quinta-feira'), ('4', 'Sexta-feira'), ('5', 'Sábado'), ('6', 'Domingo')]

# Cada período do dia é um intervalo de horas (começo, fim).
PERIODOS = {
    'manha': (time(6, 0), time(12, 0)),
    'tarde': (time(12, 0), time(18, 0)),
    'noite': (time(18, 0), time(23, 59)),
}


def texto_para_preco(texto):
    '''
    Transforma o que o aluno digitou no campo de preço num número.
    Aceita vírgula ou ponto (ex.: "50,90" ou "50.90").
    Se o campo estiver vazio ou não for um número, devolve None (= ignorar o filtro).
    '''
    try:
        preco = Decimal(texto.replace(',', '.'))
    except InvalidOperation:
        return None
    # "NaN" e "Infinity" também viram Decimal, mas não são preços de verdade
    # (e fariam o banco dar erro). is_finite() confere que é um número normal.
    if not preco.is_finite():
        return None
    return preco


def filtro_professores(request):
    '''
    Mostra a lista de professores com vários filtros juntos.
    Os filtros chegam pelo GET (no endereço da página), porque buscar não muda nada no banco.
    Cada filtro só é aplicado se o aluno preencheu aquele campo.
    '''
    # Pega o que o aluno escolheu no formulário. Se o campo não veio, fica vazio ('').
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

    # Começa com todos os professores (com nota média e favoritos já calculados).
    professores = professores_queryset(request.user)

    # 1) Nome ou disciplina digitados na busca.
    if busca:
        professores = professores.filter(
            Q(usuario__nome__icontains=busca) | Q(disciplinas__nome__icontains=busca)
        ).distinct()

    # 2) Disciplina escolhida na lista. Só usa se for um número de tamanho normal
    #    (um número gigante digitado à mão no endereço daria erro no banco).
    if disciplina.isdecimal() and len(disciplina) < 10:
        professores = professores.filter(disciplinas__pk=disciplina)

    # 3) Modalidade. Quem dá aula online e presencial (HIBRIDA) aparece nas duas.
    if modalidade == 'ONLINE':
        professores = professores.filter(modalidade__in=['ONLINE', 'HIBRIDA'])
    elif modalidade == 'PRESENCIAL':
        professores = professores.filter(modalidade__in=['PRESENCIAL', 'HIBRIDA'])

    # 4) Faixa de preço por hora.
    preco = texto_para_preco(preco_min)
    if preco is not None:
        professores = professores.filter(valor_hora__gte=preco)    # gte = maior ou igual
    preco = texto_para_preco(preco_max)
    if preco is not None:
        professores = professores.filter(valor_hora__lte=preco)    # lte = menor ou igual

    # 5) Dia da semana e período em que o professor atende.
    # Primeiro achamos os horários (Disponibilidade) que servem;
    # depois ficamos só com os professores donos desses horários.
    if dia in dict(DIAS_DA_SEMANA) or periodo in PERIODOS:
        horarios = Disponibilidade.objects.all()
        if dia in dict(DIAS_DA_SEMANA):
            horarios = horarios.filter(dia_semana=dia)
        if periodo in PERIODOS:
            comeco, fim = PERIODOS[periodo]
            # O horário serve se começa antes do fim do período e termina depois do começo dele.
            horarios = horarios.filter(hora_inicio__lt=fim, hora_fim__gt=comeco)
        professores = professores.filter(pk__in=horarios.values('professor'))

    # 6) Nota mínima das avaliações.
    if nota_min in ['3', '4', '4.5']:
        professores = professores.filter(nota_media__gte=nota_min)

    # 7) Só professores verificados.
    if so_verificados:
        professores = professores.filter(verificado=True)

    # 8) Ordem da lista. Se não escolheu nada, fica em ordem alfabética.
    if ordem == 'menor_preco':
        professores = professores.order_by('valor_hora')
    elif ordem == 'maior_preco':
        professores = professores.order_by('-valor_hora')     # o "-" inverte: do maior para o menor
    elif ordem == 'melhor_nota':
        professores = professores.order_by('-nota_media')
    else:
        professores = professores.order_by('usuario__nome')

    # Prepara o nome e as iniciais que o card de professor mostra.
    for professor in professores:
        identificar(professor)

    # contexto é o dicionário com os dados enviados para o template.
    # 'filtros' guarda o que o aluno escolheu, para o formulário continuar preenchido.
    contexto = {
        'professores': professores,
        'disciplinas': Disciplina.objects.order_by('nome'),
        'dias_da_semana': DIAS_DA_SEMANA,
        'filtros': request.GET,
        'ordem': ordem,
    }
    return render(request, 'filtro_professores.html', contexto)

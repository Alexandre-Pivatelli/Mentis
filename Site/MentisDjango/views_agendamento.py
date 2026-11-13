from datetime import date, datetime, time, timedelta

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from .models import Aluno, Aula, Disciplina, Professor, StatusAula

# Toda aula marcada por aqui dura 1 hora.
DURACAO_MIN = 60

DIAS_DA_SEMANA = ['Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira',
                  'Sexta-feira', 'Sábado', 'Domingo']


def proxima_data(dia_semana, hora):
    '''
    Sprint 9: recebe um dia da semana (0 = segunda ... 6 = domingo) e um horário,
    e devolve a próxima data em que esse dia da semana acontece.
    Exemplo: se hoje é quarta e o aluno clicou em "Sexta-feira", devolve a data desta sexta.
    Se o dia for hoje, mas o horário já passou, pula para a semana seguinte.
    '''
    hoje = timezone.localdate()
    dias_ate_la = (dia_semana - hoje.weekday()) % 7
    dia = hoje + timedelta(days=dias_ate_la)
    if timezone.make_aware(datetime.combine(dia, hora)) <= timezone.now():
        dia = dia + timedelta(days=7)
    return dia


def horario_vindo_do_perfil(parametros):
    '''
    Sprint 9: quando o aluno clica num horário do perfil do professor,
    o link chega aqui com ?dia=4&hora=14:00 no endereço.
    Esta função transforma isso nos dados que o formulário precisa (data e hora).
    Se o link vier errado ou sem esses dados, devolve um dicionário vazio
    e o formulário só aparece em branco.
    '''
    dia_texto = parametros.get('dia', '')
    hora_texto = parametros.get('hora', '')

    # O dia só vale se for um dos textos '0', '1', ..., '6'.
    if dia_texto not in ['0', '1', '2', '3', '4', '5', '6']:
        return {}
    try:
        hora = time.fromisoformat(hora_texto)
    except ValueError:
        return {}

    dia = proxima_data(int(dia_texto), hora)
    return {'data': dia.isoformat(), 'hora': hora.strftime('%H:%M')}


@login_required(login_url='login')
def agendar_aula(request, professor_id):
    '''
    Mostra o formulário para o aluno marcar uma aula com o professor.
    No GET, só mostra a página.
    No POST, confere os dados e, se estiver tudo certo, cria a aula
    e manda o aluno para a agenda dele.
    '''
    aluno = Aluno.objects.filter(usuario=request.user).first()
    professor = get_object_or_404(Professor, pk=professor_id)
    disciplinas = professor.disciplinas.all()
    disponibilidades = professor.disponibilidades.order_by('dia_semana', 'hora_inicio')

    # Lista de horários do professor, já com o nome do dia, para mostrar na página.
    horarios = []
    for disponibilidade in disponibilidades:
        horarios.append({
            'dia_semana': disponibilidade.dia_semana,   # Sprint 9: usado no link de cada horário
            'dia': DIAS_DA_SEMANA[disponibilidade.dia_semana],
            'inicio': disponibilidade.hora_inicio,
            'fim': disponibilidade.hora_fim,
        })

    erro = ''
    if request.method == 'POST':
        disciplina_id = request.POST.get('disciplina')
        data_texto = request.POST.get('data')
        hora_texto = request.POST.get('hora')
        modalidade = request.POST.get('modalidade')
        observacao = request.POST.get('observacao', '').strip()

        # 1) Só aluno pode marcar aula.
        if aluno is None:
            erro = 'Só contas de aluno podem marcar aulas.'

        # 2) A disciplina precisa ser uma das que o professor ensina.
        disciplina = Disciplina.objects.filter(pk=disciplina_id, professores=professor).first() if disciplina_id else None
        if not erro and disciplina is None:
            erro = 'Escolha uma disciplina.'

        # 3) Data e hora precisam estar preenchidas e num formato válido.
        if not erro:
            try:
                dia = date.fromisoformat(data_texto)
                hora = time.fromisoformat(hora_texto)
            except (TypeError, ValueError):
                erro = 'Preencha a data e o horário da aula.'

        if not erro:
            inicio = timezone.make_aware(datetime.combine(dia, hora))
            fim = inicio + timedelta(minutes=DURACAO_MIN)

            # 4) Não dá para marcar aula no passado.
            if inicio <= timezone.now():
                erro = 'Escolha uma data e um horário no futuro.'

        # 5) O horário precisa estar dentro da disponibilidade do professor naquele dia da semana.
        if not erro:
            dentro_do_horario = False
            for disponibilidade in disponibilidades.filter(dia_semana=dia.weekday()):
                comeca = timezone.make_aware(datetime.combine(dia, disponibilidade.hora_inicio))
                termina = timezone.make_aware(datetime.combine(dia, disponibilidade.hora_fim))
                if comeca <= inicio and fim <= termina:
                    dentro_do_horario = True
            if not dentro_do_horario:
                erro = 'O professor não atende nesse dia e horário. Confira os horários ao lado.'

        # 6) Não pode bater com outra aula do professor nem do aluno.
        if not erro:
            aulas_do_dia = Aula.objects.filter(
                status__in=[StatusAula.AGENDADA, StatusAula.CONFIRMADA],
                data_hora__date=dia,
            )
            aulas_do_dia = aulas_do_dia.filter(professor=professor) | aulas_do_dia.filter(aluno=aluno)
            for aula in aulas_do_dia:
                aula_fim = aula.data_hora + timedelta(minutes=aula.duracao_min)
                if inicio < aula_fim and fim > aula.data_hora:
                    erro = 'Esse horário já está ocupado. Escolha outro.'

        # 7) A modalidade precisa ser online ou presencial.
        if not erro and modalidade not in ['ONLINE', 'PRESENCIAL']:
            erro = 'Escolha se a aula será online ou presencial.'

        # Se passou por todas as conferências, cria a aula.
        if not erro:
            aula = Aula.objects.create(
                aluno=aluno,
                professor=professor,
                disciplina=disciplina,
                data_hora=inicio,
                duracao_min=DURACAO_MIN,
                modalidade=modalidade,
                local_ou_link=observacao or 'A combinar com o professor pelas mensagens',
                valor=professor.valor_hora,
                status=StatusAula.AGENDADA,
            )
            # Manda o aluno para a agenda, já aberta no dia da aula nova.
            dia_texto = dia.isoformat()
            return redirect(reverse('agenda_aluno') + '?mes=' + dia.replace(day=1).isoformat() + '&dia=' + dia_texto)

    # O que vai aparecer já preenchido no formulário:
    # - no POST (deu erro), é o que o aluno já tinha digitado, para não apagar;
    # - no GET (Sprint 9), é o horário que o aluno clicou no perfil, se ele veio por esse link.
    if request.method == 'POST':
        dados = request.POST
    else:
        dados = horario_vindo_do_perfil(request.GET)

    contexto = {
        'professor': professor,
        'nome_professor': professor.usuario.nome or professor.usuario.username,
        'disciplinas': disciplinas,
        'horarios': horarios,
        'erro': erro,
        'dados': dados,
        'hoje': timezone.localdate().isoformat(),
    }
    return render(request, 'agendar_aula.html', contexto)

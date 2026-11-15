import calendar
from datetime import date, datetime, time, timedelta

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, OuterRef, Subquery
from django.http import Http404, HttpResponse, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods, require_GET

from .calendario import aula_ics
from .models import Aluno, Aula, Avaliacao, Conversa, Mensagem, Professor, StatusAula


@never_cache
@login_required(login_url='login')
@require_GET
def aula_calendario_view(request, aula_id):
    aula = get_object_or_404(
        Aula.objects.select_related('disciplina'),
        pk=aula_id,
        aluno__usuario=request.user,
        status=StatusAula.CONFIRMADA,
    )
    response = HttpResponse(aula_ics(aula, timezone.now()), content_type='text/calendar; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="mentis-aula-{aula.pk}.ics"'
    return response


class MensagemForm(forms.Form):
    texto = forms.CharField(max_length=3000, strip=True, widget=forms.Textarea(attrs={
        'rows': 2, 'placeholder': 'Escreva uma mensagem…', 'aria-label': 'Sua mensagem'}))


def conversas_usuario(user):
    return Conversa.objects.filter(Q(aluno__usuario=user) | Q(professor__usuario=user)).select_related(
        'aluno__usuario', 'professor__usuario')


@never_cache
@login_required(login_url='login')
@require_http_methods(['GET', 'POST'])
def mensagens_view(request):
    user = request.user
    aluno = Aluno.objects.filter(usuario=user).first()
    if not aluno and not Professor.objects.filter(usuario=user).exists():
        return HttpResponseForbidden('É necessário um perfil de estudante ou professor.')
    conversas = conversas_usuario(user)
    if request.method == 'POST' and request.POST.get('acao') == 'nova':
        if not aluno:
            return HttpResponseForbidden('Apenas estudantes podem iniciar uma conversa por aqui.')
        professor = get_object_or_404(Professor, pk=request.POST.get('professor') if request.POST.get('professor', '').isdigit() and len(request.POST.get('professor', '')) < 19 else 0)
        if professor.usuario_id == user.pk:
            return HttpResponseForbidden('Escolha outro participante.')
        conversa, _ = Conversa.objects.get_or_create(aluno=aluno, professor=professor)
        return redirect(reverse('mensagens_aluno') + f'?conversa={conversa.pk}')
    selected = request.GET.get('conversa')
    conversa = get_object_or_404(conversas, pk=selected if selected.isdigit() and len(selected)<19 else 0) if selected else None
    form = MensagemForm(request.POST if request.method == 'POST' else None)
    if request.method == 'POST':
        if conversa is None:
            return HttpResponseForbidden('Escolha uma conversa antes de enviar.')
        if form.is_valid():
            Mensagem.objects.create(conversa=conversa, autor=user, texto=form.cleaned_data['texto'])
            conversa.save(update_fields=['atualizada_em'])
            return redirect(reverse('mensagens_aluno') + f'?conversa={conversa.pk}')
    items = []
    tem_anteriores = False
    if conversa:
        conversa.mensagens.exclude(autor=user).filter(lida_em__isnull=True).update(lida_em=timezone.now())
        historico = conversa.mensagens.select_related('autor')
        antes = request.GET.get('antes', '')
        if antes.isdigit() and len(antes) < 19 and request.GET.get('format') != 'json':
            historico = historico.filter(pk__lt=int(antes))
        items = list(historico.order_by('-pk')[:100])[::-1]
        tem_anteriores = bool(items and conversa.mensagens.filter(pk__lt=items[0].pk).exists())
    if request.GET.get('format') == 'json':
        after = request.GET.get('apos', '0')
        after = int(after) if after.isdigit() and len(after) < 19 else 0
        return JsonResponse({'mensagens': [{'id': m.pk, 'texto': m.texto, 'minha': m.autor_id == user.pk,
            'hora': timezone.localtime(m.enviada_em).strftime('%H:%M')} for m in items if m.pk > after]})
    ultima = Mensagem.objects.filter(conversa=OuterRef('pk')).order_by('-pk')
    lista = conversas.annotate(ultima_texto=Subquery(ultima.values('texto')[:1]),
        nao_lidas=Count('mensagens', filter=Q(mensagens__lida_em__isnull=True) & ~Q(mensagens__autor=user)))
    for c in lista:
        c.contato = c.professor.usuario if c.aluno_id == user.pk else c.aluno.usuario
    contato = (conversa.professor.usuario if conversa.aluno_id == user.pk else conversa.aluno.usuario) if conversa else None
    return render(request, 'mensagens.html', {'conversas': lista, 'conversa': conversa, 'contato': contato,
        'mensagens': items, 'tem_anteriores': tem_anteriores, 'form': form, 'aluno': aluno,
        'professores_contato': Professor.objects.select_related('usuario').exclude(usuario=user).order_by('usuario__nome') if aluno else []})


class AvaliacaoAulaForm(forms.Form):
    nota = forms.TypedChoiceField(
        label='Nota',
        choices=[('', 'Selecione uma nota')] + [(nota, f'{nota}/5') for nota in range(1, 6)],
        coerce=int,
    )
    comentario = forms.CharField(
        label='Comentário',
        max_length=1500,
        widget=forms.Textarea(attrs={'rows': 3}),
    )


@never_cache
@login_required(login_url='login')
@require_http_methods(['GET', 'POST'])
def agenda_view(request):
    aluno = get_object_or_404(Aluno, usuario=request.user)
    hoje = timezone.localdate()
    try:
        mes = date.fromisoformat(request.GET.get('mes', hoje.replace(day=1).isoformat())).replace(day=1)
        if not 1901 <= mes.year <= 2099:
            raise ValueError
    except (ValueError, TypeError):
        mes = hoje.replace(day=1)
    seguinte = (mes.replace(day=28) + timedelta(days=4)).replace(day=1)
    anterior = (mes - timedelta(days=1)).replace(day=1)
    aulas = list(Aula.objects.filter(aluno=aluno, data_hora__gte=timezone.make_aware(datetime.combine(mes, time.min)),
        data_hora__lt=timezone.make_aware(datetime.combine(seguinte, time.min))).select_related(
            'professor__usuario', 'disciplina', 'avaliacao').order_by('data_hora', 'pk'))
    try:
        dia = date.fromisoformat(request.GET.get('dia', hoje.isoformat() if hoje.month == mes.month and hoje.year == mes.year else mes.isoformat()))
        if dia.month != mes.month or dia.year != mes.year:
            dia = mes
    except (TypeError, ValueError):
        dia = mes
    semanas = []
    for semana in calendar.Calendar(firstweekday=0).monthdatescalendar(mes.year, mes.month):
        semanas.append([{'data': d, 'atual': d.month == mes.month, 'hoje': d == hoje, 'selecionado': d == dia,
            'quantidade': sum(timezone.localtime(a.data_hora).date() == d for a in aulas)} for d in semana])
    do_dia = [a for a in aulas if timezone.localtime(a.data_hora).date() == dia]
    status_resposta = 200
    for aula in do_dia:
        recebeu_post = request.method == 'POST' and request.POST.get('aula_id') == str(aula.pk)
        if aula.status != StatusAula.REALIZADA:
            continue
        if hasattr(aula, 'avaliacao'):
            if recebeu_post:
                return redirect(f"{reverse('agenda_aluno')}?mes={mes.isoformat()}&dia={dia.isoformat()}#aula-{aula.pk}")
            continue
        if recebeu_post:
            form = AvaliacaoAulaForm(request.POST, prefix=f'aula-{aula.pk}')
            if form.is_valid():
                # A relação única com a aula também protege contra envios simultâneos.
                _, criada = Avaliacao.objects.get_or_create(aula=aula, defaults=form.cleaned_data)
                if criada:
                    messages.success(request, 'Avaliação publicada.')
                return redirect(f"{reverse('agenda_aluno')}?mes={mes.isoformat()}&dia={dia.isoformat()}#aula-{aula.pk}")
            aula.form_avaliacao = form
            status_resposta = 400
        else:
            aula.form_avaliacao = AvaliacaoAulaForm(prefix=f'aula-{aula.pk}')

    if request.method == 'POST' and status_resposta != 400:
        raise Http404

    return render(request, 'agenda.html', {'mes': mes, 'anterior': anterior, 'seguinte': seguinte,
        'semanas': semanas, 'dia': dia, 'hoje': hoje, 'aulas_dia': do_dia, 'total_mes': len(aulas)},
        status=status_resposta)

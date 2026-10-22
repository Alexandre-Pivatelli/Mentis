from datetime import timedelta

from django.conf import settings
from django.db.models import F
from django.utils import timezone
from django.utils.crypto import salted_hmac

from .models import TentativaAutenticacao


def permitir_tentativa(request, operacao):
    """Reserva uma tentativa usando UPDATE condicional, inclusive entre processos.

    Não confia em X-Forwarded-For enviado pelo cliente. Em produção, o proxy
    deve fornecer REMOTE_ADDR corretamente. Contabiliza todos os POSTs.
    """
    agora = timezone.now()
    limite, segundos = ((getattr(settings, 'AUTH_LOGIN_LIMIT', 20), 900)
                        if operacao == 'login' else (getattr(settings, 'AUTH_SIGNUP_LIMIT', 10), 3600))
    chave = salted_hmac('mentis.auth.limit', f'{operacao}:{request.META.get("REMOTE_ADDR", "unknown")}',
                        algorithm='sha256').hexdigest()
    TentativaAutenticacao.objects.filter(inicio__lt=agora - timedelta(days=1)).delete()
    TentativaAutenticacao.objects.get_or_create(chave=chave, defaults={'inicio': agora})
    TentativaAutenticacao.objects.filter(chave=chave, inicio__lte=agora - timedelta(seconds=segundos)).update(
        inicio=agora, quantidade=0)
    permitido = TentativaAutenticacao.objects.filter(chave=chave, quantidade__lt=limite).update(
        quantidade=F('quantidade') + 1)
    return bool(permitido), segundos

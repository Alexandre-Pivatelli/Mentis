from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET


MENSAGENS = {
    400: ('Solicitação inválida', 'Não conseguimos processar esta solicitação. Confira o endereço e tente novamente.'),
    403: ('Acesso restrito', 'Você não tem permissão para acessar esta página.'),
    404: ('Página não encontrada', 'O endereço pode ter mudado ou esta página pode ter sido removida.'),
    500: ('Algo deu errado', 'Encontramos um problema ao carregar a página. Tente novamente em alguns instantes.'),
}


def _pagina_erro(codigo):
    titulo, descricao = MENSAGENS[codigo]
    # Sem contexto da sessão ou consultas ao banco, inclusive se ele estiver indisponível.
    return render(None, 'erro.html', {
        'codigo': codigo,
        'titulo': titulo,
        'descricao': descricao,
    }, status=codigo)


@never_cache
def erro_400(request, exception):
    return _pagina_erro(400)


@never_cache
def erro_403(request, exception):
    return _pagina_erro(403)


@never_cache
def erro_404(request, exception):
    return _pagina_erro(404)


@never_cache
def erro_500(request):
    return _pagina_erro(500)


@never_cache
@require_GET
def pagina_erro(request):
    # Permite visualizar a página com DEBUG ativo sem provocar uma falha real.
    return _pagina_erro(404)

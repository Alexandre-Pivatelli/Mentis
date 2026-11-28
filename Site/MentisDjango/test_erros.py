from django.core.exceptions import PermissionDenied, SuspiciousOperation
from django.test import SimpleTestCase, override_settings
from django.urls import include, path, reverse


def provocar_erro(request, codigo):
    if codigo == 400:
        raise SuspiciousOperation('Detalhe interno da solicitação')
    if codigo == 403:
        raise PermissionDenied('Detalhe interno da permissão')
    raise RuntimeError('Detalhe interno do servidor')


# Os handlers pertencem ao URLconf raiz, como ocorre na configuração real.
from config.urls import handler400, handler403, handler404, handler500

urlpatterns = [
    path('falha/<int:codigo>/', provocar_erro),
    path('', include('config.urls')),
]


@override_settings(DEBUG=False, SECURE_SSL_REDIRECT=False, ROOT_URLCONF=__name__)
class PaginasErroTests(SimpleTestCase):
    def test_handlers_renderizam_sem_banco_nem_detalhes_internos(self):
        self.client.raise_request_exception = False
        for codigo in (400, 403, 404, 500):
            with self.subTest(codigo=codigo):
                url = '/pagina-inexistente/' if codigo == 404 else f'/falha/{codigo}/'
                resposta = self.client.get(url)
                self.assertContains(resposta, f'Erro {codigo}', status_code=codigo)
                self.assertNotContains(resposta, 'Detalhe interno', status_code=codigo)
                self.assertTemplateUsed(resposta, 'erro.html')
                self.assertIn('no-store', resposta['Cache-Control'])

    @override_settings(DEBUG=True)
    def test_visualizacao_com_debug_ativo(self):
        resposta = self.client.get(reverse('pagina_erro'))
        self.assertContains(resposta, 'Página não encontrada', status_code=404)

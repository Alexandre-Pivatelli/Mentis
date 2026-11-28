from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

handler400 = 'MentisDjango.views_erros.erro_400'
handler403 = 'MentisDjango.views_erros.erro_403'
handler404 = 'MentisDjango.views_erros.erro_404'
handler500 = 'MentisDjango.views_erros.erro_500'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('MentisDjango.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

from django.urls import path
from . import views
from .views_aluno import ambiente_aluno_view
from .views_estudante import mensagens_view, agenda_view
from .views_favoritos import favoritos_view, favorito_professor_view

urlpatterns = [
    path('', views.principal_view, name='principal'),
    path('login/', views.login_view, name='login'),
    path('sair/', views.logout_view, name='logout'),
    path('cadastro/', views.cadastro_view, name='cadastro'),
    path('usuarios/', views.usuarios_view, name='usuarios'),
    path('perfil-aluno/', views.perfil_aluno_view, name='perfil_aluno'),
    path('perfil/editar/', views.editar_perfil_view, name='editar_perfil'),
    path('perfil/sessao/', views.sessao_perfil_view, name='sessao_perfil'),
    path('professores/', views.professores_view, name='professores'),
    path('favoritos/', favoritos_view, name='favoritos_aluno'),
    path('professor/<int:pk>/favorito/', favorito_professor_view, name='favorito_professor'),
    path('professor/', views.professor_view, name='professor'),
    path('professor/<int:pk>/', views.professor_view, name='professor_detalhe'),
    path('avaliar-site/', views.avaliar_site_view, name='avaliar_site'),
    path('mensagens/', mensagens_view, name='mensagens_aluno'),
    path('agenda/', agenda_view, name='agenda_aluno'),
    path('ambiente-aluno/', ambiente_aluno_view, name='ambiente_aluno'),
]

from django.urls import path
from . import views
from .views_estudante import mensagens_view, agenda_view
from .views_aluno import ambiente_aluno_view

urlpatterns = [
    path('mensagens/', mensagens_view, name='mensagens_aluno'),
    path('agenda/', agenda_view, name='agenda_aluno'),
    path("", views.principal_view, name="principal"),
    path("login/", views.login_view, name="login"),
    path("sair/", views.logout_view, name="logout"),
    path("usuarios/", views.usuarios_view, name="usuarios"),
    path('cadastro/', views.cadastro_view, name='cadastro'),
    path("perfil-aluno/", views.perfil_aluno_view, name="perfil_aluno"),
    path('ambiente-aluno/', ambiente_aluno_view, name='ambiente_aluno'),
    path("professor/", views.professor_view, name="professor"),
    path("professor/<int:pk>/", views.professor_view, name="professor_detalhe"),
    path('perfil/editar/', views.editar_perfil_view, name='editar_perfil'),
    path('perfil/sessao/', views.sessao_perfil_view, name='sessao_perfil'),
]

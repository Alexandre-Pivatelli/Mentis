from django.urls import path
from . import views

urlpatterns = [
    path("", views.principal_view, name="principal"),
    path("login/", views.login_view, name="login"),
    path("sair/", views.logout_view, name="logout"),
    path("usuarios/", views.usuarios_view, name="usuarios"),
    path('cadastro/', views.cadastro_view, name='cadastro'),
    path("perfil-aluno/", views.perfil_aluno_view, name="perfil_aluno"),
    path("professor/", views.professor_view, name="professor"),
    path("professor/<int:pk>/", views.professor_view, name="professor_detalhe"),
    path('perfil/editar/', views.editar_perfil_view, name='editar_perfil'),
    path('professores/', views.professores_view, name='professores'),
]

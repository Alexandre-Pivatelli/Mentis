from django.urls import path
from . import views
from .views_erros import pagina_erro
from .views_agendamento import agendar_aula
from .views_aulas_professor import aulas_professor, responder_aula
from .views_cancelar_aula import cancelar_aula
from .views_aluno import ambiente_aluno_view, avaliar_aula_view
from .views_estudante import agenda_view, aula_calendario_view, mensagens_view
from .views_favoritos import favoritos_view, favorito_professor_view
from .views_filtro import filtro_professores
from .views_pagamentos import cancelar_assinatura_view, historico_pagamentos_view

urlpatterns = [
    path('erro/', pagina_erro, name='pagina_erro'),
    path('professor/<int:professor_id>/agendar/', agendar_aula, name='agendar_aula'),
    path('', views.principal_view, name='principal'),
    path('login/', views.login_view, name='login'),
    path('sair/', views.logout_view, name='logout'),
    path('cadastro/', views.cadastro_view, name='cadastro'),
    path('cadastro/concluido/', views.cadastro_concluido_view, name='cadastro_concluido'),
    path('usuarios/', views.usuarios_view, name='usuarios'),
    path('perfil-aluno/', views.perfil_aluno_view, name='perfil_aluno'),
    path('perfil/editar/', views.editar_perfil_view, name='editar_perfil'),
    path('perfil/senha/', views.redefinir_senha_view, name='redefinir_senha'),
    path('redefinir-senha/', views.redefinir_senha_view, name='redefinir_senha_atalho'),
    path('perfil/sessao/', views.sessao_perfil_view, name='sessao_perfil'),
    path('professores/', views.professores_view, name='professores'),
    path('professores/filtro/', filtro_professores, name='filtro_professores'),
    path('favoritos/', favoritos_view, name='favoritos_aluno'),
    path('professor/<int:pk>/favorito/', favorito_professor_view, name='favorito_professor'),
    path('professor/', views.professor_view, name='professor'),
    path('professor/<int:pk>/', views.professor_view, name='professor_detalhe'),
    path('avaliar-site/', views.avaliar_site_view, name='avaliar_site'),
    path('mensagens/', mensagens_view, name='mensagens_aluno'),
    path('agenda/', agenda_view, name='agenda_aluno'),
    path('agenda/aulas/<int:aula_id>/calendario.ics', aula_calendario_view, name='aula_calendario'),
    path('agenda/aulas/<int:aula_id>/cancelar/', cancelar_aula, name='cancelar_aula'),
    path('ambiente-aluno/', ambiente_aluno_view, name='ambiente_aluno'),
    path('aula/<int:pk>/avaliar/', avaliar_aula_view, name='avaliar_aula'),
    path('materiais/', views.materiais_view, name='materiais'),
    path('sobre/', views.sobre_view, name='sobre'),

    # Painel do professor
    path('painel/professor/', views.painel_professor_view, name='painel_professor'),
    path('painel/professor/aulas/', aulas_professor, name='aulas_professor'),
    path('painel/professor/aulas/<int:aula_id>/responder/', responder_aula, name='responder_aula'),
    path('painel/professor/agenda/', views.painel_professor_agenda, name='painel_professor_agenda'),
    path('painel/professor/assinatura/', views.painel_professor_assinatura, name='painel_professor_assinatura'),
    path('painel/professor/materiais/novo/', views.painel_professor_material_criar, name='painel_professor_material_criar'),
    path('painel/professor/materiais/<int:pk>/excluir/', views.painel_professor_material_excluir, name='painel_professor_material_excluir'),
    path('painel/professor/materiais/<int:pk>/editar/', views.painel_professor_material_editar, name='painel_professor_material_editar'),
    path('professor/<int:pk>/assinatura/', views.assinatura_professor_view, name='assinatura_professor'),
    path('professor/<int:pk>/assinatura/cancelar/', cancelar_assinatura_view, name='cancelar_assinatura'),
    path('pagamentos/', historico_pagamentos_view, name='historico_pagamentos'),
]


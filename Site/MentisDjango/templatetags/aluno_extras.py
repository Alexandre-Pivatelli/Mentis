"""Filtros de template do ambiente do aluno (Sprint 6)."""
from django import template

register = template.Library()


@register.filter
def iniciais(nome):
    """'Bia Toledano' -> 'BT'. Usado no card do perfil."""
    return ''.join(parte[0] for parte in str(nome).split()[:2]).upper()

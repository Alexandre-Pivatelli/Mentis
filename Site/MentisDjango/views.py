from django.shortcuts import render


def principal_view(request):
    return render(request, "principal.html")


def login_view(request):
    return render(request, "login.html")


def usuarios_view(request):
    return render(request, "usuarios.html")


def perfil_aluno_view(request):
    return render(request, "perfil_aluno.html")


def professor_view(request):
    return render(request, "professor.html")

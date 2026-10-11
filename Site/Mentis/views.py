from django.shortcuts import render

def login(request):
    '''
    View function for home page of site.
    Renders the home.html template.
    '''
    return render(request, 'login.html')
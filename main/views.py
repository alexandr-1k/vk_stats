from django.shortcuts import render
from .services import get_chart_data, get_empty_data


def login_view(request):
    return render(request, "main/start_page.html")


def app_view(request):

    return render(request, "main/input_page.html", get_empty_data())


def input_view(request):

    #return render(request, "main/input_page.html", get_chart_data(access_token, request.GET.dict()))
    return render(request, "main/input_page.html", get_empty_data())




from django.shortcuts import render
from .services import get_chart_data, get_empty_data, extract_data_from_db
from django.http import HttpResponse
from django.contrib.admin.models import LogEntry

LogEntry.objects.all().delete()

def login_view(request):
    return render(request, "main/start_page.html")


def app_view(request):
    return render(request, "main/input_page.html", get_empty_data('0'))


def input_view(request):
    return render(request, "main/input_page.html", get_chart_data(request))


def get_csv(request):

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename=export.csv'
    extracted = extract_data_from_db(request)
    extracted.to_csv(path_or_buf=response, encoding='utf-8', index=False)
    return response

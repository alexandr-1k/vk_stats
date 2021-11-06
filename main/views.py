from allauth.socialaccount.models import SocialToken
from django.shortcuts import render
import time


def login_view(request):
    return render(request, "main/start_page.html")


def app_view(request):
    print(f"\nRequest.user: {request.user}")
    return render(request, "main/input_page.html", {'x': [1, 2, 3, 4, 5], 'y1': [i * 2 for i in range(5)],
                                                'y2': [i * 3 for i in range(5)]})


def input_view(request):
    print(f"\nRequest.user: {request.user}")

    access_token = SocialToken.objects.get(account__user=request.user,
                                           account__provider='vk')

    print(f"\nAccess token in use:  ... {str(access_token)[-5:]}")

    return render(request, "main/input_page.html")

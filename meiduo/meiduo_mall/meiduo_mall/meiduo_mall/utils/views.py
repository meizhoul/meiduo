from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin


class LoginRequired(LoginRequiredMixin,View):
    pass

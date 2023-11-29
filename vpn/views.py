import logging
from sys import getsizeof
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError
from django.http import HttpResponse, HttpRequest
from django.shortcuts import render, redirect

from .dtos.edit_profile_dto import EditProfileForm
from .dtos.site_dto import SiteForm
from .dtos.user_dto import FormUser
from .models import Site

logger = logging.getLogger(__name__)


def login_view(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        user = find_user(request.POST["username"])

        if user and user.is_active:
            aut_user = authenticate(
                request,
                username=request.POST["username"],
                password=request.POST["password"],
            )

            if aut_user is not None:
                login(request, aut_user)
                return redirect("main")
            else:
                return render(
                    request,
                    "account/login.html",
                    {"errors": "Неверное имя пользователя или пароль."},
                )

        else:
            return render(
                request,
                "account/login.html",
                {"errors": "Такого пользователя не существует"},
            )

    context = {}
    return render(request, "account/login.html", context)


def find_user(username: str) -> bool | User:
    try:
        user = User.objects.get(username=username)
    except ObjectDoesNotExist:
        return False
    return user


def registration(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        user_dto = FormUser(request.POST)

        if user_dto.is_valid():
            user = User(**user_dto.cleaned_data)
            user.set_password(user_dto.cleaned_data["password"])
            try:
                user.save()
            except IntegrityError as e:
                context = (
                    {"errors": ["Это имя уже занято"]}
                    if "UNIQUE" in str(e)
                    else {"errors": "[Не правильно ввели данные]"}
                )
                return render(request, "account/registration.html", context)

            login(request, user, backend="django.contrib.auth.backends.ModelBackend")
            return redirect("main")

        else:
            context = {"errors": ["Не правильно ввели данные"]}
            return render(request, "account/registration.html", context)

    else:
        context = {}
        return render(request, "account/registration.html", context)


def main(request) -> HttpResponse:
    return render(request, "main/main.html")


@login_required
def profile_view(request: HttpRequest) -> HttpResponse:
    sites = request.user.site_set.all()
    form = SiteForm()
    if request.method == "POST":
        form = SiteForm(request.POST)
        if form.is_valid():
            form.cleaned_data["name"] = form.cleaned_data["name"].replace(" ", "_")
            domain = urlparse(form.cleaned_data["url"]).netloc
            site = Site(**form.cleaned_data, domain=domain)
            site.user_id = request.user
            try:
                site.save()
                return render(
                    request,
                    "account/profile.html",
                    {"user": request.user, "sites": sites, "form": form},
                )

            except IntegrityError as e:
                errors = (
                    ["Название или домен уже заняты."]
                    if "UNIQUE" in str(e)
                    else ["Не удалось добавить сайт. Пожалуйста, проверьте данные."]
                )
                return render(
                    request,
                    "account/profile.html",
                    {
                        "errors": errors,
                        "user": request.user,
                        "sites": sites,
                        "form": form,
                    },
                )

    return render(
        request,
        "account/profile.html",
        {
            "user": request.user,
            "sites": sites,
            "form": form,
        },
    )


@login_required
def edit_profile(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = EditProfileForm(request.POST)
        if form.is_valid():
            new_username = form.cleaned_data["new_username"]

            try:
                User.objects.get(username=new_username)
                errors = ["Это имя уже занято. Выберите другое."]
                sites = request.user.site_set.all()
                form = SiteForm()
                return render(
                    request,
                    "account/profile.html",
                    {
                        "errors": errors,
                        "user": request.user,
                        "sites": sites,
                        "form": form,
                    },
                )

            except User.DoesNotExist:
                request.user.username = new_username
                request.user.save()
                return redirect("profile")

        return render(
            request, "account/profile.html", {"errors": ["Data entered incorrectly"]}
        )
    return render(request, "account/profile.html", {"errors": ["Invalid request"]})


def proxy_view(
    request: HttpRequest, user_site_name: str, original_link: str
) -> HttpResponse:
    if request.method == "GET":
        if "proxy" in original_link:
            len_prefix = (
                str(original_link).index(user_site_name) + len(user_site_name) + 1
            )
            original_link = str(original_link)[len_prefix::]

        proxy_links = {}
        local_host = request.META["HTTP_HOST"]
        protocol = urlparse(original_link).scheme + "://"
        proxy_links[protocol] = str(original_link).replace(protocol, "")
        proxy_result = (
            f"{protocol}{local_host}/proxy/{user_site_name}/{proxy_links[protocol]}"
        )
        cookies = request.COOKIES
        response = requests.get(
            original_link, proxies={protocol: proxy_result}, cookies=cookies
        )

        html_content = response.text
        domain = urlparse(original_link).netloc

        update_user_activity_in_site(
            request.user.id,
            site_domain=domain,
            text_content=html_content,
            cookie=str(cookies),
        )

        context = {
            "text_content": update_href_in_html(
                html_content, user_site_name, domain, protocol
            ),
            "user_site_name": user_site_name,
        }

        return render(request, "account/proxy.html", context)


def update_href_in_html(
    text_content: str, user_site_name: str, domain: str, protocol: str
) -> str:
    soup = BeautifulSoup(text_content, "html.parser")

    for a_tag in soup.find_all("a"):
        original_link = a_tag.get("href")
        if original_link is not None and "proxy" not in original_link:
            if not urlparse(original_link).netloc:
                original_link = f"{protocol}{domain}{original_link}"
            elif urlparse(original_link).netloc != domain:
                continue

            proxy_url = "proxy/"
            new_href = f"{proxy_url}{user_site_name}/{original_link}/"
            a_tag["href"] = new_href

    return str(soup)


def update_user_activity_in_site(
    user_id: str,
    site_domain: str,
    text_content: str,
    cookie: str,
) -> None:
    downloaded_data_size = getsizeof(text_content) / (1024**3)
    sent_data_size = getsizeof(cookie) / (1024**3)
    try:
        site = Site.objects.get(user_id=user_id, url__contains=site_domain)

        site.link_click_count += 1
        site.downloaded_data_size += downloaded_data_size
        site.sent_data_size += sent_data_size

        site.save()
    except Site.DoesNotExist as e:
        logger.error(f"Error updating user activity: {user_id, site_domain} - {e}")

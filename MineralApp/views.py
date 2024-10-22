from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib.auth.hashers import make_password
from django.core.mail import send_mail
from django.db import IntegrityError
from .models import CustomUser
from django.conf import settings
from django.contrib.auth.decorators import login_required

def login_signup_view(request):
    if request.method == "POST":
        # Verifica si el formulario es de registro (si se envía el campo `confirm_password`)
        if 'confirm_password' in request.POST:
            # Proceso de registro
            username = request.POST.get("username")
            email = request.POST.get("email")
            password = request.POST.get("password")
            confirm_password = request.POST.get("confirm_password")

            if password == confirm_password:
                user = CustomUser.objects.create_user(
                    username=username,
                    email=email,
                    password=password
                )
                return redirect('pending_approval')

            else:
                return render(request, 'login.html', {'error': 'Las contraseñas no coinciden.'})

        else:
            # Proceso de inicio de sesión
            username = request.POST.get("username")
            password = request.POST.get("password")
            user = authenticate(request, username=username, password=password)

            if user is not None:
                # Verifica si el usuario está aprobado
                if user.is_approved:
                    # Verifica si la confirmación del correo es opcional o requerida
                    if user.email_confirmed or not settings.EMAIL_CONFIRMATION_REQUIRED:
                        login(request, user)
                        return redirect('home')  # Redirige a la página principal si el inicio de sesión es exitoso
                    else:
                        return render(request, 'login.html', {'error': 'Su cuenta no ha sido confirmada.'})
                else:
                    return render(request, 'login.html', {'error': 'Su cuenta no ha sido aprobada.'})
            else:
                return render(request, 'login.html', {'error': 'Nombre de usuario o contraseña incorrectos.'})

    return render(request, 'login.html')


def pending_approval_view (request):
    return render (request, 'pending_approval.html')


@login_required
def index(request):
    return render(request, "index.html")

@login_required
def update_file(request):
    return render(request, "update_file.html")

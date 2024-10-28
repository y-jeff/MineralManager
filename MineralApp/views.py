from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.decorators import login_required
from .forms import UploadFileForm
from .models import CustomUser, Trabajador, Capacitacion, Asistencia, CapacitacionTrabajador
import pandas as pd
import os

def login_signup_view(request):
    if request.method == "POST":
        if 'confirm_password' in request.POST:
            # Registro de usuario
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
            # Inicio de sesión
            username = request.POST.get("username")
            password = request.POST.get("password")
            user = authenticate(request, username=username, password=password)

            if user is not None:
                if user.is_approved:
                    if user.email_confirmed or not settings.EMAIL_CONFIRMATION_REQUIRED:
                        login(request, user)
                        return redirect('home')
                    else:
                        return render(request, 'login.html', {'error': 'Su cuenta no ha sido confirmada.'})
                else:
                    return render(request, 'login.html', {'error': 'Su cuenta no ha sido aprobada.'})
            else:
                return render(request, 'login.html', {'error': 'Nombre de usuario o contraseña incorrectos.'})

    return render(request, 'login.html')

def pending_approval_view(request):
    return render(request, 'pending_approval.html')

# Función para manejar la subida de archivos
def handle_uploaded_file(f):
    upload_dir = 'uploads/'
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, f.name)
    with open(file_path, 'wb+') as destination:
        for chunk in f.chunks():
            destination.write(chunk)
    return file_path

# Vista para manejar el formulario de carga de archivos y procesar el archivo
@login_required
def upload_file(request):
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            file_path = handle_uploaded_file(request.FILES['file'])
            process_excel(file_path)
            return redirect('upload_success')  # Redirige a la vista de éxito después de la subida
    else:
        form = UploadFileForm()
    return render(request, 'upload.html', {'form': form})

# Función para procesar el archivo Excel
def process_excel(file_path):
    df = pd.read_excel(file_path)

    # Procesar las filas y guardar en el modelo correspondiente
    for index, row in df.iterrows():
        trabajador, created = Trabajador.objects.update_or_create(
            rut=row['RUT'], 
            defaults={
                'nombre_trabajador': row['Nombre'],
                'area_id': row['Area'],
                'cargo_id': row['Cargo'],
                'horas_esperadas_totales': row['Horas']
            }
        )

        # Ejemplo para asignación de capacitaciones
        if 'Capacitacion' in row:
            capacitacion, _ = Capacitacion.objects.get_or_create(nombre_capacitacion=row['Capacitacion'])
            CapacitacionTrabajador.objects.update_or_create(
                trabajador=trabajador,
                capacitacion=capacitacion,
                defaults={'fecha_de_capacitacion': row['FechaCapacitacion']}
            )
            
@login_required
def upload_success(request):
    return render(request, 'upload_success.html')

@login_required
def index(request):
    return render(request, "index.html")

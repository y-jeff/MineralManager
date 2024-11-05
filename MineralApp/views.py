import os
import pandas as pd
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.decorators import login_required
from .forms import UploadFileForm
from .models import (
    CustomUser, Trabajador, Capacitacion, Asistencia, CapacitacionTrabajador, 
    Area, CargoTrabajador, InventarioArticuloBodega, Bodega, Articulo, Panol, 
    RetiroArticulo, Maquinaria, MantenimientoMaquinaria, RetiroMaquinaria,
    HorarioTrabajo, JornadaTrabajador, TurnoTrabajador, Categoria, RegistroEntrega
)

# Vista para la página de inicio
@login_required
def index(request):
    return render(request, "index.html")

# Vista para registro e inicio de sesión
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
                        # Redirigir al admin o al home según el tipo de usuario
                        if user.is_superuser:
                            return redirect('/admin/')  # Redirige al área de admin
                        else:
                            return redirect('home')  # Redirige al área de usuario regular
                    else:
                        return render(request, 'login.html', {'error': 'Su cuenta no ha sido confirmada.'})
                else:
                    return render(request, 'login.html', {'error': 'Su cuenta no ha sido aprobada.'})
            else:
                return render(request, 'login.html', {'error': 'Nombre de usuario o contraseña incorrectos.'})

    return render(request, 'login.html')

# Vista para mostrar página de espera de aprobación de cuenta
def pending_approval_view(request):
    return render(request, 'pending_approval.html')

# Función para manejar la subida de archivos y guardarlos en el sistema de archivos
def handle_uploaded_file(f):
    upload_dir = 'uploads/'
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, f.name)
    with open(file_path, 'wb+') as destination:
        for chunk in f.chunks():
            destination.write(chunk)
    return file_path

# Redirección a la página de inicio
def redirect_to_home(request):
    return redirect('/')

# Vista para manejar el formulario de carga de archivos y procesar el archivo
@login_required
def upload_file(request):
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            file_path = handle_uploaded_file(request.FILES['file'])
            process_excel(file_path)
            return redirect('upload_success')
    else:
        form = UploadFileForm()
    return render(request, 'upload.html', {'form': form})

# Vista para mostrar el mensaje de éxito después de la carga de archivos
@login_required
def upload_success(request):
    return render(request, 'upload_success.html')

# Función para procesar el archivo Excel y cargar datos en los modelos
def process_excel(file_path):
    excel_data = pd.ExcelFile(file_path)

    # Procesar la hoja "Trabajadores"
    if "Trabajadores" in excel_data.sheet_names:
        trabajadores_df = excel_data.parse("Trabajadores")
        for _, row in trabajadores_df.iterrows():
            jornada, _ = JornadaTrabajador.objects.get_or_create(tipo_jornada=row.get("Jornada", "Completa"))
            turno, _ = TurnoTrabajador.objects.get_or_create(tipo_turno=row.get("Turno", "Diurno"))
            horario, _ = HorarioTrabajo.objects.get_or_create(jornada_trabajador=jornada, turno_trabajador=turno)
            
            area, _ = Area.objects.get_or_create(nombre_area=row.get("Área", "Sin área"))
            cargo, _ = CargoTrabajador.objects.get_or_create(nombre_cargo=row.get("Cargo", "Sin cargo"))
            
            Trabajador.objects.update_or_create(
                rut=row['RUT'],
                defaults={
                    'nombre_trabajador': row.get('Nombre', 'Desconocido'),
                    'area': area,
                    'cargo': cargo,
                    'horario': horario,
                    'horas_esperadas_totales': row.get('Horas Esperadas', 0)
                }
            )

    # Procesar la hoja "Capacitaciones"
    if "Capacitaciones" in excel_data.sheet_names:
        capacitaciones_df = excel_data.parse("Capacitaciones")
        for _, row in capacitaciones_df.iterrows():
            trabajador = Trabajador.objects.get(rut=row['RUT'])
            capacitacion, _ = Capacitacion.objects.get_or_create(
                nombre_capacitacion=row['Nombre de la Capacitación'],
                defaults={
                    'fecha_inicio': row['Fecha de Inicio'],
                    'fecha_fin': row['Fecha de Fin'],
                    'es_renovable': row['Renovación Requerida'] == 'Sí'
                }
            )
            CapacitacionTrabajador.objects.update_or_create(
                trabajador=trabajador,
                capacitacion=capacitacion,
                defaults={'fecha_de_capacitacion': row['Fecha de Inicio']}
            )

    # Procesar la hoja "Inventario Artículos Bodega"
    if "Inventario Artículos Bodega" in excel_data.sheet_names:
        inventario_df = excel_data.parse("Inventario Artículos Bodega")
        
        for _, row in inventario_df.iterrows():
            categoria, _ = Categoria.objects.get_or_create(nombre_categoria_item=row.get("Categoría", "General"))
            articulo, _ = Articulo.objects.get_or_create(
                nombre_articulo=row['Artículo'],
                defaults={
                    'categoria': categoria,
                    'descripcion_articulo': row.get('Descripción', 'No especificada')
                }
            )
            bodega, _ = Bodega.objects.get_or_create(nombre_bodega=row.get("Bodega", "Principal"))
            
            InventarioArticuloBodega.objects.update_or_create(
                articulo=articulo,
                bodega=bodega,
                defaults={
                    'cantidad_articulos': row.get('Cantidad Artículos', 0),
                    'en_bodega': row.get('En Bodega', 'No') == 'Sí'
                }
            )

    # Procesar la hoja "Pañol"
    if "Pañol" in excel_data.sheet_names:
        panol_df = excel_data.parse("Pañol")
        for _, row in panol_df.iterrows():
            trabajador = Trabajador.objects.get(rut=row['RUT'])
            articulo, _ = Articulo.objects.get_or_create(nombre_articulo=row['Artículo'])
            panol, _ = Panol.objects.get_or_create(nombre_panol="Pañol Central")
            RetiroArticulo.objects.update_or_create(
                trabajador=trabajador,
                articulo=articulo,
                defaults={
                    'cantidad_retirada': row['Cantidad Retirada'],
                    'fecha_retiro_articulo': row['Fecha de Retiro'],
                    'motivo_retiro_articulo': row['Motivo']
                }
            )

    # Procesar la hoja "Maquinarias"
    if "Maquinarias" in excel_data.sheet_names:
        maquinarias_df = excel_data.parse("Maquinarias")
        for _, row in maquinarias_df.iterrows():
            Maquinaria.objects.update_or_create(
                nombre_maquinaria=row['Maquinaria'],
                defaults={
                    'fecha_adquisicion': row['Fecha de Adquisición'],
                    'estado': row['Estado']
                }
            )

    # Procesar la hoja "Mantenimiento Maquinaria"
    if "Mantenimiento Maquinaria" in excel_data.sheet_names:
        mantenimiento_df = excel_data.parse("Mantenimiento Maquinaria")
        for _, row in mantenimiento_df.iterrows():
            maquinaria = Maquinaria.objects.get(nombre_maquinaria=row['Maquinaria'])
            MantenimientoMaquinaria.objects.update_or_create(
                maquinaria=maquinaria,
                fecha_mantenimiento=row['Fecha de Mantenimiento'],
                defaults={
                    'descripcion': row['Descripción'],
                    'realizado_por': row['Realizado por']
                }
            )

    # Procesar la hoja "Retiro Maquinaria"
    if "Retiro Maquinaria" in excel_data.sheet_names:
        retiro_df = excel_data.parse("Retiro Maquinaria")
        for _, row in retiro_df.iterrows():
            maquinaria = Maquinaria.objects.get(nombre_maquinaria=row['Maquinaria'])
            RetiroMaquinaria.objects.update_or_create(
                maquinaria=maquinaria,
                fecha_retiro=row['Fecha de Retiro'],
                defaults={'motivo': row['Motivo']}
            )

from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.conf import settings
import csv
from .models import (
    CustomUser, Trabajador, Area, Cargo, Horario, Jornada, Turno,
    Capacitacion, CapacitacionTrabajador, Panol, Bodega,
    ArticuloPanol, ArticuloBodega, Maquinaria, MantenimientoMaquinaria, MovimientoArticulo
)
from datetime import datetime
from django.core.exceptions import ValidationError

# Vista para inicio de sesión
def login_signup_view(request):
    if request.method == "POST":
        if 'confirm_password' not in request.POST:
            username = request.POST.get("username")
            password = request.POST.get("password")
            user = authenticate(request, username=username, password=password)

            if user is not None:
                if user.email_confirmed or not settings.EMAIL_CONFIRMATION_REQUIRED:
                    login(request, user)
                    if user.is_superuser:
                        return redirect('/admin/')
                    else:
                        return redirect('home')
                else:
                    return render(request, 'login.html', {'error': 'Su cuenta no ha sido confirmada.'})
            else:
                return render(request, 'login.html', {'error': 'Nombre de usuario o contraseña incorrectos.'})
    return render(request, 'login.html')


# Página Principal
@login_required
def index(request):
    return render(request, 'index.html')


# Vista de carga de CSV
@login_required
def upload_csv(request):
    if request.method == 'POST':
        files = request.FILES.getlist('file')

        # Procesa Trabajadores.csv primero
        for file in files:
            if file.name == 'Trabajadores.csv':
                handle_trabajadores_csv(file)

        # Luego procesa los otros archivos
        for file in files:
            if file.name == 'Capacitaciones.csv':
                handle_capacitaciones_csv(file)
            elif file.name == 'Inventario_Panol.csv':
                handle_articulo_panol_csv(file)
            elif file.name == 'Inventario_Bodega.csv':
                handle_articulo_bodega_csv(file)
            elif file.name == 'Maquinarias.csv':
                handle_maquinarias_csv(file)
            elif file.name == 'Mantenimiento_Maquinaria.csv':
                handle_mantenimientos_csv(file)
            elif file.name == 'Movimientos.csv':
                handle_movimientos_csv(file)

        return redirect('upload_success')
    return render(request, 'upload.html')


# Página de éxito de carga
@login_required
def upload_success(request):
    return render(request, 'upload_success.html', {'message': 'Archivos subidos correctamente.'})


# Funciones para procesar cada CSV
def handle_trabajadores_csv(file):
    reader = csv.DictReader(file.read().decode('utf-8').splitlines())
    for row in reader:
        area, _ = Area.objects.get_or_create(nombre_area=row['Area'])
        cargo, _ = Cargo.objects.get_or_create(nombre_cargo=row['Cargo'])
        jornada, _ = Jornada.objects.get_or_create(tipo_jornada=row['Jornada'])
        turno, _ = Turno.objects.get_or_create(tipo_turno=row['Turno'])
        horario, _ = Horario.objects.get_or_create(ciclo=row['Ciclo'])
        Trabajador.objects.update_or_create(
            rut=row['RUT'],
            defaults={
                'nombre_trabajador': row['Nombre'],
                'area': area,
                'cargo': cargo,
                'jornada': jornada,
                'turno': turno,
                'horario': horario,
                'horas_esperadas_totales': row['Horas']
            }
        )


def handle_capacitaciones_csv(file):
    reader = csv.DictReader(file.read().decode('utf-8').splitlines())
    for row in reader:
        try:
            trabajador = Trabajador.objects.get(rut=row['RUT'])
            capacitacion, _ = Capacitacion.objects.get_or_create(
                nombre_capacitacion=row['Capacitacion'],
                es_renovable=(row.get('Renovable', 'No') == 'Sí')
            )
            fecha_inicio = parse_date(row.get('Fecha Inicio'))
            fecha_fin = parse_date(row.get('Fecha Fin'))

            CapacitacionTrabajador.objects.update_or_create(
                trabajador=trabajador,
                capacitacion=capacitacion,
                defaults={
                    'fecha_inicio': fecha_inicio,
                    'fecha_fin': fecha_fin
                }
            )
        except Trabajador.DoesNotExist:
            print(f"Error: Trabajador con RUT {row['RUT']} no encontrado.")
        except ValidationError as e:
            print(f"Error de validación: {e}")


def handle_articulo_panol_csv(file):
    reader = csv.DictReader(file.read().decode('utf-8').splitlines())
    for row in reader:
        panol, _ = Panol.objects.get_or_create(nombre_panol=row['Pañol'])
        ArticuloPanol.objects.update_or_create(
            panol=panol,
            nombre_articulo=row['Nombre Articulo'],
            defaults={
                'descripcion_articulo': row['Descripción'],
                'cantidad': row['Cantidad']
            }
        )


def handle_articulo_bodega_csv(file):
    reader = csv.DictReader(file.read().decode('utf-8').splitlines())
    for row in reader:
        bodega, _ = Bodega.objects.get_or_create(nombre_bodega=row['Bodega'])
        ArticuloBodega.objects.update_or_create(
            bodega=bodega,
            nombre_articulo=row['Nombre Articulo'],
            defaults={
                'descripcion_articulo': row['Descripción'],
                'cantidad': row['Cantidad']
            }
        )


def handle_maquinarias_csv(file):
    reader = csv.DictReader(file.read().decode('utf-8').splitlines())
    for row in reader:
        area, _ = Area.objects.get_or_create(nombre_area=row['Area'])
        Maquinaria.objects.update_or_create(
            codigo_maquinaria=row['Código'],
            defaults={
                'nombre_maquinaria': row['Nombre Maquinaria'],
                'fecha_adquisicion': parse_date(row['Fecha Adquisición']),
                'estado': row['Estado'],
                'area': area
            }
        )


def handle_mantenimientos_csv(file):
    reader = csv.DictReader(file.read().decode('utf-8').splitlines())
    for row in reader:
        try:
            maquinaria = Maquinaria.objects.get(codigo_maquinaria=row['Código'])
            MantenimientoMaquinaria.objects.update_or_create(
                maquinaria=maquinaria,
                fecha_mantenimiento=parse_date(row['Fecha Mantenimiento']),
                defaults={
                    'descripcion': row['Descripción'],
                    'realizado_por': row['Realizado Por']
                }
            )
        except Maquinaria.DoesNotExist:
            print(f"Error: Maquinaria con código {row['Código']} no encontrada.")


def handle_movimientos_csv(file):
    reader = csv.DictReader(file.read().decode('utf-8').splitlines())
    for row in reader:
        try:
            articulo = ArticuloBodega.objects.get(nombre_articulo=row['Nombre Articulo'])
            origen = Bodega.objects.get(nombre_bodega=row['Bodega Origen'])
            destino = Panol.objects.get(nombre_panol=row['Pañol Destino'])
            fecha_movimiento = parse_date(row['Fecha Movimiento'], default_today=True)

            MovimientoArticulo.objects.create(
                articulo=articulo,
                origen=origen,
                destino=destino,
                cantidad=int(row['Cantidad']),
                fecha_movimiento=fecha_movimiento,
                motivo=row.get('Motivo', '')
            )
        except (ArticuloBodega.DoesNotExist, Bodega.DoesNotExist, Panol.DoesNotExist) as e:
            print(f"Error: {e}")


# Helper function to parse dates and handle empty values
def parse_date(date_str, default_today=False):
    if date_str:
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            raise ValidationError(f"Fecha inválida: {date_str}")
    return datetime.today().date() if default_today else None


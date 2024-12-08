# Módulos estándar de Python
import base64
import csv
import io
import json
import re
from datetime import date, datetime, timedelta
from itertools import chain

# Django - Configuración y utilidades
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db.models import Case, Count, F, IntegerField, Q, Sum, When
from django.http import FileResponse, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from datetime import datetime, timedelta
from django.utils.timezone import localtime, now, timezone
from django.views.decorators.csrf import csrf_exempt
# Django - Herramientas adicionales
from django.http import HttpResponseForbidden

# Bibliotecas de terceros
import matplotlib.pyplot as plt
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, SimpleDocTemplate, Table, TableStyle
from io import BytesIO

# Módulos del proyecto
from .forms import (
    ArticuloBodegaForm, ArticuloPanolForm, CapacitacionForm,
    CapacitacionTrabajadorForm, CapacitacionTrabajadorFormSet,
    MovimientoArticuloForm, ProductoForm, RetiroArticuloForm, TrabajadorForm
)
from .models import (
    Area, ArticuloBodega, ArticuloPanol, Bodega, Capacitacion,
    CapacitacionTrabajador, Cargo, CustomUser, Horario, Jornada,
    Maquinaria, MantenimientoMaquinaria, MovimientoArticulo,
    Panol, RegistroHoras, RetiroArticulo, Trabajador, Turno
)


# Vista para inicio de sesión y redirección si ya está autenticado
def login_signup_view(request):
    # Si el usuario ya está autenticado, redirige al home
    if request.user.is_authenticated:
        return redirect('home')

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
    total_trabajadores = Trabajador.objects.filter(activo=True).count()
    stock_bajo_panol = ArticuloPanol.objects.filter(cantidad__lte=10).count()
    stock_bajo_bodega = ArticuloBodega.objects.filter(cantidad__lte=10).count()
    certificaciones_proximas_qs = CapacitacionTrabajador.objects.filter(
        fecha_fin__lte=now() + timedelta(days=90),
        fecha_fin__gte=now(),
        trabajador__activo=True
    ).select_related('trabajador', 'capacitacion')

    certificaciones_data = [
        {
            "trabajador": cert.trabajador,
            "capacitacion": cert.capacitacion,
            "fecha_fin": cert.fecha_fin,
            "dias_restantes": (cert.fecha_fin - now().date()).days,
        }
        for cert in certificaciones_proximas_qs
    ]

    maquinaria_mantenimiento = Maquinaria.objects.filter(estado="mantenimiento").count()
    maquinaria_inactiva = Maquinaria.objects.filter(estado="inactivo").count()

    context = {
        "total_trabajadores": total_trabajadores,
        "stock_bajo_panol": stock_bajo_panol,
        "stock_bajo_bodega": stock_bajo_bodega,
        "certificaciones_proximas": len(certificaciones_data),
        "certificaciones_data": certificaciones_data,
        "maquinaria_mantenimiento": maquinaria_mantenimiento,
        "maquinaria_inactiva": maquinaria_inactiva,
    }

    return render(request, "index.html", context)

#Vistas para subir archivo
# Procesa Trabajadores.csv
def handle_trabajadores_csv(file):
    decoded_file = file.read().decode('utf-8').splitlines()
    reader = csv.DictReader(decoded_file)
    for row in reader:
        area, _ = Area.objects.get_or_create(nombre_area=row['Area'])
        cargo, _ = Cargo.objects.get_or_create(nombre_cargo=row['Cargo'])
        jornada, _ = Jornada.objects.get_or_create(tipo_jornada=row['Jornada'])
        turno, _ = Turno.objects.get_or_create(tipo_turno=row['Turno'])
        horario, _ = Horario.objects.get_or_create(ciclo=row['Ciclo'])

        trabajador, created = Trabajador.objects.update_or_create(
            rut=row['RUT'],
            defaults={
                'nombre_trabajador': row['Nombre'],
                'area': area,
                'cargo': cargo,
                'jornada': jornada,
                'turno': turno,
                'horario': horario,
            }
        )

        if created or not RegistroHoras.objects.filter(trabajador=trabajador).exists():
            RegistroHoras.objects.create(
                trabajador=trabajador,
                area=area,
                horas_esperadas=int(row.get('Horas', 40)),
                horas_trabajadas=int(row.get('Horas Trabajadas', 0)),
                fecha_registro=timezone.now()
            )


# Procesa Capacitaciones.csv
def handle_capacitaciones_csv(file):
    """
    Procesa el archivo Capacitaciones.csv y actualiza o crea registros únicos por combinación de trabajador y capacitación.
    """
    decoded_file = file.read().decode('utf-8').splitlines()
    reader = csv.DictReader(decoded_file)
    for row in reader:
        trabajador = Trabajador.objects.filter(rut=row['RUT']).first()
        if trabajador:
            capacitacion, _ = Capacitacion.objects.get_or_create(nombre_capacitacion=row['Capacitacion'])
            CapacitacionTrabajador.objects.update_or_create(
                trabajador=trabajador,
                capacitacion=capacitacion,
                defaults={
                    'fecha_inicio': row['Fecha Inicio'],
                    'fecha_fin': row['Fecha Fin'] if row['Fecha Fin'] else None,
                }
            )

# Procesa Inventario_Panol.csv
def handle_articulo_panol_csv(file):
    """
    Procesa el archivo Inventario_Panol.csv y actualiza o crea registros únicos basados en nombre_articulo y pañol.
    """
    decoded_file = file.read().decode('utf-8').splitlines()
    reader = csv.DictReader(decoded_file)
    for row in reader:
        panol, _ = Panol.objects.get_or_create(nombre_panol=row['Pañol'])
        ArticuloPanol.objects.update_or_create(
            nombre_articulo=row['Nombre Articulo'],
            panol=panol,
            defaults={
                'descripcion_articulo': row['Descripción'],
                'cantidad': int(row['Cantidad']),
            }
        )

# Procesa Inventario_Bodega.csv
def handle_articulo_bodega_csv(file):
    """
    Procesa el archivo Inventario_Bodega.csv y actualiza o crea registros únicos basados en nombre_articulo y bodega.
    """
    decoded_file = file.read().decode('utf-8').splitlines()
    reader = csv.DictReader(decoded_file)
    for row in reader:
        bodega, _ = Bodega.objects.get_or_create(nombre_bodega=row['Bodega'])
        ArticuloBodega.objects.update_or_create(
            nombre_articulo=row['Nombre Articulo'],
            bodega=bodega,
            defaults={
                'descripcion_articulo': row['Descripción'],
                'cantidad': int(row['Cantidad']),
            }
        )

# Procesa Maquinarias.csv
def handle_maquinarias_csv(file):
    """
    Procesa el archivo Maquinarias.csv y actualiza o crea registros únicos basados en el código de maquinaria.
    """
    decoded_file = file.read().decode('utf-8').splitlines()
    reader = csv.DictReader(decoded_file)
    for row in reader:
        # Obtén o crea el área asociada
        area, _ = Area.objects.get_or_create(nombre_area=row['Area'])
        
        # Actualiza o crea la maquinaria con horas esperadas
        Maquinaria.objects.update_or_create(
            codigo_maquinaria=row['Código'],  # Identificador único
            defaults={
                'nombre_maquinaria': row['Nombre Maquinaria'],
                'fecha_adquisicion': row['Fecha Adquisición'],
                'estado': row['Estado'],
                'area': area,
                'horas_esperadas': int(row['Horas Esperadas']),
            }
        )

# Procesa Mantenimiento_Maquinaria.csv
def handle_mantenimientos_csv(file):
    """
    Procesa el archivo Mantenimiento_Maquinaria.csv y actualiza o crea registros únicos basados en maquinaria y fecha de mantenimiento.
    """
    decoded_file = file.read().decode('utf-8').splitlines()
    reader = csv.DictReader(decoded_file)
    for row in reader:
        maquinaria = Maquinaria.objects.filter(codigo_maquinaria=row['Código']).first()
        if maquinaria:
            MantenimientoMaquinaria.objects.update_or_create(
                maquinaria=maquinaria,
                fecha_mantenimiento=row['Fecha Mantenimiento'],  # Identificador único
                defaults={
                    'descripcion': row['Descripción'],
                    'realizado_por': row['Realizado Por'],
                }
            )

# Procesa Movimientos.csv
def handle_movimientos_csv(file):
    """
    Procesa el archivo Movimientos.csv y actualiza o crea registros únicos basados en artículo, origen y destino.
    """
    decoded_file = file.read().decode('utf-8').splitlines()
    reader = csv.DictReader(decoded_file)
    for row in reader:
        articulo = ArticuloBodega.objects.filter(nombre_articulo=row['Nombre Articulo']).first()
        if articulo:
            origen, _ = Bodega.objects.get_or_create(nombre_bodega=row['Bodega Origen'])
            destino, _ = Panol.objects.get_or_create(nombre_panol=row['Pañol Destino'])
            MovimientoArticulo.objects.update_or_create(
                articulo=articulo,
                origen=origen,
                destino=destino,
                defaults={
                    'cantidad': int(row['Cantidad']),
                    'fecha_movimiento': row['Fecha Movimiento'],
                    'motivo': row['Motivo'] if 'Motivo' in row else None,
                }
            )

# Procesa Horas Trabajadas - Trabajadores
def procesar_csv_trabajadores(reader):
    """
    Procesa un archivo CSV para registrar las horas trabajadas de los trabajadores.
    """
    for row in reader:
        # Busca el trabajador basado en el RUT
        trabajador = Trabajador.objects.filter(rut=row['RUT']).first()

        if trabajador:
            # Crear el registro de horas
            RegistroHoras.objects.create(
                tipo='trabajador',
                trabajador=trabajador,
                area=trabajador.area,  # Se asume que el trabajador tiene un área asociada
                horas_trabajadas=int(row['Horas Trabajadas']),
                fecha_registro=row['Fecha']  # El CSV debe incluir un campo de fecha
            )
        else:
            print(f"Trabajador con RUT {row['RUT']} no encontrado.")

# Procesa Horas Trabajadas - Maquinarias

def procesar_csv_maquinarias(reader):
    """
    Procesa un archivo CSV para registrar las horas trabajadas de las maquinarias.
    """
    for row in reader:
        # Busca la maquinaria basada en el código
        maquinaria = Maquinaria.objects.filter(codigo_maquinaria=row['Código']).first()

        if maquinaria:
            # Verifica si la columna `Fecha` existe en el archivo
            fecha_registro = row.get('Fecha', date.today())  # Usa la fecha actual si no está en el CSV

            RegistroHoras.objects.create(
                tipo='maquinaria',
                maquinaria=maquinaria,
                area=maquinaria.area,  # Se asume que la maquinaria tiene un área asociada
                horas_trabajadas=int(row['Horas Trabajadas']),
                fecha_registro=fecha_registro
            )
        else:
            print(f"Maquinaria con código {row['Código']} no encontrada.")

def handle_despidos_csv(file):
    """
    Procesa un archivo CSV para activar/desactivar trabajadores masivamente.
    El CSV debe tener columnas 'RUT' y 'Activo' (True/False).
    """
    decoded_file = file.read().decode('utf-8').splitlines()
    reader = csv.DictReader(decoded_file)

    rut_no_encontrados = []  # Lista para rastrear RUTs no encontrados

    for row in reader:
        rut = row.get('RUT')  # Obtiene el RUT
        estado = row.get('Activo', 'False').strip().lower() == 'true'  # Convierte 'Activo' a booleano

        if not rut:
            continue  # Salta filas sin RUT

        try:
            trabajador = Trabajador.objects.get(rut=rut)
            trabajador.activo = estado  # Cambia el estado del atributo 'activo'
            trabajador.save()  # Guarda los cambios
        except Trabajador.DoesNotExist:
            rut_no_encontrados.append(rut)  # Agrega el RUT no encontrado a la lista

    return rut_no_encontrados  # Retorna los RUTs no encontrados para notificar al usuario



# Página de carga de archivos          
@login_required
def upload_csv(request):
    if request.method == 'POST':
        files = request.FILES.getlist('file')  # Soporte para múltiples archivos

        for file in files:
            try:
                # Verifica si es un archivo CSV
                if not file.name.endswith('.csv'):
                    messages.error(request, f"{file.name} no es un archivo CSV válido.")
                    continue

                # Lee el contenido del archivo
                decoded_file = file.read().decode('utf-8').splitlines()
                reader = csv.DictReader(decoded_file)

                # Verifica si tiene columnas requeridas
                if file.name == 'Trabajadores.csv':
                    required_columns = ['RUT', 'Nombre', 'Area', 'Horas']
                    if not all(col in reader.fieldnames for col in required_columns):
                        messages.error(request, f"{file.name} no contiene las columnas requeridas: {required_columns}.")
                        continue
                    handle_trabajadores_csv(file)
                    messages.success(request, f"{file.name}: Datos de trabajadores procesados.")

                elif file.name == 'Maquinarias.csv':
                    required_columns = ['Código', 'Horas Trabajadas', 'Fecha']
                    if not all(col in reader.fieldnames for col in required_columns):
                        messages.error(request, f"{file.name} no contiene las columnas requeridas: {required_columns}.")
                        continue
                    procesar_csv_maquinarias(reader)
                    messages.success(request, f"{file.name}: Horas de maquinarias procesadas.")

                elif file.name == 'Capacitaciones.csv':
                    required_columns = ['RUT', 'Capacitacion', 'Fecha Inicio']
                    if not all(col in reader.fieldnames for col in required_columns):
                        messages.error(request, f"{file.name} no contiene las columnas requeridas: {required_columns}.")
                        continue
                    handle_capacitaciones_csv(file)
                    messages.success(request, f"{file.name}: Datos de capacitaciones procesados.")

                elif file.name == 'Inventario_Panol.csv':
                    handle_articulo_panol_csv(file)
                    messages.success(request, f"{file.name}: Datos de inventario de pañol procesados.")

                elif file.name == 'Inventario_Bodega.csv':
                    handle_articulo_bodega_csv(file)
                    messages.success(request, f"{file.name}: Datos de inventario de bodega procesados.")

                elif file.name == 'Mantenimiento_Maquinaria.csv':
                    handle_mantenimientos_csv(file)
                    messages.success(request, f"{file.name}: Datos de mantenimientos procesados.")

                elif file.name == 'Movimientos.csv':
                    handle_movimientos_csv(file)
                    messages.success(request, f"{file.name}: Datos de movimientos procesados.")

                elif file.name == 'Despidos.csv':
                    required_columns = ['RUT', 'Activo']
                    if not all(col in reader.fieldnames for col in required_columns):
                        messages.error(request, f"{file.name} no contiene las columnas requeridas: {required_columns}.")
                        continue
                    
                    # Procesa despidos masivos
                    rut_no_encontrados = handle_despidos_csv(file)
                    
                    if rut_no_encontrados:
                        messages.warning(request, f"Los siguientes RUT no fueron encontrados: {', '.join(rut_no_encontrados)}.")
                    else:
                        messages.success(request, f"{file.name}: Todos los trabajadores han sido procesados correctamente.")

                else:
                    messages.error(request, f"{file.name}: El archivo no es reconocido.")

            except Exception as e:
                messages.error(request, f"Ocurrió un error procesando {file.name}: {e}")

        return redirect('upload_success')  # Redirige a la página de éxito

    return render(request, 'upload.html')  # Renderiza la página de subida


# Página de éxito de carga
@login_required
def upload_success(request):
    return render(request, 'upload_success.html', {'message': 'Archivos subidos correctamente.'})


# Vista de Pañol
@login_required
def panol_view(request):
    search_query = request.GET.get('q', '')
    ubicacion_id = request.GET.get('ubicacion', '')
    cantidad_filtro = request.GET.get('cantidad_filtro', '')

    articulos = ArticuloPanol.objects.all()

    # Filtro por búsqueda
    if search_query:
        articulos = articulos.filter(
            Q(nombre_articulo__icontains=search_query) |
            Q(descripcion_articulo__icontains=search_query)
        )

    # Filtro por ubicación
    if ubicacion_id:
        articulos = articulos.filter(panol__id=ubicacion_id)

    # Filtro por cantidad
    if cantidad_filtro == 'bajo':
        articulos = articulos.filter(cantidad__lte=10, cantidad__gt=0)
    elif cantidad_filtro == 'agotado':
        articulos = articulos.filter(cantidad=0)

    # Procesar la creación de un artículo
    if request.method == 'POST' and 'crear' in request.POST:
        create_form = ArticuloPanolForm(request.POST)
        if create_form.is_valid():
            create_form.save()
            messages.success(request, "Artículo agregado exitosamente.")
            return redirect('pañol')
        else:
            print("Errores en el formulario de creación:", create_form.errors)
    else:
        create_form = ArticuloPanolForm()

    # Procesar la edición de un artículo
    if 'editar_id' in request.GET:
        articulo_editar = get_object_or_404(ArticuloPanol, id=request.GET['editar_id'])
        edit_form = ArticuloPanolForm(request.POST or None, instance=articulo_editar)
        
        if request.method == 'POST' and 'editar' in request.POST:
            if edit_form.is_valid():
                edit_form.save()
                messages.success(request, "Artículo editado exitosamente.")
                return redirect('pañol')
            else:
                print("Errores en el formulario de edición:", edit_form.errors)
    else:
        edit_form = None

    # Procesar la eliminación de un artículo
    if 'eliminar_id' in request.GET:
        articulo_eliminar = get_object_or_404(ArticuloPanol, id=request.GET['eliminar_id'])
        if request.method == 'POST' and 'eliminar' in request.POST:
            articulo_eliminar.delete()
            messages.success(request, "Artículo eliminado exitosamente.")
            return redirect('pañol')

    advertencias = ArticuloPanol.objects.filter(cantidad__lte=10)
    panoles = Panol.objects.all()

    context = {
        'articulos': articulos,
        'panoles': panoles,
        'search_query': search_query,
        'ubicacion_id': ubicacion_id,
        'cantidad_filtro': cantidad_filtro,
        'advertencias': advertencias,
        'create_form': create_form,  # Formulario de creación separado
        'edit_form': edit_form,
    }

    return render(request, 'panol.html', context)

@login_required
def descargar_informe_pañol(request):
    # Filtrar artículos con cantidad baja o agotada
    articulos_bajos = ArticuloPanol.objects.filter(cantidad__lte=10)

    # Configuración del PDF en orientación horizontal
    buffer = BytesIO()
    pdf = SimpleDocTemplate(buffer, pagesize=landscape(letter))
    elements = []

    # Encabezado de la tabla
    data = [
        ["Nombre", "Descripción", "Cantidad", "Ubicación"]
    ]

    # Estilo de la tabla con mayor espacio entre celdas y mejor apariencia
    table_style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('TOPPADDING', (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ])

    # Agregar datos de cada artículo
    for articulo in articulos_bajos:
        data.append([
            articulo.nombre_articulo,
            articulo.descripcion_articulo,
            articulo.cantidad,
            articulo.panol.nombre_panol
        ])

    # Crear la tabla y definir el ancho de columnas
    table = Table(data, colWidths=[1*inch, 2*inch, 3*inch, 1*inch, 1.5*inch])
    table.setStyle(table_style)
    elements.append(table)

    # Construcción del PDF
    pdf.build(elements)
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="informe_articulos_bajos.pdf"'
    return response

# Vista de Bodega

@login_required
def bodega_view(request):
    search_query = request.GET.get('q', '')
    ubicacion_id = request.GET.get('ubicacion', '')
    cantidad_filtro = request.GET.get('cantidad_filtro', '')

    # Obtener todos los artículos en bodega
    articulos = ArticuloBodega.objects.all()

    # Filtrar por búsqueda
    if search_query:
        articulos = articulos.filter(
            Q(nombre_articulo__icontains=search_query) |
            Q(descripcion_articulo__icontains=search_query)
        )

    # Filtrar por ubicación
    if ubicacion_id:
        articulos = articulos.filter(bodega__id=ubicacion_id)

    # Filtrar por cantidad
    if cantidad_filtro == 'bajo':
        articulos = articulos.filter(cantidad__lte=10, cantidad__gt=0)
    elif cantidad_filtro == 'agotado':
        articulos = articulos.filter(cantidad=0)

    # Procesar la creación de un artículo
    if request.method == 'POST' and 'crear' in request.POST:
        create_form = ArticuloBodegaForm(request.POST)
        if create_form.is_valid():
            create_form.save()
            messages.success(request, "Artículo agregado exitosamente en la bodega.")
            return redirect('bodega')
        else:
            print("Errores en el formulario de creación:", create_form.errors)
    else:
        create_form = ArticuloBodegaForm()

    # Procesar la edición de un artículo
    if 'editar_id' in request.GET:
        articulo_editar = get_object_or_404(ArticuloBodega, id=request.GET['editar_id'])
        edit_form = ArticuloBodegaForm(request.POST or None, instance=articulo_editar)
        
        if request.method == 'POST' and 'editar' in request.POST:
            if edit_form.is_valid():
                edit_form.save()
                messages.success(request, "Artículo editado exitosamente.")
                return redirect('bodega')
            else:
                print("Errores en el formulario de edición:", edit_form.errors)
    else:
        edit_form = None

    # Procesar la eliminación de un artículo
    if 'eliminar_id' in request.GET:
        articulo_eliminar = get_object_or_404(ArticuloBodega, id=request.GET['eliminar_id'])
        if request.method == 'POST' and 'eliminar' in request.POST:
            articulo_eliminar.delete()
            messages.success(request, "Artículo eliminado exitosamente.")
            return redirect('bodega')

    # Obtener advertencias para artículos con baja cantidad
    advertencias = ArticuloBodega.objects.filter(cantidad__lte=10)
    bodegas = Bodega.objects.all()

    context = {
        'articulos': articulos,
        'bodegas': bodegas,
        'search_query': search_query,
        'ubicacion_id': ubicacion_id,
        'cantidad_filtro': cantidad_filtro,
        'advertencias': advertencias,
        'create_form': create_form,  # Formulario de creación
        'edit_form': edit_form,      # Formulario de edición, si aplica
    }

    return render(request, 'bodega.html', context)

# Descargar Informe de Bodega

@login_required
def descargar_informe_bodega(request):
    # Filter articles with low or zero quantity in "bodega"
    articulos_bajos = ArticuloBodega.objects.filter(cantidad__lte=10)

    # Configure the PDF layout in landscape orientation
    buffer = BytesIO()
    pdf = SimpleDocTemplate(buffer, pagesize=landscape(letter))
    elements = []

    # Table header
    data = [
        ["Nombre", "Descripción", "Cantidad", "Ubicación"]
    ]

    # Define the table style with more padding and better appearance
    table_style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('TOPPADDING', (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ])

    # Add data for each article
    for articulo in articulos_bajos:
        data.append([
            articulo.nombre_articulo,
            articulo.descripcion_articulo,
            articulo.cantidad,
            articulo.bodega.nombre_bodega
        ])

    # Create the table and define column widths
    table = Table(data, colWidths=[2*inch, 3*inch, 1*inch, 2*inch])
    table.setStyle(table_style)
    elements.append(table)

    # Build the PDF
    pdf.build(elements)
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="informe_bodega_bajo_stock.pdf"'
    return response


#artciculo bodega
@login_required
def obtener_articulos_por_bodega(request, bodega_id):
    """
    Devuelve los artículos disponibles en la bodega seleccionada.
    """
    articulos = ArticuloBodega.objects.filter(
        bodega_id=bodega_id,  # Coincide con la bodega seleccionada
        cantidad__gt=0        # Cantidad mayor que 0
    ).values(
        'id', 'nombre_articulo', 'cantidad'
    )
    return JsonResponse(list(articulos), safe=False)

@login_required
def mover_articulo_view(request):
    # Cargar las bodegas y pañoles
    bodegas = Bodega.objects.all()
    panoles = Panol.objects.all()

    # Si es POST, procesar el movimiento
    if request.method == 'POST':
        articulo_id = request.POST.get('articulo')
        cantidad = int(request.POST.get('cantidad'))
        origen_id = request.POST.get('origen')
        destino_id = request.POST.get('destino')
        motivo = request.POST.get('motivo', '')

        # Validar el artículo y las cantidades
        articulo = get_object_or_404(ArticuloBodega, id=articulo_id, bodega_id=origen_id)
        destino = get_object_or_404(Panol, id=destino_id)

        if cantidad > articulo.cantidad:
            messages.error(request, "Cantidad solicitada excede el inventario disponible.")
            return redirect('mover_articulo')

        # Actualizar cantidades y registrar movimiento
        articulo.cantidad -= cantidad
        articulo.save()

        MovimientoArticulo.objects.create(
            articulo=articulo,
            origen=articulo.bodega,
            destino=destino,
            cantidad=cantidad,
            motivo=motivo,
            fecha_movimiento=now()
        )
        messages.success(request, f"Movimiento exitoso de {cantidad} {articulo.nombre_articulo}.")
        return redirect('mover_articulo')

    # Historial de movimientos
    historial = MovimientoArticulo.objects.all().order_by('-fecha_movimiento')

    context = {
        'bodegas': bodegas,
        'panoles': panoles,
        'historial': historial,
    }
    return render(request, 'mover_articulo.html', context)

#retiro articulo
@login_required
def retiro_articulo_view(request):
    # Historial de retiros
    retiros = RetiroArticulo.objects.all().order_by('-fecha_retiro')  # Ordenar por fecha descendente

    # Procesar formulario de retiro
    if request.method == 'POST':
        form = RetiroArticuloForm(request.POST)
        if form.is_valid():
            trabajador = form.cleaned_data['trabajador']
            articulo = form.cleaned_data['articulo']
            cantidad = form.cleaned_data['cantidad']

            # Validar que la cantidad solicitada no exceda el inventario
            if articulo.cantidad >= cantidad:
                articulo.cantidad -= cantidad  # Descontar la cantidad retirada
                articulo.save()

                # Crear el registro de retiro
                retiro = RetiroArticulo.objects.create(
                    trabajador=trabajador,
                    articulo=articulo,
                    cantidad=cantidad
                )
                retiro.save()
                messages.success(request, "El retiro se registró correctamente.")
                return redirect('retiro_articulo')
            else:
                messages.error(request, "La cantidad solicitada excede el inventario disponible.")
        else:
            messages.error(request, "Por favor, corrija los errores en el formulario.")
    else:
        form = RetiroArticuloForm()

    context = {
        'form': form,
        'retiros': retiros,
    }
    return render(request, 'retiro_articulo.html', context)


# Normalizar RUT
def normalizar_rut(rut):
    return rut.replace(".", "").replace("-", "").strip().upper()

# Vista para gestión de trabajadores


def corregir_certificaciones_invalidas():
    """
    Corrige las certificaciones no renovables eliminando cualquier fecha de finalización inválida.
    """
    certificaciones_invalidas = CapacitacionTrabajador.objects.filter(
        Q(capacitacion__es_renovable=False) & ~Q(fecha_fin=None)
    )

    for cert in certificaciones_invalidas:
        cert.fecha_fin = None
        cert.save()

#Trabajadores
@login_required
def trabajadores_view(request):
    trabajadores = Trabajador.objects.filter(activo=True)

    # Filtrar por búsqueda general
    search_query = request.GET.get('search', '')
    if search_query:
        trabajadores = trabajadores.filter(
            Q(nombre_trabajador__icontains=search_query) |
            Q(rut__icontains=search_query) |
            Q(area__nombre_area__icontains=search_query) |
            Q(cargo__nombre_cargo__icontains=search_query)
        )

    # Filtrar por área
    area_id = request.GET.get('area', '')
    if area_id:
        trabajadores = trabajadores.filter(area_id=area_id)

    # Filtrar por turno
    turno = request.GET.get('turno', '')
    if turno:
        trabajadores = trabajadores.filter(turno__tipo_turno=turno)

    # Filtrar por certificaciones próximas a expirar o expiradas
    certificacion = request.GET.get('certificacion', '')
    if certificacion == "expira_90":
        fecha_limite = now() + timedelta(days=90)
        trabajadores = trabajadores.filter(
            capacitaciontrabajador__fecha_fin__lte=fecha_limite,
            capacitaciontrabajador__fecha_fin__gte=now()
        )
    elif certificacion == "expira_30":
        fecha_limite = now() + timedelta(days=30)
        trabajadores = trabajadores.filter(
            capacitaciontrabajador__fecha_fin__lte=fecha_limite,
            capacitaciontrabajador__fecha_fin__gte=now()
        )
    elif certificacion == "expirada":
        trabajadores = trabajadores.filter(
            capacitaciontrabajador__fecha_fin__lt=now()
        )

    # **Advertencia**: Verificar si hay trabajadores activos con certificaciones próximas a expirar o expiradas
    advertencia = CapacitacionTrabajador.objects.filter(
        trabajador__activo=True,
        fecha_fin__lte=now() + timedelta(days=90),  # Próximas a expirar en 90 días
        fecha_fin__gte=now()
    ).exists()

    # Preparar datos para el template
    trabajadores_data = []
    for trabajador in trabajadores:
        horas_trabajadas = trabajador.registrohoras_set.aggregate(total=Sum('horas_trabajadas'))['total'] or 0
        horas_esperadas = trabajador.registrohoras_set.aggregate(total=Sum('horas_esperadas'))['total'] or 0

        trabajadores_data.append({
            'trabajador': trabajador,
            'horas_trabajadas': horas_trabajadas,
            'horas_esperadas': horas_esperadas,
        })

    context = {
        'trabajadores_data': trabajadores_data,
        'areas': Area.objects.all(),
        'advertencia': advertencia,  # Pasar la advertencia al template
    }
    return render(request, 'trabajadores.html', context)


def normalizar_rut(rut):
    return rut.replace(".", "").strip().upper()

@login_required
def add_trabajador_view(request):
    if request.method == "POST":
        # Normalizar el RUT
        rut = normalizar_rut(request.POST.get('rut'))
        
        # Los demás datos
        nombre = request.POST.get('nombre')
        area_id = request.POST.get('area')
        cargo_id = request.POST.get('cargo')
        jornada_id = request.POST.get('jornada')
        turno_id = request.POST.get('turno')
        horario_id = request.POST.get('horario')
        horas_esperadas = int(request.POST.get('horas_esperadas', 40))

        # Verificar si el trabajador ya existe
        if Trabajador.objects.filter(rut=rut).exists():
            messages.error(request, f"Ya existe un trabajador con el RUT {rut}.")
            return redirect('add_trabajador')

        # Crear el trabajador
        trabajador = Trabajador.objects.create(
            rut=rut,
            nombre_trabajador=nombre,
            area=get_object_or_404(Area, id=area_id),
            cargo=get_object_or_404(Cargo, id=cargo_id),
            jornada=get_object_or_404(Jornada, id=jornada_id),
            turno=get_object_or_404(Turno, id=turno_id),
            horario=get_object_or_404(Horario, id=horario_id),
        )

        # Registrar horas trabajadas
        RegistroHoras.objects.create(
            trabajador=trabajador,
            area=trabajador.area,
            horas_trabajadas=0,
            horas_esperadas=horas_esperadas,
            fecha_registro=timezone.now()
        )

        messages.success(request, f"El trabajador {nombre} fue agregado exitosamente.")
        return redirect('gestion_trabajadores')

    # Obtener datos para los dropdowns
    context = {
        'areas': Area.objects.all(),
        'cargos': Cargo.objects.all(),
        'jornadas': Jornada.objects.all(),
        'turnos': Turno.objects.all(),
        'horarios': Horario.objects.all(),
    }
    return render(request, 'add_trabajador.html', context)

# Vista para editar trabajador
@login_required
def editar_trabajador(request, rut):
    trabajador = get_object_or_404(Trabajador, rut=rut)

    if request.method == 'POST':
        # Actualizar información básica del trabajador
        trabajador.nombre_trabajador = request.POST.get('nombre')
        area_id = request.POST.get('area')
        cargo_id = request.POST.get('cargo')
        jornada_id = request.POST.get('jornada')
        horario_id = request.POST.get('horario')
        turno_id = request.POST.get('turno')

        if area_id:
            trabajador.area = get_object_or_404(Area, id=area_id)
        if cargo_id:
            trabajador.cargo = get_object_or_404(Cargo, id=cargo_id)
        if jornada_id:
            trabajador.jornada = get_object_or_404(Jornada, id=jornada_id)
        if horario_id:
            trabajador.horario = get_object_or_404(Horario, id=horario_id)
        if turno_id:
            trabajador.turno = get_object_or_404(Turno, id=turno_id)

        trabajador.save()

        # Actualizar horas esperadas y trabajadas
        registro_horas = RegistroHoras.objects.filter(trabajador=trabajador).first()
        if registro_horas:
            registro_horas.horas_esperadas = request.POST.get('horas_esperadas', registro_horas.horas_esperadas)
            registro_horas.horas_trabajadas = request.POST.get('horas_trabajadas', registro_horas.horas_trabajadas)
            registro_horas.save()
        else:
            RegistroHoras.objects.create(
                trabajador=trabajador,
                area=trabajador.area,
                horas_esperadas=request.POST.get('horas_esperadas', 40),
                horas_trabajadas=request.POST.get('horas_trabajadas', 0),
                fecha_registro=timezone.now()
            )

        # Manejo de certificaciones
        certificaciones_a_eliminar = request.POST.getlist('certificaciones_eliminar')
        for cert_id in certificaciones_a_eliminar:
            certificacion = get_object_or_404(CapacitacionTrabajador, id=cert_id)
            certificacion.delete()

        for cert in trabajador.capacitaciontrabajador_set.all():
            fecha_inicio = request.POST.get(f'fecha_inicio_{cert.id}')
            fecha_fin = request.POST.get(f'fecha_fin_{cert.id}') if cert.capacitacion.es_renovable else None
            if fecha_inicio:
                cert.fecha_inicio = fecha_inicio
            if fecha_fin:
                cert.fecha_fin = fecha_fin
            cert.save()

        for key, value in request.POST.items():
            if key.startswith('certificacion_nueva_'):
                capacitacion = get_object_or_404(Capacitacion, id=value)
                fecha_inicio = request.POST.get(f'fecha_inicio_nueva_{key.split("_")[-1]}')
                fecha_fin = request.POST.get(f'fecha_fin_nueva_{key.split("_")[-1]}') if capacitacion.es_renovable else None
                CapacitacionTrabajador.objects.create(
                    trabajador=trabajador,
                    capacitacion=capacitacion,
                    fecha_inicio=fecha_inicio,
                    fecha_fin=fecha_fin,
                )

        messages.success(request, 'El trabajador ha sido actualizado correctamente.')
        return redirect('gestion_trabajadores')

    # Obtener datos para mostrar
    registro_horas = RegistroHoras.objects.filter(trabajador=trabajador).first()
    horas_esperadas = registro_horas.horas_esperadas if registro_horas else 40
    horas_trabajadas = registro_horas.horas_trabajadas if registro_horas else 0

    certificaciones_disponibles = Capacitacion.objects.all()

    context = {
        'trabajador': trabajador,
        'areas': Area.objects.all(),
        'cargos': Cargo.objects.all(),
        'jornadas': Jornada.objects.all(),
        'horarios': Horario.objects.all(),
        'turnos': Turno.objects.all(),
        'certificaciones': trabajador.capacitaciontrabajador_set.all(),
        'capacitaciones_disponibles': certificaciones_disponibles,
        'horas_esperadas': horas_esperadas,
        'horas_trabajadas': horas_trabajadas,
    }
    return render(request, 'editar_trabajador.html', context)


# Eliminar certiificación
@csrf_exempt
@login_required
def eliminar_certificacion(request, cert_id):
    try:
        certificacion = get_object_or_404(CapacitacionTrabajador, id=cert_id)
        certificacion.delete()
        return JsonResponse({'success': True, 'message': 'Certificación eliminada correctamente.'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error al eliminar certificación: {str(e)}'})

#Actualizacion de Certificaciones
def actualizar_capacitacion_trabajador(request, pk):
    capacitacion_trabajador = get_object_or_404(CapacitacionTrabajador, pk=pk)

    # Validar que no se pueda asignar fecha de fin a capacitaciones no renovables
    if not capacitacion_trabajador.capacitacion.es_renovable and 'fecha_fin' in request.POST:
        fecha_fin = request.POST.get('fecha_fin')
        if fecha_fin:
            raise ValidationError(
                f"La capacitación '{capacitacion_trabajador.capacitacion.nombre_capacitacion}' no es renovable y no puede tener una fecha de finalización."
            )

    # Actualizar los datos normalmente
    capacitacion_trabajador.fecha_inicio = request.POST.get('fecha_inicio')
    capacitacion_trabajador.fecha_fin = request.POST.get('fecha_fin', None)
    capacitacion_trabajador.save()
    return JsonResponse({'success': True})

# Ocultar trabajador (equivalente a eliminar visualmente)
@csrf_exempt
def eliminar_trabajador(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            rut = data.get('rut', '').strip()  # Recupera el RUT enviado
            print("RUT recibido del frontend:", rut)  # Depuración

            # Busca el trabajador tal como está en la base de datos
            trabajador = Trabajador.objects.get(rut=rut)
            trabajador.activo = False
            trabajador.save()

            return JsonResponse({'success': True, 'message': 'Trabajador eliminado correctamente.'})
        except Trabajador.DoesNotExist:
            print("Trabajador no encontrado en la base de datos.")
            return JsonResponse({'success': False, 'message': f'Trabajador con RUT {rut} no encontrado.'})
        except Exception as e:
            print(f"Error inesperado: {e}")
            return JsonResponse({'success': False, 'message': f'Error inesperado: {str(e)}'})
    return JsonResponse({'success': False, 'message': 'Método no permitido.'})

# Generar informe de certificaciones próximas a expirar
@login_required
def descargar_informe_trabajadores(request):
    fecha_limite = now() + timedelta(days=30)
    trabajadores = Trabajador.objects.filter(
        capacitaciontrabajador__fecha_fin__lte=fecha_limite
    ).distinct()

    buffer = BytesIO()
    pdf = SimpleDocTemplate(buffer, pagesize=landscape(letter))
    elements = []

    # Encabezado
    data = [
        ["RUT", "Nombre", "Área", "Puesto", "Certificación", "Fecha de Expiración"]
    ]

    # Detalles
    for trabajador in trabajadores:
        certificaciones = CapacitacionTrabajador.objects.filter(
            trabajador=trabajador, fecha_fin__lte=fecha_limite
        )
        for cert in certificaciones:
            data.append([
                trabajador.rut,
                trabajador.nombre_trabajador,
                trabajador.area.nombre_area,
                trabajador.cargo.nombre_cargo,
                cert.capacitacion.nombre_capacitacion,
                cert.fecha_fin.strftime('%d-%m-%Y'),
            ])

    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    elements.append(table)
    pdf.build(elements)
    buffer.seek(0)
    return FileResponse(buffer, as_attachment=True, filename="informe_trabajadores.pdf")

from django.http import HttpResponseForbidden

#Maquinaria
@login_required
def maquinaria_view(request):
    maquinarias = Maquinaria.objects.all()

    # Filtros de búsqueda
    search_query = request.GET.get('search', '')
    if search_query:
        maquinarias = maquinarias.filter(
            Q(nombre_maquinaria__icontains=search_query) |
            Q(area__nombre_area__icontains=search_query) |
            Q(estado__icontains=search_query)
        )

    # Filtrar por estado
    estado = request.GET.get('estado', '')
    if estado:
        maquinarias = maquinarias.filter(estado=estado)

    # Filtrar por área
    area_id = request.GET.get('area', '')
    if area_id:
        maquinarias = maquinarias.filter(area_id=area_id)

    context = {
        'maquinarias': maquinarias,
        'areas': Area.objects.all(),
        'estados': dict(Maquinaria.ESTADOS),  # Convertir a dict para usar en el template
        'selected_estado': estado,
        'selected_area': area_id,
        'search_query': search_query,
    }
    return render(request, 'maquinaria.html', context)



@login_required
def add_maquinaria(request):
    if request.method == 'POST':
        nombre = request.POST.get('nombre_maquinaria')
        estado = request.POST.get('estado')
        area_id = request.POST.get('area')
        area = Area.objects.get(id=area_id) if area_id else None

        Maquinaria.objects.create(
            nombre_maquinaria=nombre,
            estado=estado,
            area=area,
            fecha_adquisicion=now().date()  # Fecha actual al agregar
        )
        messages.success(request, f"La maquinaria {nombre} fue añadida exitosamente.")
        return redirect('maquinaria')

@login_required
def edit_maquinaria(request, maquinaria_id):
    maquinaria = get_object_or_404(Maquinaria, id=maquinaria_id)

    if request.method == 'POST':
        nombre_maquinaria = request.POST.get('nombre_maquinaria')
        estado = request.POST.get('estado')
        area_id = request.POST.get('area')
        fecha_adquisicion = request.POST.get('fecha_adquisicion')

        # Validar y convertir la fecha
        try:
            fecha_adquisicion = datetime.strptime(fecha_adquisicion, '%d-%m-%Y').strftime('%Y-%m-%d')
        except ValueError:
            return JsonResponse({'error': 'Formato de fecha inválido. Use DD-MM-YYYY.'}, status=400)

        # Actualizar los datos
        maquinaria.nombre_maquinaria = nombre_maquinaria
        maquinaria.estado = estado
        maquinaria.area_id = area_id
        maquinaria.fecha_adquisicion = fecha_adquisicion

        try:
            maquinaria.save()
            messages.success(request, f"La maquinaria {maquinaria.nombre_maquinaria} fue editada exitosamente.")
            return redirect('maquinaria')
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Método no permitido.'}, status=405)

@login_required
def delete_maquinaria(request, maquinaria_id):
    maquinaria = get_object_or_404(Maquinaria, id=maquinaria_id)
    if request.method == "POST":
        maquinaria.delete()
        messages.success(request, f"La maquinaria {maquinaria.nombre_maquinaria} fue eliminada exitosamente.")
        return redirect('maquinaria')
    else:
        messages.error(request, "No se pudo eliminar la maquinaria.")
        return redirect('maquinaria')
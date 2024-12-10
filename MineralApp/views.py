# Módulos estándar de Python
import base64
import csv
import io
import json
import re
from datetime import date, datetime, timedelta
from itertools import chain
import chardet

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
from django.utils.timezone import now
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

    # Obtener certificaciones próximas a expirar (90 días o menos) o expiradas
    certificaciones_proximas_qs = CapacitacionTrabajador.objects.filter(
        Q(fecha_fin__lte=now() + timedelta(days=90), fecha_fin__gte=now()) |
        Q(fecha_fin__lt=now()),
        trabajador__activo=True
    ).select_related('trabajador', 'capacitacion')

    certificaciones_data = [
        {
            "trabajador": cert.trabajador,
            "capacitacion": cert.capacitacion,
            "fecha_fin": cert.fecha_fin,
            "dias_restantes": (cert.fecha_fin - now().date()).days if cert.fecha_fin >= now().date() else "Expirada",
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


# ------------------ SUBIDA DE ARCHIVOS ------------------

def decode_csv_file(file):
    raw_data = file.read()
    result = chardet.detect(raw_data)
    encoding = result['encoding']
    decoded_file = raw_data.decode(encoding).splitlines()
    return decoded_file

def procesar_despidos_csv(file):
    """
    Procesa el archivo Despidos.csv y actualiza el estado de los trabajadores en la base de datos.
    """
    try:
        # Leer el archivo CSV
        decoded_file = file.read().decode('utf-8', errors='replace').splitlines()
        reader = csv.DictReader(decoded_file)
        
        # Validar que la columna 'RUT' esté presente
        if 'RUT' not in reader.fieldnames:
            raise Exception("El archivo Despidos.csv debe contener una columna 'RUT'.")

        errores = []

        # Procesar cada fila
        for row in reader:
            rut = row.get('RUT').strip()
            motivo = row.get('Motivo', '').strip()
            fecha_despido = row.get('Fecha Despido', '').strip()

            try:
                # Buscar el trabajador por RUT
                trabajador = Trabajador.objects.filter(rut=rut).first()
                if trabajador:
                    # Marcar como inactivo
                    trabajador.activo = False
                    trabajador.save()

                    # Registrar el motivo o la fecha si están presentes (opcional)
                    if motivo or fecha_despido:
                        # Lógica adicional para guardar información del despido si es necesaria
                        pass
                else:
                    errores.append(f"Trabajador con RUT {rut} no encontrado.")
            except Exception as e:
                errores.append(f"Error procesando RUT {rut}: {e}")

        # Retornar errores si los hay
        return errores
    except UnicodeDecodeError as e:
        raise Exception(f"Error de codificación en el archivo: {e}")
    except Exception as e:
        raise Exception(f"Error al procesar el archivo Despidos.csv: {e}")



def procesar_archivo_csv(nombre_archivo, file):
    try:
        # Detectar el archivo y llamar a la función correspondiente
        if nombre_archivo == 'Trabajadores.csv':
            procesar_trabajadores_csv(file)
        elif nombre_archivo == 'Capacitaciones.csv':
            procesar_capacitaciones_csv(file)
        elif nombre_archivo == 'Inventario_Panol.csv':
            procesar_inventario_panol_csv(file)
        elif nombre_archivo == 'Inventario_Bodega.csv':
            procesar_inventario_bodega_csv(file)
        elif nombre_archivo == 'Despidos.csv':
            procesar_despidos_csv(file)
        elif nombre_archivo == 'Maquinarias.csv':
            procesar_maquinarias_csv(file)
        else:
            raise Exception(f"El archivo {nombre_archivo} no es reconocido.")
    except UnicodeDecodeError as e:
        raise Exception(f"Error de codificación en {nombre_archivo}: {e}")
    except Exception as e:
        raise Exception(f"Error al procesar {nombre_archivo}: {e}")


@login_required
def upload_csv(request):
    if request.method == 'POST':
        if 'file' not in request.FILES:
            messages.error(request, "No se seleccionó ningún archivo.")
            return redirect('upload_csv')  # O cualquier URL de retorno

        archivo = request.FILES['file']
        try:
            # Procesa el archivo
            nombre_archivo = archivo.name
            procesar_archivo_csv(nombre_archivo, archivo)
            messages.success(request, f"El archivo {nombre_archivo} se procesó correctamente.")
        except Exception as e:
            messages.error(request, f"Error al procesar {nombre_archivo}: {e}")
        return redirect('upload_csv')

    return render(request, 'upload.html')




# Procesadores de CSV
def procesar_trabajadores_csv(file):
    """
    Procesa el archivo Trabajadores.csv y actualiza o crea registros únicos basados en el RUT.
    Si el registro no incluye las horas esperadas, se asume un valor predeterminado de 40.
    """
    try:
        decoded_file = decode_csv_file(file)
        reader = csv.DictReader(decoded_file)

        for row in reader:
            # Obtener o crear objetos relacionados
            area, _ = Area.objects.get_or_create(nombre_area=row['Area'])
            cargo, _ = Cargo.objects.get_or_create(nombre_cargo=row['Cargo'])
            jornada, _ = Jornada.objects.get_or_create(tipo_jornada=row['Jornada'])
            turno, _ = Turno.objects.get_or_create(tipo_turno=row['Turno'])
            horario, _ = Horario.objects.get_or_create(ciclo=row['Ciclo'])

            # Crear o actualizar el trabajador
            trabajador, _ = Trabajador.objects.update_or_create(
                rut=row['RUT'],  # Identificador único
                defaults={
                    'nombre_trabajador': row['Nombre'],
                    'area': area,
                    'cargo': cargo,
                    'jornada': jornada,
                    'turno': turno,
                    'horario': horario,
                    'activo': True,
                }
            )

            # Procesar horas trabajadas y esperadas
            horas_esperadas = int(row['Horas']) if 'Horas' in row and row['Horas'] else 40

            # Crear o actualizar el registro de horas
            RegistroHoras.objects.update_or_create(
                trabajador=trabajador,
                area=area,
                fecha_registro=now().date(),  # Fecha actual corregida
                defaults={
                    'horas_trabajadas': 0,  # Asumimos que no se han trabajado horas aún
                    'horas_esperadas': horas_esperadas,
                }
            )
    except Exception as e:
        raise Exception(f"Error al procesar Trabajadores.csv: {e}")
    

def procesar_capacitaciones_csv(file):
    """
    Procesa el archivo Capacitaciones.csv y actualiza o crea registros únicos por combinación de trabajador y capacitación.
    """
    try:
        decoded_file = decode_csv_file(file)
        reader = csv.DictReader(decoded_file)

        for row in reader:
            trabajador = Trabajador.objects.filter(rut=row['RUT']).first()
            if trabajador:
                capacitacion, _ = Capacitacion.objects.get_or_create(
                    nombre_capacitacion=row['Capacitacion']
                )

                # Determinar si es renovable y ajustar la fecha de finalización
                if not capacitacion.es_renovable:
                    fecha_fin = None  # Las capacitaciones no renovables no tienen fecha de fin
                else:
                    fecha_fin = row['Fecha Fin'] if row['Fecha Fin'] else None

                # Crear o actualizar el registro de capacitación
                CapacitacionTrabajador.objects.update_or_create(
                    trabajador=trabajador,
                    capacitacion=capacitacion,
                    defaults={
                        'fecha_inicio': row['Fecha Inicio'],
                        'fecha_fin': fecha_fin,
                    }
                )
            else:
                raise Exception(f"Trabajador no encontrado (RUT: {row['RUT']})")
    except Exception as e:
        raise Exception(f"Error al procesar Capacitaciones.csv: {e}")

def procesar_inventario_panol_csv(file):
    """
    Procesa el archivo Inventario_Panol.csv y actualiza o crea registros únicos
    basados en nombre_articulo y pañol.
    """
    try:
        # Decodificar el archivo
        decoded_file = decode_csv_file(file)
        reader = csv.DictReader(decoded_file)

        for row in reader:
            # Validar campos obligatorios
            if not all(field in row for field in ['Pañol', 'Nombre Articulo', 'Descripción', 'Cantidad']):
                raise Exception("Estructura mal realizada. Faltan campos obligatorios.")

            # Obtener o crear el pañol
            panol, _ = Panol.objects.get_or_create(nombre_panol=row['Pañol'])

            # Actualizar o crear el artículo
            ArticuloPanol.objects.update_or_create(
                nombre_articulo=row['Nombre Articulo'],
                panol=panol,
                defaults={
                    'descripcion_articulo': row['Descripción'],
                    'cantidad': int(row['Cantidad']),
                }
            )
    except UnicodeDecodeError as e:
        raise Exception(f"Error de codificación en Inventario_Panol.csv: {e}")
    except Exception as e:
        raise Exception(f"Error al procesar Inventario_Panol.csv: {e}")



def procesar_inventario_bodega_csv(file):
    """
    Procesa el archivo Inventario_Bodega.csv y actualiza o crea registros únicos
    basados en nombre_articulo y bodega.
    """
    try:
        decoded_file = decode_csv_file(file)
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
    except Exception as e:
        raise Exception(f"Error al procesar Inventario_Bodega.csv: {e}")


def procesar_maquinarias_csv(file):
    try:
        decoded_file = decode_csv_file(file)
        reader = csv.DictReader(decoded_file)
        for row in reader:
            area, _ = Area.objects.get_or_create(nombre_area=row['Area'])
            Maquinaria.objects.update_or_create(
                codigo_maquinaria=row['Código'],  # Identificador único
                defaults={
                    'nombre_maquinaria': row['Nombre Maquinaria'],
                    'fecha_adquisicion': row['Fecha Adquisición'],
                    'estado': row['Estado'],
                    'area': area,
                }
            )
    except Exception as e:
        raise Exception(f"Error al procesar Maquinarias.csv: {e}")

# -------------------- Vista de pañol -----------------------------------
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

    # Advertencia de certificaciones próximas a expirar
    advertencia = CapacitacionTrabajador.objects.filter(
        trabajador__activo=True,
        fecha_fin__lte=now() + timedelta(days=90),  # Próximas a expirar en 90 días
        fecha_fin__gte=now()
    ).exists()

    # Preparar datos para el template, incluyendo certificaciones
    trabajadores_data = []
    for trabajador in trabajadores:
        horas_trabajadas = trabajador.registrohoras_set.aggregate(total=Sum('horas_trabajadas'))['total'] or 0
        horas_esperadas = trabajador.registrohoras_set.aggregate(total=Sum('horas_esperadas'))['total'] or 0
        certificaciones = CapacitacionTrabajador.objects.filter(trabajador=trabajador)

        trabajadores_data.append({
            'trabajador': trabajador,
            'horas_trabajadas': horas_trabajadas,
            'horas_esperadas': horas_esperadas,
            'certificaciones': certificaciones,  # Incluye certificaciones en el contexto
        })

    context = {
        'trabajadores_data': trabajadores_data,
        'areas': Area.objects.all(),
        'advertencia': advertencia,
    }
    print(f"Trabajadores cargados al contexto: {len(trabajadores_data)}")
    return render(request, 'trabajadores.html', context)


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
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse, FileResponse
from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.utils.timezone import now, timezone
from django.core.exceptions import ValidationError
from django.contrib import messages
from django.db.models import Q, Sum, F, Case, When, IntegerField, Count
from datetime import datetime, date, timedelta
from itertools import chain
import json
import csv
import base64
import re

from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.units import inch
import matplotlib.pyplot as plt
import io
from reportlab.pdfgen import canvas
from io import BytesIO

from .models import (
    CustomUser, Trabajador, Area, Cargo, Horario, Jornada, Turno,
    Capacitacion, CapacitacionTrabajador, Panol, Bodega,
    ArticuloPanol, ArticuloBodega, Maquinaria, MantenimientoMaquinaria, MovimientoArticulo, RegistroHoras, RetiroArticulo
)
from .forms import (
    ArticuloBodegaForm, ArticuloPanolForm, ProductoForm, CapacitacionForm, TrabajadorForm,
    CapacitacionTrabajadorForm, CapacitacionTrabajadorFormSet, MovimientoArticuloForm, RetiroArticuloForm
)


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
    # Datos de trabajadores
    total_horas_esperadas_trabajadores = RegistroHoras.objects.filter(trabajador__isnull=False).aggregate(Sum('horas_esperadas'))['horas_esperadas__sum'] or 0
    total_horas_trabajadas_trabajadores = RegistroHoras.objects.filter(trabajador__isnull=False).aggregate(Sum('horas_trabajadas'))['horas_trabajadas__sum'] or 0

    porcentaje_trabajadores = (
        (total_horas_trabajadas_trabajadores / total_horas_esperadas_trabajadores) * 100
        if total_horas_esperadas_trabajadores > 0 else 0
    )

    # Datos de maquinarias
    total_horas_esperadas_maquinarias = RegistroHoras.objects.filter(maquinaria__isnull=False).aggregate(Sum('horas_esperadas'))['horas_esperadas__sum'] or 0
    total_horas_trabajadas_maquinarias = RegistroHoras.objects.filter(maquinaria__isnull=False).aggregate(Sum('horas_trabajadas'))['horas_trabajadas__sum'] or 0

    porcentaje_maquinarias = (
        (total_horas_trabajadas_maquinarias / total_horas_esperadas_maquinarias) * 100
        if total_horas_esperadas_maquinarias > 0 else 0
    )

    # Movimientos en bodega
    movimientos_bodega_data = MovimientoArticulo.objects.values('origen__nombre_bodega').annotate(
        total_movimientos=Sum('cantidad')
    )

    # Gráficos
    chart_trabajadores = generar_grafico_horas(
        RegistroHoras.objects.filter(trabajador__isnull=False).values('area__nombre_area').annotate(
            horas_trabajadas=Sum('horas_trabajadas'),
            horas_esperadas=Sum('horas_esperadas'),
        ),
        "Horas Trabajadas por Área (Trabajadores)"
    )

    chart_maquinarias = generar_grafico_horas(
        RegistroHoras.objects.filter(maquinaria__isnull=False).values('area__nombre_area').annotate(
            horas_trabajadas=Sum('horas_trabajadas'),
            horas_esperadas=Sum('horas_esperadas'),
        ),
        "Horas Trabajadas por Área (Maquinarias)"
    )

    chart_movimientos_bodega = generar_grafico_barras_simple(
        movimientos_bodega_data,
        "Movimientos en Bodega",
        "origen__nombre_bodega",
        "total_movimientos"
    )

    # Datos para retiros en el pañol
    retiros_pañol_data = (
        RetiroArticulo.objects.values("articulo__nombre_articulo")
        .annotate(total_cantidad=Sum("cantidad"))
    )

    # Generar gráfico para retiros en el pañol
    chart_retiros_pañol = generar_grafico_barras_simple(
        data=retiros_pañol_data,
        label_name="articulo__nombre_articulo",
        value_name="total_cantidad",
        color="blue"
    )

    context = {
        "total_horas_esperadas_trabajadores": total_horas_esperadas_trabajadores,
        "total_horas_trabajadas_trabajadores": total_horas_trabajadas_trabajadores,
        "porcentaje_trabajadores": round(porcentaje_trabajadores, 2),

        "total_horas_esperadas_maquinarias": total_horas_esperadas_maquinarias,
        "total_horas_trabajadas_maquinarias": total_horas_trabajadas_maquinarias,
        "porcentaje_maquinarias": round(porcentaje_maquinarias, 2),

        "chart_trabajadores": chart_trabajadores,
        "chart_maquinarias": chart_maquinarias,
        "chart_movimientos_bodega": chart_movimientos_bodega,
        "chart_retiros_pañol": chart_retiros_pañol,
    }

    return render(request, "index.html", context)



# Función para gráficos de horas
def generar_grafico_horas(data, titulo, color1="blue", color2="green"):
    """
    Genera un gráfico de barras para comparar horas esperadas y trabajadas.
    """
    if not data:
        return ""

    areas = [d["area__nombre_area"] for d in data]
    horas_esperadas = [d["horas_esperadas"] for d in data]
    horas_trabajadas = [d["horas_trabajadas"] for d in data]

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(areas, horas_esperadas, label="Horas Esperadas", color=color1)
    ax.bar(areas, horas_trabajadas, label="Horas Trabajadas", color=color2, alpha=0.7)
    ax.set_title(titulo)
    ax.set_ylabel("Horas")
    ax.set_xticks(range(len(areas)))
    ax.set_xticklabels(areas, rotation=45, ha="right")
    ax.legend()
    plt.tight_layout()

    buffer = io.BytesIO()
    plt.savefig(buffer, format="png")
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
    buffer.close()
    return image_base64

# Función para gráficos simples de barras
def generar_grafico_barras_simple(data, titulo, label_name, value_name):
    """
    Genera un gráfico de barras simple basado en datos con etiquetas y valores.
    """
    if not data:
        return ""

    try:
        labels = [d[label_name] for d in data]
        values = [d[value_name] for d in data]
    except KeyError as e:
        raise KeyError(
            f"La clave '{e.args[0]}' no existe en los datos proporcionados. "
            f"Datos disponibles: {list(data[0].keys()) if data else 'No hay datos'}"
        )

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(labels, values, color="skyblue")
    ax.set_title(titulo)
    ax.set_ylabel("Cantidad")
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=45, ha="right")
    plt.tight_layout()

    buffer = io.BytesIO()
    plt.savefig(buffer, format="png")
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
    buffer.close()
    return image_base64



def generar_informe_pdf(request):
    # Crear un archivo PDF en memoria
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="informe.pdf"'

    # Generar contenido del PDF
    p = canvas.Canvas(response)
    p.drawString(100, 750, "Informe generado desde Mineral Manager")
    p.showPage()
    p.save()

    return response


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

                # Agrega validaciones para otros tipos de archivos
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
def articulo_bodega_view(request):
    if request.method == 'POST':
        form = MovimientoArticuloForm(request.POST)
        if form.is_valid():
            form.save()
            # Puedes añadir un mensaje de éxito
            return redirect('articulo_bodega')
    else:
        form = MovimientoArticuloForm()

    articulos = ArticuloBodega.objects.all()
    return render(request, 'articulobodega.html', {'form': form, 'articulos': articulos})



#maquinaria
@login_required
def maquinaria(request):
    maquinarias = Maquinaria.objects.all()
    areas = Area.objects.all()

    # Procesar la creación de nueva maquinaria
    if request.method == 'POST' and 'crear' in request.POST:
        nombre_maquinaria = request.POST.get('nombre_maquinaria')
        codigo_maquinaria = request.POST.get('codigo_maquinaria')
        fecha_adquisicion = request.POST.get('fecha_adquisicion')
        estado = request.POST.get('estado')
        area_id = request.POST.get('area')

        if nombre_maquinaria and codigo_maquinaria and fecha_adquisicion and estado and area_id:
            area = get_object_or_404(Area, id=area_id)
            Maquinaria.objects.create(
                nombre_maquinaria=nombre_maquinaria,
                codigo_maquinaria=codigo_maquinaria,
                fecha_adquisicion=fecha_adquisicion,
                estado=estado,
                area=area
            )
            messages.success(request, "Nueva maquinaria creada con éxito.")
            return redirect('maquinaria')

    # Procesar la edición de maquinaria existente
    if request.method == 'POST' and 'editar_id' in request.POST:
        maquinaria_id = request.POST.get('editar_id')
        maquinaria = get_object_or_404(Maquinaria, id=maquinaria_id)

        maquinaria.nombre_maquinaria = request.POST.get('nombre_maquinaria')
        maquinaria.codigo_maquinaria = request.POST.get('codigo_maquinaria')
        maquinaria.fecha_adquisicion = request.POST.get('fecha_adquisicion')
        maquinaria.estado = request.POST.get('estado')
        area_id = request.POST.get('area')
        maquinaria.area = get_object_or_404(Area, id=area_id)
        maquinaria.save()

        messages.success(request, f"La maquinaria {maquinaria.nombre_maquinaria} fue actualizada con éxito.")
        return redirect('maquinaria')

    # Procesar la eliminación de maquinaria existente
    if request.method == 'POST' and 'eliminar_id' in request.POST:
        maquinaria_id = request.POST.get('eliminar_id')
        maquinaria = get_object_or_404(Maquinaria, id=maquinaria_id)
        maquinaria.delete()
        messages.success(request, f"La maquinaria {maquinaria.nombre_maquinaria} fue eliminada con éxito.")
        return redirect('maquinaria')

    context = {
        'maquinarias': maquinarias,
        'areas': areas,
    }
    return render(request, "maquinaria.html", context)


#retiro articulo
def retiro_articulo_view(request):
    # Recuperamos todos los retiros realizados para mostrarlos en el historial
    retiros = RetiroArticulo.objects.all()

    if request.method == 'POST':
        form = RetiroArticuloForm(request.POST)
        if form.is_valid():
            form.save()
            # Redirigimos a la misma página para actualizar la lista después del registro
            return redirect('retiro_articulo')
    else:
        form = RetiroArticuloForm()

    return render(request, 'retiroarticulo.html', {'form': form, 'retiros': retiros})




# Normalizar RUT
def normalizar_rut(rut):
    return rut.replace(".", "").replace("-", "").strip().upper()

# Vista para gestión de trabajadores

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
    if certificacion == "expira_30":
        fecha_limite = timezone.now() + timedelta(days=30)
        trabajadores = trabajadores.filter(
            capacitaciontrabajador__fecha_fin__lte=fecha_limite,
            capacitaciontrabajador__fecha_fin__gte=timezone.now()
        )
    elif certificacion == "expirada":
        trabajadores = trabajadores.filter(
            capacitaciontrabajador__fecha_fin__lt=timezone.now()
        )

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
from django.shortcuts import render, redirect, get_object_or_404
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
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db.models import Q
from .forms import ArticuloBodegaForm, ArticuloPanolForm, ProductoForm, CapacitacionForm, TrabajadorForm, CapacitacionTrabajadorForm
from django.contrib import messages
from reportlab.lib.pagesizes import letter, landscape
from reportlab.pdfgen import canvas
from io import BytesIO
from datetime import timedelta
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.units import inch


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

# Procesa Trabajadores.csv
def handle_trabajadores_csv(file):
    """
    Procesa el archivo Trabajadores.csv y actualiza o crea registros únicos basados en el RUT.
    """
    decoded_file = file.read().decode('utf-8').splitlines()
    reader = csv.DictReader(decoded_file)
    for row in reader:
        area, _ = Area.objects.get_or_create(nombre_area=row['Area'])
        cargo, _ = Cargo.objects.get_or_create(nombre_cargo=row['Cargo'])
        jornada, _ = Jornada.objects.get_or_create(tipo_jornada=row['Jornada'])
        turno, _ = Turno.objects.get_or_create(tipo_turno=row['Turno'])
        horario, _ = Horario.objects.get_or_create(ciclo=row['Ciclo'])

        Trabajador.objects.update_or_create(
            rut=row['RUT'],  # Identificador único
            defaults={
                'nombre_trabajador': row['Nombre'],
                'area': area,
                'cargo': cargo,
                'jornada': jornada,
                'turno': turno,
                'horario': horario,
                'horas_esperadas_totales': int(row['Horas']),
            }
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


# Vista de trabajadores

@login_required
def trabajadores_view(request):
    trabajadores = Trabajador.objects.all()
    certificaciones = Capacitacion.objects.all()
    areas = Area.objects.all()
    cargos = Cargo.objects.all()

    # Crear nuevo trabajador
    if request.method == 'POST' and 'crear_trabajador' in request.POST:
        trabajador_form = TrabajadorForm(request.POST)
        if trabajador_form.is_valid():
            trabajador = trabajador_form.save()

            # Procesar las certificaciones nuevas
            for cert_data in request.POST.getlist('new_certificaciones'):
                cert_id = cert_data['id']
                fecha_inicio = cert_data['fecha_inicio']
                fecha_fin = cert_data['fecha_fin']
                capacitacion = get_object_or_404(Capacitacion, id=cert_id)
                CapacitacionTrabajador.objects.create(
                    trabajador=trabajador,
                    capacitacion=capacitacion,
                    fecha_inicio=fecha_inicio,
                    fecha_fin=fecha_fin
                )

            messages.success(request, "Trabajador agregado exitosamente.")
            return redirect('trabajadores')
        else:
            messages.error(request, "Error al agregar trabajador.")
    else:
        trabajador_form = TrabajadorForm()

    # Procesar la edición de trabajador
    if 'editar_id' in request.GET:
        trabajador = get_object_or_404(Trabajador, rut=request.GET['editar_id'])
        trabajador_form = TrabajadorForm(request.POST or None, instance=trabajador)
        
        if request.method == 'POST' and 'guardar_cambios' in request.POST:
            if trabajador_form.is_valid():
                trabajador_form.save()

                # Procesar las certificaciones vinculadas
                for cert_data in request.POST.getlist('certificaciones'):
                    cert_id = cert_data['id']
                    fecha_inicio = cert_data['fecha_inicio']
                    fecha_fin = cert_data['fecha_fin']
                    capacitacion = get_object_or_404(Capacitacion, id=cert_id)
                    CapacitacionTrabajador.objects.update_or_create(
                        trabajador=trabajador,
                        capacitacion=capacitacion,
                        defaults={'fecha_inicio': fecha_inicio, 'fecha_fin': fecha_fin}
                    )

                messages.success(request, "Trabajador y certificaciones actualizados exitosamente.")
                return redirect('trabajadores')
            else:
                messages.error(request, "Error al editar trabajador.")

    context = {
        'trabajadores': trabajadores,
        'certificaciones': certificaciones,
        'areas': areas,
        'cargos': cargos,
        'trabajador_form': trabajador_form,
    }
    return render(request, 'trabajadores.html', context)



#Descargar Informe de Trabajadores
@login_required
def descargar_informe_trabajadores(request):
    # Filtrar certificaciones próximas a expirar
    fecha_limite = timezone.now() + timedelta(days=30)
    trabajadores = Trabajador.objects.filter(
        capacitaciontrabajador__fecha_fin__lte=fecha_limite
    ).distinct()

    # Configuración del PDF en orientación horizontal
    buffer = BytesIO()
    pdf = SimpleDocTemplate(buffer, pagesize=landscape(letter))
    elements = []

    # Encabezado de la tabla
    data = [
        ["Rut", "Nombre Completo", "Puesto de Trabajo", "Área", "Certificación", "Fecha de Expiración"]
    ]

    # Estilo de la tabla con mayor espacio entre celdas
    table_style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('TOPPADDING', (0, 1), (-1, -1), 8),  # Aumenta espacio superior
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),  # Aumenta espacio inferior
        ('LEFTPADDING', (0, 0), (-1, -1), 12),  # Aumenta espacio izquierdo
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),  # Aumenta espacio derecho
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ])

    # Agregar datos de cada trabajador y certificaciones
    for trabajador in trabajadores:
        certificaciones = CapacitacionTrabajador.objects.filter(
            trabajador=trabajador,
            fecha_fin__lte=fecha_limite
        )
        for cert in certificaciones:
            data.append([
                trabajador.rut,
                trabajador.nombre_trabajador,
                trabajador.cargo.nombre_cargo,
                trabajador.area.nombre_area,
                cert.capacitacion.nombre_capacitacion,
                cert.fecha_fin.strftime("%d-%m-%Y")
            ])

    # Creación de la tabla con colWidths para ajustar el ancho total de la página
    table = Table(data, colWidths=[1.5*inch, 2*inch, 2*inch, 1.5*inch, 2*inch, 1.5*inch])
    table.setStyle(table_style)
    elements.append(table)

    # Construcción del PDF
    pdf.build(elements)
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="informe_certificaciones_prontas_a_expirar.pdf"'
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
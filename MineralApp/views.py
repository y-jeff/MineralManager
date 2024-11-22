from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.conf import settings
import csv
from .models import (
    CustomUser, Trabajador, Area, Cargo, Horario, Jornada, Turno,
    Capacitacion, CapacitacionTrabajador, Panol, Bodega,
    ArticuloPanol, ArticuloBodega, Maquinaria, MantenimientoMaquinaria, MovimientoArticulo, RegistroHoras
)
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db.models import Q
from .forms import ArticuloBodegaForm, ArticuloPanolForm, ProductoForm, CapacitacionForm, TrabajadorForm, CapacitacionTrabajadorForm, CapacitacionTrabajadorFormSet
from django.contrib import messages
from reportlab.lib.pagesizes import letter, landscape
from io import BytesIO
from datetime import timedelta
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from datetime import datetime, date
from django.db.models import Sum, F, Q, Case, When, IntegerField
import csv
import matplotlib.pyplot as plt
import io
from django.http import FileResponse
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
import base64

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
    # Datos para trabajadores
    trabajadores = (
        RegistroHoras.objects.filter(trabajador__isnull=False)
        .values("area__nombre_area")
        .annotate(
            horas_totales=Sum("horas_trabajadas"),
            horas_esperadas=Sum("horas_esperadas"),
        )
    )

    # Gráficos de trabajadores
    areas_trabajadores = [t["area__nombre_area"] for t in trabajadores]
    horas_totales_trabajadores = [t["horas_totales"] for t in trabajadores]
    horas_esperadas_trabajadores = [t["horas_esperadas"] for t in trabajadores]

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(areas_trabajadores, horas_esperadas_trabajadores, label="Horas Esperadas", color="blue")
    ax.bar(areas_trabajadores, horas_totales_trabajadores, label="Horas Trabajadas", color="green", alpha=0.7)
    ax.set_title("Horas Trabajadas vs Esperadas (Trabajadores)")
    ax.set_ylabel("Horas")
    ax.legend()
    plt.tight_layout()

    # Convertir gráfico a base64
    buffer = io.BytesIO()
    plt.savefig(buffer, format="png")
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
    buffer.close()

    context = {
        "chart_trabajadores": image_base64,
    }

    return render(request, "index.html", context)

@login_required
def generar_informe_pdf(request):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)

    styles = getSampleStyleSheet()
    content = []

    # Título del informe
    content.append(Paragraph("Informe de KPI's", styles["Title"]))

    # Trabajadores
    content.append(Paragraph("Horas Trabajadas por Trabajadores:", styles["Heading2"]))
    trabajadores_data = [["Área", "Horas Totales", "Horas Esperadas", "Cumplimiento"]]
    trabajadores = (
        RegistroHoras.objects.filter(trabajador__isnull=False)
        .values("area__nombre_area")
        .annotate(
            horas_totales=Sum("horas_trabajadas"),
            horas_esperadas=Sum("horas_esperadas"),
        )
    )
    for t in trabajadores:
        cumplimiento = (
            (t["horas_totales"] / t["horas_esperadas"]) * 100
            if t["horas_esperadas"] > 0
            else 0
        )
        trabajadores_data.append(
            [
                t["area__nombre_area"],
                t["horas_totales"],
                t["horas_esperadas"],
                f"{cumplimiento:.2f}%",
            ]
        )
    tabla_trabajadores = Table(trabajadores_data)
    tabla_trabajadores.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.blue),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
            ]
        )
    )
    content.append(tabla_trabajadores)

    # Maquinarias
    content.append(Paragraph("Horas Trabajadas por Maquinarias:", styles["Heading2"]))
    maquinarias_data = [["Área", "Horas Totales", "Horas Esperadas", "Cumplimiento"]]
    maquinarias = (
        RegistroHoras.objects.filter(maquinaria__isnull=False)
        .values("area__nombre_area")
        .annotate(
            horas_totales=Sum("horas_trabajadas"),
            horas_esperadas=Sum("horas_esperadas"),
        )
    )
    for m in maquinarias:
        cumplimiento = (
            (m["horas_totales"] / m["horas_esperadas"]) * 100
            if m["horas_esperadas"] > 0
            else 0
        )
        maquinarias_data.append(
            [
                m["area__nombre_area"],
                m["horas_totales"],
                m["horas_esperadas"],
                f"{cumplimiento:.2f}%",
            ]
        )
    tabla_maquinarias = Table(maquinarias_data)
    tabla_maquinarias.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.green),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
            ]
        )
    )
    content.append(tabla_maquinarias)

    doc.build(content)
    buffer.seek(0)
    return FileResponse(buffer, as_attachment=True, filename="Informe_KPIs.pdf")

#Vistas para subir archivo
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


# Vista de trabajadores

@login_required
def trabajadores_view(request):
    search_query = request.GET.get('q', '')
    trabajadores = Trabajador.objects.all()

    # Filtro por búsqueda
    if search_query:
        trabajadores = trabajadores.filter(
            Q(rut__icontains=search_query) |
            Q(nombre_trabajador__icontains=search_query)
        )

    context = {
        'trabajadores': trabajadores,
    }
    return render(request, 'trabajadores.html', context)

# Vista para crear un trabajador
@login_required
def crear_trabajador(request):
    if request.method == 'POST':
        trabajador_form = TrabajadorForm(request.POST)
        if trabajador_form.is_valid():
            trabajador = trabajador_form.save()
            messages.success(request, "Trabajador creado exitosamente.")
            return redirect('trabajadores')
        else:
            messages.error(request, "Hubo un error al crear el trabajador.")
    else:
        trabajador_form = TrabajadorForm()

    context = {
        'trabajador_form': trabajador_form,
    }
    return render(request, 'crear_trabajador.html', context)

# Vista para editar un trabajador
@login_required
def editar_trabajador(request, rut):
    trabajador = get_object_or_404(Trabajador, rut=rut)
    form = TrabajadorForm(request.POST or None, instance=trabajador)
    formset = CapacitacionTrabajadorFormSet(request.POST or None, instance=trabajador)

    if request.method == 'POST':
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            messages.success(request, "Cambios guardados exitosamente.")
            return redirect('trabajadores')
        else:
            messages.error(request, "Por favor, corrija los errores en el formulario.")

    # Asegurarnos de que las fechas actuales se carguen correctamente
    for subform in formset:
        if subform.instance.pk:  # Solo para instancias existentes
            subform.initial['fecha_inicio'] = subform.instance.fecha_inicio
            subform.initial['fecha_fin'] = subform.instance.fecha_fin

    return render(request, 'editar_trabajador.html', {
        'form': form,
        'formset': formset,
    })

# Vista para agregar una nueva certificación global
@login_required
def agregar_certificacion(request):
    if request.method == 'POST':
        nombre = request.POST.get('nombre_certificacion')
        es_renovable = request.POST.get('es_renovable', 'off') == 'on'

        if Capacitacion.objects.filter(nombre_capacitacion=nombre).exists():
            messages.error(request, f"La certificación '{nombre}' ya existe.")
        else:
            Capacitacion.objects.create(nombre_capacitacion=nombre, es_renovable=es_renovable)
            messages.success(request, f"La certificación '{nombre}' se agregó exitosamente.")
        return redirect('trabajadores')

    return render(request, 'agregar_certificacion.html')

# Vista para eliminar una certificación específica de un trabajador
@login_required
def eliminar_trabajador(request, rut):
    # Busca el trabajador por su RUT, o lanza un error 404 si no existe
    trabajador = get_object_or_404(Trabajador, rut=rut)

    if request.method == "POST":
        # Elimina el trabajador
        trabajador.delete()
        messages.success(request, f"El trabajador {trabajador.nombre_trabajador} ha sido eliminado correctamente.")
        return redirect('trabajadores')  # Redirige a la lista de trabajadores

    # Renderiza la página de confirmación
    return render(request, 'eliminar_trabajador.html', {'trabajador': trabajador})

@login_required
def eliminar_certificacion(request, id):
    # Busca la certificación por su ID
    certificacion = get_object_or_404(CapacitacionTrabajador, id=id)

    if request.method == "POST":
        # Elimina la certificación
        certificacion.delete()
        messages.success(request, "La certificación fue eliminada correctamente.")
        return redirect('trabajadores')  # Redirige a la vista de trabajadores

    # Renderiza una página de confirmación
    return render(request, 'eliminar_certificacion.html', {'certificacion': certificacion})

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


#artciculo bodega
@login_required
def articulobodega(request):
    return render(request, "articulobodega.html")
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
# Módulos estándar de Python
import csv
import json
from datetime import datetime, timedelta
import chardet
import locale

locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')

# Django - Configuración y utilidades
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db.models import Q, Sum
from django.http import FileResponse, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from datetime import datetime, timedelta
from django.utils.timezone import now
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.db.models import F

# Bibliotecas de terceros
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from io import BytesIO

# Módulos del proyecto
from .forms import (
    ArticuloBodegaForm, ArticuloPanolForm,
    CapacitacionTrabajadorFormSet,
    RetiroArticuloForm,
)
from .models import (
    Area, ArticuloBodega, ArticuloPanol, Bodega, Capacitacion,
    CapacitacionTrabajador, Cargo, Horario, Jornada,
    Maquinaria, MovimientoArticulo,
    Panol, RegistroHoras, RetiroArticulo, Trabajador, Turno,
    MantenimientoMaquinaria, TrabajoMaquinaria

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
    stock_bajo_panol = ArticuloPanol.objects.filter(cantidad__lte=50).count()
    stock_bajo_bodega = ArticuloBodega.objects.filter(cantidad__lte=50).count()

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

    maquinaria_mantenimiento = Maquinaria.objects.filter(estado="En Mantenimiento").count()
    maquinaria_inactiva = Maquinaria.objects.filter(estado="Inactivo").count()

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


# --------------------- Vista de Subida de archivos ----------------------------
import csv
import chardet
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import *
from datetime import datetime

# ----------------- DECODIFICAR ARCHIVO CSV -----------------

def decode_csv_file(file):
    """
    Decodifica el archivo CSV con la codificación detectada.
    """
    raw_data = file.read()
    result = chardet.detect(raw_data)
    encoding = result['encoding']
    print(f"Encoding detectado: {encoding}")  # Depuración
    decoded_file = raw_data.decode(encoding).splitlines()
    return csv.DictReader(decoded_file)


# ----------------- PROCESAR ARCHIVO CSV -----------------
def procesar_archivo_csv(nombre_archivo, file):
    """
    Identifica el archivo CSV y llama a la función de procesamiento correspondiente.
    """
    reader = decode_csv_file(file)
    columnas = reader.fieldnames
    print(f"Columnas detectadas en el archivo '{nombre_archivo}': {columnas}")

    try:
        if 'RUT' in columnas and 'Nombre' in columnas and 'Area' in columnas:
            procesar_trabajadores_csv(reader)
        elif 'Código' in columnas and 'Nombre Maquinaria' in columnas:
            procesar_maquinarias_csv(reader)
        elif 'Bodega' in columnas:
            procesar_inventario_bodega_csv(reader)
        elif 'Pañol' in columnas:
            procesar_inventario_panol_csv(reader)
        elif 'Capacitacion' in columnas and 'Fecha Inicio' in columnas:
            procesar_capacitaciones_csv(reader)  # Agregado para Capacitaciones.csv
        elif 'Código' in columnas and 'Fecha Mantenimiento' in columnas:
            procesar_mantenimientos_csv(reader)
        elif 'Código' in columnas and 'horas_trabajadas' in columnas:
            procesar_trabajos_maquinaria_csv(reader)
        else:
            raise Exception(f"El archivo {nombre_archivo} no es reconocido o tiene formato incorrecto.")
    except Exception as e:
        print(f"Error al procesar archivo '{nombre_archivo}': {e}")
        raise e

        

# ----------------- VISTA PRINCIPAL: UPLOAD CSV -----------------
@login_required
def upload_csv(request):
    """
    Vista principal para manejar la subida de archivos CSV.
    """
    if request.method == 'POST' and 'file' in request.FILES:
        archivo = request.FILES['file']
        try:
            procesar_archivo_csv(archivo.name, archivo)
            messages.success(request, "Subida con éxito.")  # Mensaje directo
        except Exception as e:
            messages.error(request, f"Error: {e}")
        return redirect('upload_csv')  # Redirige para refrescar la página

    return render(request, 'upload.html')

# ----------------- FUNCIONES DE PROCESAMIENTO -----------------

def procesar_trabajadores_csv(reader):
    """
    Procesa el archivo Trabajadores.csv y crea o actualiza trabajadores y sus horas.
    """
    for row in reader:
        try:
            # Obtener o crear los campos relacionados
            area, _ = Area.objects.get_or_create(nombre_area=row['Area'])
            turno, _ = Turno.objects.get_or_create(tipo_turno=row['Turno'])
            jornada, _ = Jornada.objects.get_or_create(tipo_jornada=row['Jornada'])
            cargo, _ = Cargo.objects.get_or_create(nombre_cargo=row['Cargo'])
            horario, _ = Horario.objects.get_or_create(ciclo=row.get('Horario', 'Sin Definir'))

            # Crear o actualizar Trabajador
            trabajador, _ = Trabajador.objects.update_or_create(
                rut=row['RUT'],
                defaults={
                    'nombre_trabajador': row['Nombre'],
                    'area': area,
                    'turno': turno,
                    'jornada': jornada,
                    'cargo': cargo,
                    'horario': horario,
                }
            )

            # Registrar horas esperadas y trabajadas
            RegistroHoras.objects.update_or_create(
                trabajador=trabajador,
                fecha_registro=timezone.now().date(),
                defaults={
                    'area': trabajador.area,  # Asignar el área desde el trabajador
                    'horas_esperadas': int(row['Horas Esperadas']),
                    'horas_trabajadas': int(row['Horas']),
                }
            )
        except Exception as e:
            raise Exception(f"Error al procesar trabajador RUT {row['RUT']}: {e}")

def procesar_despidos_csv(reader):
    """
    Procesa el archivo Despidos.csv y actualiza el estado de los trabajadores.
    """
    for row in reader:
        try:
            trabajador = Trabajador.objects.filter(rut=row['RUT']).first()
            if trabajador:
                trabajador.activo = False
                trabajador.save()
        except Exception as e:
            raise Exception(f"Error al procesar despidos: {e}")

def procesar_maquinarias_csv(reader):
    """
    Procesa el archivo Maquinarias.csv.
    """
    for row in reader:
        area, _ = Area.objects.get_or_create(nombre_area=row['Area'])
        Maquinaria.objects.update_or_create(
            codigo_maquinaria=row['Código'],
            defaults={
                'nombre_maquinaria': row['Nombre Maquinaria'],
                'fecha_adquisicion': datetime.strptime(row['Fecha Adquisición'], "%Y-%m-%d").date(),
                'estado': row['Estado'],
                'area': area,
            }
        )

def procesar_inventario_panol_csv(reader):
    """
    Procesa el archivo Inventario_Panol.csv.
    """
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

def procesar_inventario_bodega_csv(reader):
    """
    Procesa el archivo Inventario_Bodega.csv.
    """
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

def procesar_capacitaciones_csv(reader):
    """
    Procesa el archivo Capacitaciones.csv y determina si la capacitación es renovable.
    """
    for row in reader:
        try:
            trabajador = Trabajador.objects.filter(rut=row['RUT']).first()
            if trabajador:
                # Verificar si existe Fecha Fin
                fecha_inicio = row['Fecha Inicio']
                fecha_fin = row['Fecha Fin'] if row['Fecha Fin'] else None
                
                # Determinar si la capacitación es renovable
                es_renovable = True if fecha_fin else False

                # Crear o actualizar la capacitación
                capacitacion, _ = Capacitacion.objects.update_or_create(
                    nombre_capacitacion=row['Capacitacion'],
                    defaults={'es_renovable': es_renovable}
                )

                # Guardar la relación CapacitacionTrabajador
                CapacitacionTrabajador.objects.update_or_create(
                    trabajador=trabajador,
                    capacitacion=capacitacion,
                    defaults={
                        'fecha_inicio': fecha_inicio,
                        'fecha_fin': fecha_fin
                    }
                )
        except Exception as e:
            raise Exception(f"Error al procesar capacitación: {e}")



def procesar_mantenimientos_csv(reader):
    """
    Procesa el archivo Mantenimiento_Maquinaria.csv y registra mantenimientos.
    """
    for row in reader:
        try:
            maquinaria = Maquinaria.objects.get(codigo_maquinaria=row['Código'])
            trabajador = Trabajador.objects.get(nombre_trabajador=row['Realizado Por'])

            MantenimientoMaquinaria.objects.create(
                maquinaria=maquinaria,
                realizado_por=trabajador,
                fecha_mantenimiento=datetime.strptime(row['Fecha Mantenimiento'], "%Y-%m-%d").date(),
                descripcion=row['Descripción']
            )
        except Maquinaria.DoesNotExist:
            raise Exception(f"Error: No existe maquinaria con código {row['Código']}")
        except Trabajador.DoesNotExist:
            raise Exception(f"Error: No existe trabajador {row['Realizado Por']}")
        except Exception as e:
            raise Exception(f"Error en mantenimiento: {e}")

def procesar_trabajos_maquinaria_csv(reader):
    """
    Procesa el archivo Trabajos_Maquinaria.csv.
    """
    for row in reader:
        maquinaria = Maquinaria.objects.get(codigo_maquinaria=row['maquinaria_id'])
        trabajador = Trabajador.objects.get(rut=row['trabajador_id'])
        TrabajoMaquinaria.objects.create(
            maquinaria=maquinaria,
            trabajador=trabajador,
            fecha_trabajo=datetime.strptime(row['fecha_trabajo'], "%Y-%m-%d").date(),
            horas_trabajadas=int(row['horas_trabajadas'])
        )

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
    # Historial de retiros ordenados por fecha más reciente
    retiros = RetiroArticulo.objects.all().order_by('-fecha_retiro', '-id')

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

@login_required
def devolver_articulo(request, retiro_id):
    # Buscar el registro de retiro por ID
    retiro = get_object_or_404(RetiroArticulo, id=retiro_id)

    # Verificar si ya fue devuelto
    if not retiro.es_devuelto:  # Solo si no se ha devuelto aún
        retiro.fecha_devuelta = timezone.now()  # Asignar la fecha actual como devolución
        retiro.es_devuelto = True  # Marcar el estado como devuelto

        # Devolver la cantidad al inventario del artículo
        retiro.articulo.cantidad += retiro.cantidad  # Incrementar el stock del artículo
        retiro.articulo.save()

        retiro.save()  # Guardar los cambios en el registro existente

        messages.success(request, "El artículo ha sido devuelto correctamente.")
    else:
        messages.warning(request, "Este artículo ya fue devuelto anteriormente.")

    return redirect('retiro_articulo')  # Redirigir a la página de historial

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
    # Lista inicial de maquinarias
    maquinarias = Maquinaria.objects.all()

    # Filtrar maquinarias activas y trabajadores activos para los dropdowns
    maquinarias_activas = Maquinaria.objects.filter(estado="Activo")
    trabajadores_activos = Trabajador.objects.filter(activo=True)

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

    # Contexto para el template
    context = {
        'maquinarias': maquinarias,
        'maquinarias_activas': maquinarias_activas,
        'trabajadores_activos': trabajadores_activos,
        'areas': Area.objects.all(),
        'estados': dict(Maquinaria.ESTADOS),
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
        estado = request.POST.get('estado')  # Solo se editará el estado

        # Convertir fecha al formato correcto
        fecha_adquisicion = request.POST.get('fecha_adquisicion', None)
        if fecha_adquisicion:
            try:
                fecha_adquisicion = datetime.strptime(fecha_adquisicion, "%d de %B de %Y").strftime("%Y-%m-%d")
            except ValueError:
                messages.error(request, "Formato de fecha inválido. Debe ser DD de Mes de YYYY.")
                return redirect('maquinaria')

        # Actualizar solo el estado y dejar fecha intacta si no se envía
        maquinaria.estado = estado
        if fecha_adquisicion:
            maquinaria.fecha_adquisicion = fecha_adquisicion

        maquinaria.save()
        messages.success(request, "La maquinaria ha sido actualizada correctamente.")
        return redirect('maquinaria')

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
    
    
@login_required
def add_mantenimiento(request):
    if request.method == "POST":
        maquinaria_id = request.POST.get('maquinaria')
        trabajador_id = request.POST.get('trabajador')
        descripcion = request.POST.get('descripcion')  # Capturar la descripción
        estado_activo = request.POST.get('estado_activo') == "on"

        try:
            maquinaria = Maquinaria.objects.get(id=maquinaria_id)
            trabajador = Trabajador.objects.get(rut=trabajador_id)

            # Guardar mantenimiento con descripción
            MantenimientoMaquinaria.objects.create(
                maquinaria=maquinaria,
                realizado_por=trabajador,
                fecha_mantenimiento=timezone.now().date(),
                descripcion=descripcion  # Guardar la descripción
            )

            # Actualizar estado de la maquinaria
            if not estado_activo:
                maquinaria.estado = "En Mantenimiento"
                maquinaria.save()

            messages.success(request, "Mantenimiento registrado correctamente.")
        except Exception as e:
            messages.error(request, f"Error: {e}")

        return redirect('maquinaria')

@login_required
def add_trabajo_maquinaria(request):
    if request.method == "POST":
        print("Datos recibidos del formulario: ", request.POST)  # Depuración

        maquinaria_id = request.POST.get("maquinaria")
        trabajador_rut = request.POST.get("trabajador")
        horas_trabajadas = request.POST.get("horas_trabajadas")
        descripcion = request.POST.get("descripcion")

        try:
            # Validar campos
            if not horas_trabajadas or not descripcion:
                messages.error(request, "Todos los campos son obligatorios.")
                return redirect('maquinaria')

            if int(horas_trabajadas) > 24 or int(horas_trabajadas) < 1:
                messages.error(request, "Las horas trabajadas deben estar entre 1 y 24.")
                return redirect('maquinaria')

            # Obtener instancias
            maquinaria = get_object_or_404(Maquinaria, id=maquinaria_id)
            trabajador = get_object_or_404(Trabajador, rut=trabajador_rut)

            # Guardar el trabajo
            trabajo = TrabajoMaquinaria.objects.create(
                maquinaria=maquinaria,
                trabajador=trabajador,
                fecha_trabajo=timezone.now().date(),  # Fecha actual
                horas_trabajadas=int(horas_trabajadas),
                descripcion=descripcion
            )

            print("Trabajo guardado: ", trabajo)  # Depuración
            messages.success(request, "Trabajo agregado exitosamente.")
            return redirect('maquinaria')

        except Exception as e:
            print("Error: ", e)  # Depuración
            messages.error(request, f"Error al guardar el trabajo: {e}")
            return redirect('maquinaria')

    else:
        return JsonResponse({"error": "Método no permitido"}, status=405)

@login_required
def desactivar_maquinaria(request, maquinaria_id):
    """
    Cambia el estado de una maquinaria a 'Inactivo' en lugar de eliminarla.
    """
    maquinaria = get_object_or_404(Maquinaria, id=maquinaria_id)
    if request.method == "POST":
        maquinaria.estado = "Inactivo"  # Actualiza el estado
        maquinaria.save()  # Guarda los cambios en la base de datos
        messages.success(request, f"La maquinaria '{maquinaria.nombre_maquinaria}' ha sido desactivada.")
        return redirect('maquinaria')  # Redirige a la vista de maquinarias
    return redirect('maquinaria')

def obtener_mantenimientos(request, maquinaria_id):
    mantenimientos = MantenimientoMaquinaria.objects.filter(maquinaria_id=maquinaria_id)
    data = [
        {
            'rut': m.trabajador.rut,
            'nombre_trabajador': m.trabajador.nombre,
            'codigo_maquinaria': m.maquinaria.codigo,
            'nombre_maquinaria': m.maquinaria.nombre,
            'fecha_mantenimiento': m.fecha_mantenimiento.strftime('%Y-%m-%d'),
            'descripcion': m.descripcion,
        }
        for m in mantenimientos
    ]
    return JsonResponse(data, safe=False)

def obtener_trabajos(request, maquinaria_id):
    trabajos = TrabajoMaquinaria.objects.filter(maquinaria_id=maquinaria_id)
    data = [
        {
            'rut': t.trabajador.rut,
            'nombre_trabajador': t.trabajador.nombre,
            'codigo_maquinaria': t.maquinaria.codigo,
            'nombre_maquinaria': t.maquinaria.nombre,
            'horas_trabajadas': t.horas_trabajadas,
            'descripcion': t.descripcion,
        }
        for t in trabajos
    ]
    return JsonResponse(data, safe=False)



def ver_mantenimientos(request, maquinaria_id):
    maquinaria = get_object_or_404(Maquinaria, id=maquinaria_id)
    search_query = request.GET.get('search', '')

    # Filtrar mantenimientos por búsqueda
    mantenimientos = MantenimientoMaquinaria.objects.filter(maquinaria=maquinaria).order_by('-fecha_mantenimiento')

    if search_query:
        mantenimientos = mantenimientos.filter(
            Q(trabajador__nombre_trabajador__icontains=search_query) |  # Buscar por nombre del trabajador
            Q(trabajador__rut__icontains=search_query) |               # Buscar por RUT del trabajador
            Q(descripcion__icontains=search_query) |                   # Buscar en descripción
            Q(fecha_mantenimiento__icontains=search_query)             # Buscar en fecha
        )

    return render(request, 'ver_mantenimientos.html', {'mantenimientos': mantenimientos, 'maquinaria': maquinaria, 'search_query': search_query})


def ver_trabajos(request, maquinaria_id):
    maquinaria = get_object_or_404(Maquinaria, id=maquinaria_id)
    search_query = request.GET.get('search', '')

    # Filtrar trabajos por búsqueda
    trabajos = TrabajoMaquinaria.objects.filter(maquinaria=maquinaria).order_by('-fecha_trabajo')

    if search_query:
        trabajos = trabajos.filter(
            Q(trabajador__nombre_trabajador__icontains=search_query) |  # Buscar por nombre del trabajador
            Q(trabajador__rut__icontains=search_query) |               # Buscar por RUT del trabajador
            Q(descripcion__icontains=search_query) |                   # Buscar en descripción
            Q(fecha_trabajo__icontains=search_query)                   # Buscar en fecha
        )

    return render(request, 'ver_trabajos.html', {'trabajos': trabajos, 'maquinaria': maquinaria, 'search_query': search_query})
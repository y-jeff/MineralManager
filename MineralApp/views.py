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
from datetime import datetime
from django.core.exceptions import ValidationError
from django.db.models import Q
from .forms import ArticuloBodegaForm, ArticuloPanolForm
from django.contrib import messages
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from io import BytesIO

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

# Funciones para procesar cada CSV (se mantienen sin cambios)
# [...]

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
def descargar_informe(request):
    articulos_bajos = ArticuloPanol.objects.filter(cantidad__lte=10)
    
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    pdf.setTitle("Informe de Artículos Bajos en Stock")

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(72, 750, "Informe de Artículos Bajos en Stock")
    pdf.setFont("Helvetica", 12)
    pdf.drawString(72, 730, "Lista de artículos con stock bajo o agotado:")

    y = 700
    for articulo in articulos_bajos:
        pdf.drawString(72, y, f"Nombre: {articulo.nombre_articulo} | Descripción: {articulo.descripcion_articulo} | "
                              f"Cantidad: {articulo.cantidad} | Ubicación: {articulo.panol.nombre_panol}")
        y -= 20
        if y < 50:
            pdf.showPage()
            y = 750

    pdf.save()

    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="informe_articulos_bajos.pdf"'
    return response
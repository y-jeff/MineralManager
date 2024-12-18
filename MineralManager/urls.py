"""
URL configuration for MineralManager project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from MineralApp import views
from django.shortcuts import redirect
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth import views as auth_views

# Definir la función para verificar si el usuario es superusuario
def is_superuser(user):
    return user.is_authenticated and user.is_superuser

# Redirigir a una vista de "Acceso Denegado" si no es superusuario
def access_denied(request):
    return redirect('login_signup')  # Cambia 'login_signup' a otra vista si prefieres otra redirección

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.login_signup_view, name='login_signup'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login_signup'), name='logout'),

    #Vista de inicio
    path('home/', views.index, name='home'),

    # Subida de archivo
    path('upload/', views.upload_csv, name='upload_csv'),

    # Cambio de contraseña
    path('password_reset/', auth_views.PasswordResetView.as_view(template_name='password_reset_form.html'), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='password_reset_confirm.html'), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='password_reset_complete.html'), name='password_reset_complete'),

    # Vista de "Acceso Denegado"
    path('access_denied/', access_denied, name='access_denied'),

    # Vistas de inventario
    path('pañol/', views.panol_view, name='pañol'),
    path('panol/descargar_informe/', views.descargar_informe_pañol, name='descargar_informe_pañol'),

    #Vista de Trabajadores
    path('trabajadores/', views.trabajadores_view, name='gestion_trabajadores'),
    path('trabajadores/editar/<str:rut>/', views.editar_trabajador, name='editar_trabajador'),
    path('trabajadores/eliminar/', views.eliminar_trabajador, name='eliminar_trabajador'),
    path('trabajadores/agregar/', views.add_trabajador_view, name='add_trabajador'),
    path('trabajadores/descargar_informe/', views.descargar_informe_trabajadores, name='descargar_informe_trabajadores'),
    path('trabajadores/eliminar_certificacion/<int:cert_id>/', views.eliminar_certificacion, name='eliminar_certificacion'),

    # Vista de Bodega
    path('bodega/', views.bodega_view, name='bodega'),
    path('bodega/descargar_informe/', views.descargar_informe_bodega, name='descargar_informe_bodega'),

    # vista articulo bodega
    path('articulobodega/', views.mover_articulo_view, name='mover_articulo'),
    path('api/articulos/<int:bodega_id>/', views.obtener_articulos_por_bodega, name='obtener_articulos_por_bodega'),

    #vista maquinaria
    # Rutas para obtener mantenimientos y trabajos
    path('maquinaria/mantenimientos/<int:maquinaria_id>/', views.ver_mantenimientos, name='ver_mantenimientos'),
    path('maquinaria/trabajos/<int:maquinaria_id>/', views.ver_trabajos, name='ver_trabajos'),

    # Rutas para agregar mantenimiento y trabajo
    path('maquinaria/agregar-mantenimiento/', views.add_mantenimiento, name='add_mantenimiento'),
    path('maquinaria/agregar-trabajo/', views.add_trabajo_maquinaria, name='add_trabajo_maquinaria'),
    
    # Rutas de visualización de maquinaria
    path('maquinaria/', views.maquinaria_view, name='maquinaria'),

    # Ruta para desactivar maquinaria
    path('maquinaria/desactivar/<int:maquinaria_id>/', views.desactivar_maquinaria, name='desactivar_maquinaria'),

   # Ruta para edicion de maquinaria
    path('maquinaria/editar/<int:maquinaria_id>/', views.edit_maquinaria, name='edit_maquinaria'),
    
    #vista retiro
    path('retiro/', views.retiro_articulo_view, name='retiro_articulo'),
    path('devolver/<int:retiro_id>/', views.devolver_articulo, name='devolver_articulo'),
]

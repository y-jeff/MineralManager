from django.contrib import admin
from .models import (
    CustomUser, Area, Cargo, Jornada, Turno, Horario, Trabajador,
    Capacitacion, CapacitacionTrabajador, Panol, Bodega,
    ArticuloPanol, ArticuloBodega, Maquinaria, MantenimientoMaquinaria,
    MovimientoArticulo, RegistroHoras, TrabajoMaquinaria
)
from django.contrib.auth.admin import UserAdmin


class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ('username', 'email', 'is_active', 'is_staff', 'is_superuser', 'date_joined')
    list_filter = ('is_staff', 'is_superuser', 'is_active')
    search_fields = ('username', 'email')
    ordering = ('date_joined',)
    fieldsets = (
        (None, {'fields': ('username', 'email', 'password')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser')}),
        ('Dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'is_active', 'is_staff', 'is_superuser')}
        ),
    )

admin.site.register(CustomUser, CustomUserAdmin)

# Registrar todos los modelos en el panel de administración
admin.site.register(Area)
admin.site.register(Cargo)
admin.site.register(Jornada)
admin.site.register(Turno)
admin.site.register(Horario)
admin.site.register(Trabajador)
admin.site.register(Capacitacion)
admin.site.register(CapacitacionTrabajador)
admin.site.register(Panol)
admin.site.register(Bodega)
admin.site.register(ArticuloPanol)
admin.site.register(ArticuloBodega)
admin.site.register(Maquinaria)
admin.site.register(MantenimientoMaquinaria)
admin.site.register(MovimientoArticulo)
admin.site.register(RegistroHoras)
admin.site.register(TrabajoMaquinaria)
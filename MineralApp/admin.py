from django.contrib import admin
from .models import (
    Area, Categoria, Articulo, Bodega, InventarioArticuloBodega, Capacitacion,
    CargoTrabajador, Trabajador, HorarioTrabajo, JornadaTrabajador, TurnoTrabajador,
    RegistroAsistenciaTrabajador, Asistencia, AsignacionArticulo, CapacitacionTrabajador,
    JornadaEquipo, Panol, RetiroArticulo, RegistroEntrega, CustomUser
)

# Registro de CustomUser con opciones adicionales para el panel de administración
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'is_approved', 'email_confirmed', 'is_admin')
    list_filter = ('is_approved', 'email_confirmed', 'is_admin')
    search_fields = ('username', 'email')
    ordering = ('username',)
    fieldsets = (
        (None, {'fields': ('username', 'email', 'password')}),
        ('Permisos', {'fields': ('is_approved', 'email_confirmed', 'is_admin', 'is_active')}),
    )

admin.site.register(CustomUser, CustomUserAdmin)

# Registro de los demás modelos
admin.site.register(Area)
admin.site.register(Categoria)
admin.site.register(Articulo)
admin.site.register(Bodega)
admin.site.register(InventarioArticuloBodega)
admin.site.register(Capacitacion)
admin.site.register(CargoTrabajador)
admin.site.register(Trabajador)
admin.site.register(HorarioTrabajo)
admin.site.register(JornadaTrabajador)
admin.site.register(TurnoTrabajador)
admin.site.register(RegistroAsistenciaTrabajador)
admin.site.register(Asistencia)
admin.site.register(AsignacionArticulo)
admin.site.register(CapacitacionTrabajador)
admin.site.register(JornadaEquipo)
admin.site.register(Panol)
admin.site.register(RetiroArticulo)
admin.site.register(RegistroEntrega)

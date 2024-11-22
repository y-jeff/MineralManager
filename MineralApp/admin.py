from django.contrib import admin
from .models import (
    CustomUser, Area, Cargo, Jornada, Turno, Horario, Trabajador,
    Capacitacion, CapacitacionTrabajador, Panol, Bodega,
    ArticuloPanol, ArticuloBodega, Maquinaria, MantenimientoMaquinaria,
    MovimientoArticulo, RegistroHoras
)

# Registrar todos los modelos en el panel de administración
admin.site.register(CustomUser)
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
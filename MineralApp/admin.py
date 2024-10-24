from django.contrib import admin
from .models import (
    Area,
    Categoria,
    Articulo,
    Bodega,
    InventarioArticuloBodega,
    MovimientoInventario,
    Capacitacion,
    CargoTrabajador,
    Trabajador,
    HorarioTrabajo,
    JornadaTrabajador,
    TurnoTrabajador,
    RegistroAsistenciaTrabajador,
    Asistencia,
    CapacitacionTrabajador,
    Panol,
    RetiroArticulo,
    RegistroEntrega,
    Maquinaria,
    RegistroCambios,
    MantenimientoMaquinaria,
    RetiroMaquinaria,
    CustomUser  # Ya está registrado
)


# Registrando los modelos en el administrador
admin.site.register(Area)
admin.site.register(Categoria)
admin.site.register(Articulo)
admin.site.register(Bodega)
admin.site.register(InventarioArticuloBodega)
admin.site.register(MovimientoInventario)
admin.site.register(Capacitacion)
admin.site.register(CargoTrabajador)
admin.site.register(Trabajador)
admin.site.register(HorarioTrabajo)
admin.site.register(JornadaTrabajador)
admin.site.register(TurnoTrabajador)
admin.site.register(RegistroAsistenciaTrabajador)
admin.site.register(Asistencia)
admin.site.register(CapacitacionTrabajador)
admin.site.register(Panol)
admin.site.register(RetiroArticulo)
admin.site.register(RegistroEntrega)
admin.site.register(Maquinaria)
admin.site.register(RegistroCambios)
admin.site.register(MantenimientoMaquinaria)
admin.site.register(RetiroMaquinaria)

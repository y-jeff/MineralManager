from django import forms
from .models import (
    ArticuloPanol, ArticuloBodega, Producto, 
    Trabajador, Capacitacion, CapacitacionTrabajador, Bodega
)

# Formulario para subir archivos
class UploadFileForm(forms.Form):
    file = forms.FileField(label='Selecciona un archivo')

# Formulario para crear/editar un artículo en panol
class ArticuloPanolForm(forms.ModelForm):
    class Meta:
        model = ArticuloPanol
        fields = ['nombre_articulo', 'descripcion_articulo', 'cantidad', 'panol']
        widgets = {
            'descripcion_articulo': forms.Textarea(attrs={'rows': 3}),
        }

    def clean_cantidad(self):
        cantidad = self.cleaned_data.get('cantidad')
        if cantidad < 0:
            raise forms.ValidationError("La cantidad no puede ser negativa.")
        return cantidad

# Formulario para disponibilidad en bodega
class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = ['disponibilidad']

    disponibilidad = forms.ChoiceField(
        choices=Producto.disponibilidad_choices,
        widget=forms.RadioSelect,
    )

# Formulario para crear/editar un artículo en bodega
class ArticuloBodegaForm(forms.ModelForm):
    class Meta:
        model = ArticuloBodega
        fields = ['nombre_articulo', 'descripcion_articulo', 'cantidad', 'bodega']
        widgets = {
            'descripcion_articulo': forms.Textarea(attrs={'rows': 3}),
        }

    def clean_cantidad(self):
        cantidad = self.cleaned_data.get('cantidad')
        if cantidad < 0:
            raise forms.ValidationError("La cantidad no puede ser negativa.")
        return cantidad

# Trabajadores Form
class TrabajadorForm(forms.ModelForm):
    class Meta:
        model = Trabajador
        fields = ['rut', 'nombre_trabajador', 'cargo', 'area']

class CapacitacionForm(forms.ModelForm):
    class Meta:
        model = Capacitacion
        fields = ['nombre_capacitacion', 'es_renovable']

class CapacitacionTrabajadorForm(forms.ModelForm):
    class Meta:
        model = CapacitacionTrabajador
        fields = ['capacitacion', 'fecha_inicio', 'fecha_fin']

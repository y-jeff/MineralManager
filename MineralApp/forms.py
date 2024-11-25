from django import forms
from .models import (
    ArticuloPanol, ArticuloBodega, Producto, 
    Trabajador, Capacitacion, CapacitacionTrabajador, Bodega, MovimientoArticulo, RetiroArticulo
)
from django.forms import inlineformset_factory


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

# Formulario para Trabajador
class TrabajadorForm(forms.ModelForm):
    class Meta:
        model = Trabajador
        fields = ['nombre_trabajador', 'area', 'cargo', 'jornada', 'turno', 'horario']
        widgets = {
            'nombre_trabajador': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre Completo'}),
            'area': forms.Select(attrs={'class': 'form-select'}),
            'cargo': forms.Select(attrs={'class': 'form-select'}),
            'jornada': forms.Select(attrs={'class': 'form-select'}),
            'turno': forms.Select(attrs={'class': 'form-select'}),
            'horario': forms.Select(attrs={'class': 'form-select'}),
        }



# Formulario para Capacitaciones
class CapacitacionForm(forms.ModelForm):
    class Meta:
        model = Capacitacion
        fields = ['nombre_capacitacion', 'es_renovable']
        widgets = {
            'nombre_capacitacion': forms.TextInput(attrs={'class': 'form-control'}),
            'es_renovable': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

# Formulario para Capacitaciones relacionadas con Trabajadores
class CapacitacionTrabajadorForm(forms.ModelForm):
    class Meta:
        model = CapacitacionTrabajador
        fields = ['capacitacion', 'fecha_inicio', 'fecha_fin']
        widgets = {
            'fecha_inicio': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control',
            }),
            'fecha_fin': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control',
            }),
        }


# FormSet para gestionar Capacitaciones de un Trabajador
CapacitacionTrabajadorFormSet = inlineformset_factory(
    Trabajador,
    CapacitacionTrabajador,
    form=CapacitacionTrabajadorForm,
    extra=1,
    can_delete=True
)

#formulario de bodega  aarticulo
class MovimientoArticuloForm(forms.ModelForm):
    class Meta:
        model = MovimientoArticulo
        fields = ['articulo', 'origen', 'destino', 'cantidad', 'motivo']
        widgets = {
            'motivo': forms.TextInput(attrs={'placeholder': 'Motivo de movimiento'}),
            'fecha_movimiento': forms.HiddenInput(),  # Se puede manejar automáticamente
        }

#formulario de retiro
class RetiroArticuloForm(forms.ModelForm):
    class Meta:
        model = RetiroArticulo
        fields = ['trabajador', 'articulo', 'cantidad']
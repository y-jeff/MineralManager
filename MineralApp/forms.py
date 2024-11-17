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

# Formulario para Trabajador
class TrabajadorForm(forms.ModelForm):
    class Meta:
        model = Trabajador
        fields = ['rut', 'nombre_trabajador', 'area', 'cargo', 'jornada', 'turno', 'horario']
        widgets = {
            'rut': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ingrese el RUT'}),
            'nombre_trabajador': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre Completo'}),
            'area': forms.Select(attrs={'class': 'form-select'}),
            'cargo': forms.Select(attrs={'class': 'form-select'}),
            'jornada': forms.Select(attrs={'class': 'form-select'}),
            'turno': forms.Select(attrs={'class': 'form-select'}),
            'horario': forms.Select(attrs={'class': 'form-select'}),
        }


# Formulario para Certificación (Individual)
class CapacitacionForm(forms.ModelForm):
    class Meta:
        model = Capacitacion
        fields = ['nombre_capacitacion', 'es_renovable']
        widgets = {
            'nombre_capacitacion': forms.TextInput(attrs={'class': 'form-control'}),
            'es_renovable': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


# FormSet para Certificaciones
CertificacionFormSet = forms.inlineformset_factory(
    Trabajador,
    CapacitacionTrabajador,
    form=CapacitacionForm,
    extra=1,
    can_delete=True,
)
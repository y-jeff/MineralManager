from django import forms
from .models import ArticuloPanol, ArticuloBodega
from .models import Producto #para disponibilidad (no funciona)

#Formulario para subir archivos
class UploadFileForm(forms.Form):
    file = forms.FileField(label='Selecciona un archivo')

#Formulario de Articulo en Bodega
class ArticuloBodegaForm(forms.ModelForm):
    class Meta:
        model = ArticuloBodega
        fields = ['nombre_articulo', 'descripcion_articulo', 'cantidad', 'bodega',]
class ArticuloPanolForm(forms.ModelForm):
    class Meta:
        model = ArticuloPanol
        fields = ['nombre_articulo', 'descripcion_articulo', 'cantidad', 'panol']
#bodega disponibilidad
class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = ['disponibilidad']

    disponibilidad = forms.ChoiceField(
        choices=Producto.disponibilidad_choices,
        widget=forms.RadioSelect,
    )

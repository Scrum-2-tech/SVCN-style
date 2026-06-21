from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import Producto, Color, Talla, PerfilUsuario, Ciudad

class RegistroUsuarioForm(UserCreationForm):
    """
    FORMULARIO DE REGISTRO SEGURO: Hereda de UserCreationForm para asegurar
    que Django aplique los algoritmos de encriptación PBKDF2 (HASH) a la 
    contraseña de forma nativa e indescifrable.
    """
    email = forms.EmailField(required=True, label="Correo Electrónico")
    first_name = forms.CharField(max_length=30, required=True, label="Nombre")
    last_name = forms.CharField(max_length=30, required=True, label="Apellido")

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        if commit:
            user.save()
            # Creamos automáticamente el PerfilUsuario asociado en rol Cliente ('CLI')
            PerfilUsuario.objects.get_or_create(usuario=user, defaults={'rol': 'CLI'})
        return user


class FormularioEnvio(forms.Form):
    """
    FORMULARIO DE COMPRA: Captura los datos esenciales de destino para la
    creación de los Pedidos en el checkout del carrito.
    """
    ciudad = forms.ModelChoiceField(
        queryset=Ciudad.objects.all(),
        empty_label="Selecciona tu ciudad/municipio",
        widget=forms.Select(attrs={'class': 'form-select', 'required': 'true'})
    )
    direccion = forms.CharField(
        max_length=255,
        label="Dirección Exacta",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: Calle 45 #12-34 Apt 201',
            'required': 'true'
        })
    )


class ProductoForm(forms.ModelForm):
    """
    FORMULARIO DE INVENTARIO: Utilizado por el Administrador en el panel
    de mantenimiento para crear y editar productos de la tienda.
    """
    class Meta:
        model = Producto
        fields = [
            'nombre', 'descripcion', 'precio', 'stock', 
            'categoria', 'marca', 'talla', 'color', 'imagen', 'disponible'
        ]
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'precio': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'stock': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'categoria': forms.Select(attrs={'class': 'form-select'}),
            'marca': forms.Select(attrs={'class': 'form-select'}),
            'talla': forms.Select(attrs={'class': 'form-select'}),
            'color': forms.Select(attrs={'class': 'form-select'}),
            'imagen': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'disponible': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class ColorForm(forms.ModelForm):
    class Meta:
        model = Color
        fields = ['nombre', 'codigo_hex']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Negro Oversized'}),
            'codigo_hex': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
        }


class TallaForm(forms.ModelForm):
    class Meta:
        model = Talla
        fields = ['nombre']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: XL'}),
        }


class PerfilUsuarioForm(forms.ModelForm):
    """
    FORMULARIO DE CONTROL DE ROLES: Permite la actualización de roles 
    en los paneles administrativos del sistema.
    """
    class Meta:
        model = PerfilUsuario
        fields = ['rol', 'telefono']
        widgets = {
            'rol': forms.Select(attrs={'class': 'form-select'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
        }
from django.db import models


class Propietario(models.Model):
    TIPO_DOC_CHOICES = [
        ("Cedula", "Cédula"),
        ("NIT", "NIT"),
        ("Pasaporte", "Pasaporte"),
        ("CedulaExtranjeria", "Cédula de extranjería"),
        ("TarjetaIdentidad", "Tarjeta de identidad"),
        ("Otro", "Otro documento"),
    ]

    nombre = models.CharField(max_length=200, blank=True, default="")
    tipo_documento = models.CharField(max_length=30, choices=TIPO_DOC_CHOICES, blank=True, default="")
    numero_documento = models.CharField(max_length=40, blank=True, default="")
    telefono = models.CharField(max_length=40, blank=True, default="")
    email = models.EmailField(blank=True, default="")
    direccion = models.CharField(max_length=255, blank=True, default="")
    ciudad = models.CharField(max_length=100, blank=True, default="")
    contacto_autorizado = models.CharField(max_length=200, blank=True, default="")
    telefono_alternativo = models.CharField(max_length=40, blank=True, default="")
    notas = models.TextField(blank=True, default="")
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre or self.numero_documento or f"Propietario #{self.id}"


class Usuario(models.Model):
    ROL_ADMIN = "Administrador"
    ROL_VET = "Veterinario"
    ROL_PELUQUERO = "Peluquero"
    ROL_CHOICES = [
        (ROL_ADMIN, "Administrador"),
        (ROL_VET, "Veterinario"),
        (ROL_PELUQUERO, "Peluquero"),
    ]

    user = models.CharField(max_length=80, unique=True, db_column="User")
    email = models.EmailField(unique=True, db_column="Email")
    password = models.CharField(max_length=255, db_column="Password")
    phone = models.CharField(max_length=40, blank=True, default="", db_column="Phone")
    address = models.CharField(max_length=255, blank=True, default="", db_column="Address")
    rol = models.CharField(max_length=20, choices=ROL_CHOICES, default=ROL_ADMIN, db_column="Rol")

    nombre = models.CharField(max_length=120, blank=True, default="")
    especialidad = models.CharField(max_length=120, blank=True, default="")
    license = models.CharField(max_length=80, blank=True, default="")
    profile_picture = models.TextField(blank=True, null=True)

    ofrece_consulta_medica = models.BooleanField(default=True)
    ofrece_peluqueria = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user} ({self.rol})"


class Paciente(models.Model):
    SEXO_CHOICES = [
        ("Macho", "Macho"),
        ("Hembra", "Hembra"),
        ("Desconocido", "Desconocido"),
    ]
    TALLA_CHOICES = [
        ("Pequeño", "Pequeño"),
        ("Mediano", "Mediano"),
        ("Grande", "Grande"),
        ("Gigante", "Gigante"),
    ]
    ESTADO_REPRODUCTIVO_CHOICES = [
        ("Entero", "Entero"),
        ("Esterilizado", "Esterilizado"),
        ("Castrado", "Castrado"),
        ("Desconocido", "Desconocido"),
    ]

    propietario = models.ForeignKey(
        Propietario, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="mascotas"
    )
    # Legacy FK a Usuario (se mantiene por compatibilidad)
    owner = models.ForeignKey(
        "Usuario", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="mascotas", db_column="id_user"
    )

    nombre = models.CharField(max_length=120, blank=True, default="")
    codigo_chip = models.CharField(max_length=80, blank=True, default="")
    especie = models.CharField(max_length=80, blank=True, default="")
    raza = models.CharField(max_length=120, blank=True, default="")
    sexo = models.CharField(max_length=20, choices=SEXO_CHOICES, default="Desconocido")
    color = models.CharField(max_length=80, blank=True, default="")
    fecha_nacimiento = models.DateField(null=True, blank=True)
    peso = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    unidad_peso = models.CharField(max_length=10, default="kg")
    talla = models.CharField(max_length=20, choices=TALLA_CHOICES, blank=True, default="")
    estado_reproductivo = models.CharField(max_length=20, choices=ESTADO_REPRODUCTIVO_CHOICES, blank=True, default="")
    alimento = models.CharField(max_length=120, blank=True, default="")
    profile_picture = models.TextField(blank=True, null=True)

    # Legacy owner fields (kept for backward compat)
    owner_tipo_documento = models.CharField(max_length=8, blank=True, default="")
    owner_documento = models.CharField(max_length=40, blank=True, default="")
    owner_email = models.EmailField(blank=True, default="")
    owner_direccion = models.CharField(max_length=255, blank=True, default="")
    owner_telefono = models.CharField(max_length=40, blank=True, default="")

    fecha_registro = models.DateTimeField(auto_now_add=True, null=True)

    def get_propietario_display(self):
        if self.propietario:
            return self.propietario
        return None

    def __str__(self):
        return f"{self.nombre or 'Sin nombre'} ({self.especie or 'Sin especie'})"


class Cita(models.Model):
    ESTADO_CHOICES = [
        ("Pendiente", "Pendiente"),
        ("Confirmada", "Confirmada"),
        ("Cancelada", "Cancelada"),
        ("Completada", "Completada"),
    ]

    paciente = models.ForeignKey(
        Paciente, on_delete=models.CASCADE, related_name="citas", db_column="id_paciente"
    )
    veterinario = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="citas", db_column="id_veterinario"
    )
    fecha = models.DateTimeField()
    fecha_fin = models.DateTimeField(null=True, blank=True)
    tipo = models.CharField(max_length=60, blank=True, default="")
    motivo = models.CharField(max_length=255, blank=True, default="")
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default="Pendiente")
    duracion = models.IntegerField(default=30, null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    observacion = models.TextField(blank=True, default="")
    fecha_observacion = models.DateTimeField(null=True, blank=True)
    veterinario_observacion = models.CharField(max_length=120, blank=True, default="")

    class Meta:
        ordering = ["-fecha"]

    def __str__(self):
        return f"Cita {self.id} - {self.estado}"


class HistoriaClinica(models.Model):
    paciente = models.ForeignKey(
        Paciente, on_delete=models.CASCADE, related_name="historias", db_column="id_paciente"
    )
    MOTIVO_CHOICES = [
        ("Consulta general", "Consulta general"),
        ("Vacunación", "Vacunación"),
        ("Control", "Control"),
        ("Urgencia", "Urgencia"),
        ("Cirugía", "Cirugía"),
        ("Desparasitación", "Desparasitación"),
        ("Baño y peluquería", "Baño y peluquería"),
        ("Examen de laboratorio", "Examen de laboratorio"),
        ("Otro", "Otro"),
    ]

    hc_numero = models.CharField(max_length=80, blank=True, default="")
    fecha = models.DateField()
    hora = models.CharField(max_length=10, blank=True, default="")
    motivo_consulta = models.CharField(max_length=100, choices=MOTIVO_CHOICES, blank=True, default="")

    # SOAP format
    subjetivo = models.TextField(blank=True, default="")         # S: Subjetivo (Anamnesis/Motivo)
    objetivo = models.TextField(blank=True, default="")          # O: Objetivo (Detalles del examen)
    interpretacion = models.TextField(blank=True, default="")    # I: Interpretación (Diagnóstico)
    plan_terapeutico = models.TextField(blank=True, default="")  # P: Plan terapéutico
    plan_diagnostico = models.TextField(blank=True, default="")  # P: Plan diagnóstico
    proximo_control = models.DateField(null=True, blank=True)
    examen_fisico_general = models.TextField(blank=True, default="")
    examen_fisico_especial = models.TextField(blank=True, default="")

    # Legacy fields (kept for backward compat)
    anamnesis_dieta = models.TextField(blank=True, default="")
    anamnesis_enfermedades_previas = models.TextField(blank=True, default="")
    anamnesis_esterilizado = models.CharField(max_length=20, blank=True, default="")
    anamnesis_num_partos = models.CharField(max_length=20, blank=True, default="")
    anamnesis_cirugias_previas = models.TextField(blank=True, default="")
    examen_fisico = models.TextField(blank=True, default="")
    diagnostico = models.TextField(blank=True, default="")
    tratamiento = models.TextField(blank=True, default="")
    observaciones = models.TextField(blank=True, default="")

    creado_por = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="historias_creadas"
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    ultima_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha", "-fecha_creacion"]

    def __str__(self):
        return f"HC {self.hc_numero or self.id}"


class Vacuna(models.Model):
    paciente = models.ForeignKey(
        Paciente, on_delete=models.CASCADE, related_name="vacunas"
    )
    nombre_vacuna = models.CharField(max_length=200)
    fecha = models.DateField()
    laboratorio = models.CharField(max_length=120, blank=True, default="")
    dosis = models.CharField(max_length=80, blank=True, default="")
    lote = models.CharField(max_length=80, blank=True, default="")
    proxima_dosis = models.DateField(null=True, blank=True)
    veterinario = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL, null=True, blank=True, related_name="vacunas_aplicadas"
    )
    observaciones = models.TextField(blank=True, default="")
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha"]

    def __str__(self):
        return f"{self.nombre_vacuna} - {self.fecha}"


class Desparasitacion(models.Model):
    TIPO_CHOICES = [
        ("Interna", "Interna"),
        ("Externa", "Externa"),
        ("Interna y externa", "Interna y externa"),
    ]

    paciente = models.ForeignKey(
        Paciente, on_delete=models.CASCADE, related_name="desparasitaciones"
    )
    fecha = models.DateField()
    ultima_desparasitacion = models.DateField(null=True, blank=True)
    producto = models.CharField(max_length=200)
    tipo = models.CharField(max_length=30, choices=TIPO_CHOICES, default="Interna")
    dosis = models.CharField(max_length=80, blank=True, default="")
    proxima_fecha = models.DateField(null=True, blank=True)
    veterinario = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL, null=True, blank=True, related_name="desparasitaciones_aplicadas"
    )
    observaciones = models.TextField(blank=True, default="")
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha"]

    def __str__(self):
        return f"{self.producto} - {self.fecha}"


class Cirugia(models.Model):
    paciente = models.ForeignKey(
        Paciente, on_delete=models.CASCADE, related_name="cirugias"
    )
    fecha = models.DateField()
    nombre_cirugia = models.CharField(max_length=200)
    descripcion_quirurgica = models.TextField(blank=True, default="")
    preanestesico = models.TextField(blank=True, default="")
    anestesico = models.TextField(blank=True, default="")
    otros_medicamentos = models.TextField(blank=True, default="")
    tratamiento = models.TextField(blank=True, default="")
    observaciones = models.TextField(blank=True, default="")
    complicaciones = models.TextField(blank=True, default="")
    adjunto = models.FileField(upload_to="cirugias/", null=True, blank=True)
    veterinario = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="cirugias_realizadas"
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha"]

    def __str__(self):
        return f"{self.nombre_cirugia} - {self.fecha}"


class ExamenLaboratorio(models.Model):
    paciente = models.ForeignKey(
        Paciente, on_delete=models.CASCADE, related_name="examenes_laboratorio"
    )
    fecha = models.DateField()
    tipo_examen = models.CharField(max_length=120, blank=True, default="")
    descripcion = models.TextField(blank=True, default="")
    resultado = models.TextField(blank=True, default="")
    laboratorio = models.CharField(max_length=120, blank=True, default="")
    veterinario = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="examenes_solicitados"
    )
    adjunto = models.FileField(upload_to="examenes/", null=True, blank=True)
    observaciones = models.TextField(blank=True, default="")
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha"]

    def __str__(self):
        return f"{self.tipo_examen} - {self.fecha}"


class Seguimiento(models.Model):
    paciente = models.ForeignKey(
        Paciente, on_delete=models.CASCADE, related_name="seguimientos"
    )
    fecha = models.DateField()
    descripcion = models.TextField(blank=True, default="")
    evolucion = models.TextField(blank=True, default="")
    proximo_control = models.DateField(null=True, blank=True)
    adjunto = models.FileField(upload_to="seguimientos/", null=True, blank=True)
    veterinario = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="seguimientos_realizados"
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha"]

    def __str__(self):
        return f"Seguimiento {self.fecha}"


class Categoria(models.Model):
    nombre = models.CharField(max_length=120, unique=True)
    descripcion = models.CharField(max_length=255, blank=True, default="")
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Producto(models.Model):
    sku = models.CharField(max_length=40, unique=True)
    nombre = models.CharField(max_length=160)
    descripcion = models.TextField(blank=True, default="")
    categoria = models.ForeignKey(
        Categoria, on_delete=models.SET_NULL, null=True, blank=True, related_name="productos"
    )
    precio_compra = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    precio = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    stock = models.IntegerField(default=0)
    stock_minimo = models.IntegerField(default=0)
    activo = models.BooleanField(default=True)
    descuento_activo = models.BooleanField(default=False)
    descuento_porcentaje = models.IntegerField(default=0)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    ultima_actualizacion = models.DateTimeField(auto_now=True)

    @property
    def precio_con_descuento(self):
        from decimal import Decimal as _D
        if self.descuento_activo and self.descuento_porcentaje > 0:
            return self.precio * (_D(100) - _D(self.descuento_porcentaje)) / _D(100)
        return self.precio

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return f"{self.sku} - {self.nombre}"


class Venta(models.Model):
    ESTADO_CHOICES = [
        ("Pagada", "Pagada"),
        ("Anulada", "Anulada"),
    ]
    numero = models.CharField(max_length=20, unique=True)
    cliente = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL, null=True, blank=True, related_name="compras"
    )
    cliente_nombre = models.CharField(max_length=200, blank=True, default="")
    cliente_email = models.EmailField(blank=True, default="")
    cliente_documento = models.CharField(max_length=40, blank=True, default="")
    subtotal = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    impuestos = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    metodo_pago = models.CharField(max_length=40, default="Efectivo")
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default="Pagada")
    notas = models.TextField(blank=True, default="")
    creado_por = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL, null=True, blank=True, related_name="ventas_creadas"
    )
    fecha = models.DateTimeField(auto_now_add=True)
    factura_enviada = models.BooleanField(default=False)
    factura_enviada_at = models.DateTimeField(null=True, blank=True)
    factura_enviada_to = models.CharField(max_length=300, blank=True, default="")

    class Meta:
        ordering = ["-fecha"]

    def __str__(self):
        return f"Venta {self.numero}"


class VentaItem(models.Model):
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name="items")
    producto = models.ForeignKey(Producto, on_delete=models.SET_NULL, null=True, blank=True)
    nombre = models.CharField(max_length=160)
    sku = models.CharField(max_length=40, blank=True, default="")
    cantidad = models.IntegerField(default=1)
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    subtotal = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    precio_original = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)


class Receta(models.Model):
    numero = models.CharField(max_length=20, unique=True)
    paciente = models.ForeignKey(
        Paciente, on_delete=models.CASCADE, related_name="recetas"
    )
    veterinario = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL, null=True, blank=True, related_name="recetas_emitidas"
    )
    diagnostico = models.TextField(blank=True, default="")
    indicaciones = models.TextField(blank=True, default="")
    fecha = models.DateTimeField(auto_now_add=True)
    vigencia_dias = models.IntegerField(default=30)
    creado_por = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL, null=True, blank=True, related_name="recetas_creadas"
    )

    class Meta:
        ordering = ["-fecha"]

    def __str__(self):
        return f"Receta {self.numero}"


class RecetaItem(models.Model):
    receta = models.ForeignKey(Receta, on_delete=models.CASCADE, related_name="items")
    medicamento = models.CharField(max_length=200)
    presentacion = models.CharField(max_length=120, blank=True, default="")
    cantidad = models.CharField(max_length=40, blank=True, default="1")
    posologia = models.CharField(max_length=255, blank=True, default="")  # forma de administración
    dosis = models.CharField(max_length=120, blank=True, default="")
    via = models.CharField(max_length=80, blank=True, default="")
    frecuencia = models.CharField(max_length=120, blank=True, default="")
    duracion = models.CharField(max_length=80, blank=True, default="")
    observaciones = models.CharField(max_length=255, blank=True, default="")


class Orden(models.Model):
    PRIORIDAD_CHOICES = [
        ("Normal", "Normal"),
        ("Urgente", "Urgente"),
        ("Emergencia", "Emergencia"),
    ]
    paciente = models.ForeignKey(Paciente, on_delete=models.CASCADE, related_name="ordenes")
    fecha = models.DateField()
    tipo_orden = models.CharField(max_length=120, blank=True, default="")
    seleccion = models.CharField(max_length=200, blank=True, default="")
    cantidad = models.IntegerField(default=1)
    prioridad = models.CharField(max_length=20, choices=PRIORIDAD_CHOICES, blank=True, default="")
    notas = models.TextField(blank=True, default="")
    motivo = models.TextField(blank=True, default="")
    veterinario = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL, null=True, blank=True, related_name="ordenes_emitidas"
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha"]

    def __str__(self):
        return f"Orden {self.tipo_orden} - {self.fecha}"


class ImagenDiagnostica(models.Model):
    paciente = models.ForeignKey(Paciente, on_delete=models.CASCADE, related_name="imagenes_diagnosticas")
    fecha = models.DateField()
    ayuda_diagnostica = models.CharField(max_length=120, blank=True, default="")
    veterinario = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL, null=True, blank=True, related_name="imagenes_solicitadas"
    )
    signos_clinicos = models.TextField(blank=True, default="")
    diagnostico_presuntivo = models.TextField(blank=True, default="")
    tipo_estudio = models.TextField(blank=True, default="")
    observaciones = models.TextField(blank=True, default="")
    adjunto = models.FileField(upload_to="imagenes_diagnosticas/", null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha"]

    def __str__(self):
        return f"{self.ayuda_diagnostica} - {self.fecha}"


class Documento(models.Model):
    FIRMA_CHOICES = [("Si", "Si requiere"), ("No", "No requiere")]
    paciente = models.ForeignKey(Paciente, on_delete=models.CASCADE, related_name="documentos")
    tipo_documento = models.CharField(max_length=120, blank=True, default="")
    nombre_documento = models.CharField(max_length=200, blank=True, default="")
    requiere_firma = models.CharField(max_length=3, choices=FIRMA_CHOICES, default="No")
    contenido = models.TextField(blank=True, default="")
    adjunto = models.FileField(upload_to="documentos/", null=True, blank=True)
    fecha = models.DateField()
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha"]

    def __str__(self):
        return f"{self.nombre_documento} - {self.fecha}"


class Remision(models.Model):
    paciente = models.ForeignKey(Paciente, on_delete=models.CASCADE, related_name="remisiones")
    fecha = models.DateField()
    clinica_destino = models.CharField(max_length=200, blank=True, default="")
    motivo = models.TextField(blank=True, default="")
    diagnostico = models.TextField(blank=True, default="")
    observaciones = models.TextField(blank=True, default="")
    veterinario = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL, null=True, blank=True, related_name="remisiones_emitidas"
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha"]

    def __str__(self):
        return f"Remisión a {self.clinica_destino} - {self.fecha}"


class Peluqueria(models.Model):
    SERVICIO_CHOICES = [
        ("Baño", "Baño"),
        ("Corte de pelo", "Corte de pelo"),
        ("Baño y corte", "Baño y corte"),
        ("Corte de uñas", "Corte de uñas"),
        ("Limpieza dental", "Limpieza dental"),
        ("Deslanado", "Deslanado"),
        ("Spa completo", "Spa completo"),
        ("Otro", "Otro"),
    ]
    paciente = models.ForeignKey(Paciente, on_delete=models.CASCADE, related_name="peluquerias")
    fecha = models.DateField()
    servicio = models.CharField(max_length=40, choices=SERVICIO_CHOICES)
    precio = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    veterinario = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL, null=True, blank=True, related_name="peluquerias_realizadas"
    )
    observaciones = models.TextField(blank=True, default="")
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha"]

    def __str__(self):
        return f"{self.servicio} - {self.fecha}"


class AdjuntoArchivo(models.Model):
    """Archivos adjuntos múltiples para cualquier módulo clínico."""
    TIPO_CHOICES = [
        ("cirugia", "Cirugía"),
        ("examen", "Examen de laboratorio"),
        ("seguimiento", "Seguimiento"),
        ("consulta", "Consulta"),
        ("orden", "Orden"),
        ("remision", "Remisión"),
        ("peluqueria", "Peluquería"),
        ("imagen", "Imagen diagnóstica"),
        ("documento", "Documento"),
    ]
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    object_id = models.IntegerField()
    archivo = models.FileField(upload_to="adjuntos/%Y/%m/")
    nombre_original = models.CharField(max_length=255, blank=True, default="")
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["fecha_creacion"]

    def __str__(self):
        return f"{self.tipo}/{self.object_id} — {self.nombre_original}"


class TarifaCita(models.Model):
    DEFAULT_TIPOS = [
        ("Consulta general", 30000),
        ("Consulta especializada", 50000),
        ("Vacunación", 25000),
        ("Control y seguimiento", 20000),
        ("Peluquería básica", 15000),
        ("Peluquería completa", 30000),
        ("Baño y corte", 20000),
        ("Cirugía menor", 80000),
        ("Cirugía mayor", 200000),
        ("Urgencias", 60000),
        ("Desparasitación", 15000),
    ]

    CATEGORIA_CHOICES = [
        ("Medica", "Médica / Veterinaria"),
        ("Peluqueria", "Peluquería"),
    ]

    tipo = models.CharField(max_length=60, unique=True)
    categoria = models.CharField(max_length=20, choices=CATEGORIA_CHOICES, default="Medica")
    precio = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    descripcion = models.CharField(max_length=255, blank=True, default="")
    activo = models.BooleanField(default=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["tipo"]

    def __str__(self):
        return f"{self.tipo} — ${self.precio}"


class MovimientoInventario(models.Model):
    TIPO_CHOICES = [("Entrada", "Entrada"), ("Salida", "Salida"), ("Descuento", "Descuento")]
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name="movimientos")
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    cantidad = models.IntegerField(default=0)
    fecha = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL, null=True, blank=True, related_name="movimientos_inventario"
    )
    # Entry-specific fields
    nombre_factura = models.CharField(max_length=200, blank=True, default="")
    numero_factura = models.CharField(max_length=80, blank=True, default="")
    fecha_factura = models.DateField(null=True, blank=True)
    fecha_pago = models.DateField(null=True, blank=True)
    pago_pendiente = models.BooleanField(default=False)
    proveedor = models.CharField(max_length=200, blank=True, default="")
    nit_proveedor = models.CharField(max_length=40, blank=True, default="")
    archivo_factura = models.TextField(blank=True, null=True)
    # Exit-specific fields
    motivo = models.CharField(max_length=255, blank=True, default="")
    # General
    descuento_porcentaje = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    notas = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-fecha"]

    def __str__(self):
        return f"{self.tipo} - {self.producto.nombre} x{self.cantidad}"


class HistorialPrecio(models.Model):
    TIPO_CHOICES = [
        ("precio_venta", "Precio venta"),
        ("precio_compra", "Precio compra"),
        ("descuento_activado", "Descuento activado"),
        ("descuento_desactivado", "Descuento desactivado"),
    ]
    producto = models.ForeignKey(
        "Producto", on_delete=models.CASCADE, related_name="historial_precios"
    )
    tipo = models.CharField(max_length=30, choices=TIPO_CHOICES)
    precio_anterior = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    precio_nuevo = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    descuento_porcentaje = models.IntegerField(default=0)
    usuario = models.ForeignKey(
        "Usuario", on_delete=models.SET_NULL, null=True, blank=True
    )
    fecha = models.DateTimeField(auto_now_add=True)
    notas = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-fecha"]

    def __str__(self):
        return f"{self.producto.nombre} — {self.tipo} — {self.fecha:%d/%m/%Y}"


class Auditoria(models.Model):
    usuario = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL, null=True, blank=True, related_name="acciones"
    )
    accion = models.CharField(max_length=120)
    detalle = models.TextField(blank=True, default="")
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha"]




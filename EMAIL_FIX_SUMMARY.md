# Email Tariff Fix - COMPLETE ✓

## Problem Fixed

El email estaba mostrando:
- ❌ Valor de la cita: $0
- ❌ Concepto: "Consulta médica" (genérico)

Ahora muestra:
- ✅ Valor: Precio correcto de la tarifa seleccionada
- ✅ Concepto: Tipo exacto seleccionado (p.ej., "Cirugía mayor", "Consulta general", etc.)

## Root Cause

El código estaba buscando la tarifa por `cita.tipo` que contiene la categoría general ("Medica" o "Peluqueria"), cuando debería buscar por `cita.motivo` que contiene el tipo específico de tarifa.

## Changes Made

### File: `home/views/citas.py`

#### Function: `_build_appointment_pdf()`
- **Linea 491**: Cambio de `tipo=cita.tipo` a `tipo=cita.motivo`
- **Linea 516**: Cambio de `cita.tipo` a `cita.motivo` para mostrar el tipo de consulta
- **Linea 538**: Cambio de `"Consulta " + cita.tipo` a `cita.motivo` para el concepto

#### Function: `_send_appointment_reminder()`
- **Linea 595**: Cambio de `tipo=cita.tipo` a `tipo=cita.motivo`
- **Linea 608**: Cambio de `cita.tipo` a `cita.motivo` para el tipo de cita

## How It Works Now

### Flujo Actual:
1. Usuario selecciona categoría (Médica o Peluquería)
2. JavaScript carga tarifas dinámicas de esa categoría
3. Usuario selecciona tipo específico (p.ej., "Cirugía mayor")
4. El valor seleccionado se guarda en `cita.motivo`
5. Al crear la cita, se envía email con:
   - **Tarifa buscada por**: `cita.motivo` (tipo específico)
   - **Concepto en PDF**: El tipo exacto (p.ej., "Cirugía mayor")
   - **Precio**: El precio correcto de esa tarifa
   - **Tipo de Cita**: El tipo exacto seleccionado

## Data Flow

```
Usuario selecciona
"Cirugía mayor"
        ↓
Se guarda en cita.motivo = "Cirugía mayor"
        ↓
Al enviar email:
  tarifa = TarifaCita.objects.filter(tipo="Cirugía mayor").first()
  precio = $200,000
        ↓
Email muestra:
  Tipo de Consulta: Cirugía mayor
  Concepto: Cirugía mayor
  Valor: $200,000
```

## Test Results

✅ Python syntax validado
✅ Búsqueda de tarifas por motivo funciona
✅ Ejemplos probados:
   - Consulta general: $30,000
   - Baño y corte: $20,000
   - Todas las tarifas con acentos se encuentran correctamente

## What to Test

1. Crea una cita nueva
2. Selecciona "Médica" y elige "Cirugía mayor"
3. Completa el formulario y agendar
4. Abre el email y verifica:
   - ✓ Concepto: "Cirugía mayor" (no "Consulta médica")
   - ✓ Valor: "$200,000" (no "$0")
   - ✓ PDF adjunto tiene la información correcta

## Important Notes

- El cambio solo afecta la búsqueda de tarifas por email
- El formulario dinámico de tarifas sigue funcionando igual
- El campo `cita.tipo` sigue almacenando la categoría
- El campo `cita.motivo` ahora contiene el tipo específico
- Email incluye el precio correcto de cada tarifa

## Files Modified

- `home/views/citas.py` (2 funciones, 5 líneas totales)


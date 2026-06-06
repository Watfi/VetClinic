# Dynamic Tariff Loading - Implementation Complete ✓

## Summary of Changes

### 1. Backend Changes (`home/views/citas.py`)

#### Added to `add_cita()` view:
- Fetches all active tarifas from database
- Converts Decimal prices to float for JSON serialization
- Passes `tarifas_json` to template context
```python
tarifas = list(TarifaCita.objects.filter(activo=True).order_by("categoria", "tipo").values("tipo", "categoria", "precio"))
tarifas_serializable = [{**t, "precio": float(t["precio"])} for t in tarifas]
"tarifas_json": json.dumps(tarifas_serializable)
```

#### Added to `edit_cita()` view:
- Same tariff loading and JSON serialization as add_cita
- Ensures edit forms also have access to dynamic tarifas

### 2. Frontend Changes (`home/templates/appointments_form.html`)

#### HTML Structure:
- Removed hardcoded motivo options
- Left only the placeholder option: `<option value="">-- Selecciona un motivo --</option>`
- Added helper text with ID `motivoPriceHint`

#### JavaScript Implementation:
1. **Load TARIFAS_DATA** from template variable:
   ```javascript
   const TARIFAS_DATA = {{ tarifas_json|safe }};
   ```

2. **filterMotivos() function** now:
   - Filters tarifas by selected categoria (Medica or Peluqueria)
   - Dynamically generates option elements with:
     - `value` = tariff tipo
     - `textContent` = "tipo — $price"
     - `data-precio` = precio value
   - Handles empty state when no tarifas available
   - Restores previously selected motivo if it matches filtered category

3. **User Flow**:
   - User selects "🩺 Veterinaria" → Shows only Medica tarifas
   - User selects "✂️ Peluquería" → Shows only Peluqueria tarifas
   - Each option shows the tariff price
   - Motivo select only shows relevant options based on selected categoria

## Tarifas in Database

### Medical Services (Medica):
- Cirugía mayor: $200,000
- Cirugía menor: $80,000
- Consulta especializada: $50,000
- Consulta general: $30,000
- Control y seguimiento: $20,000
- Desparasitación: $15,000
- Urgencias: $60,000
- Vacunación: $25,000
- Prueba: $1 (test tariff)

### Grooming Services (Peluqueria):
- Baño y corte: $20,000
- Corte de Uñas: $20,000
- Peluquería básica: $15,000
- Peluquería completa: $30,000

## Testing

Run the following to verify tarifas load correctly:
```bash
python manage.py shell
from home.models import TarifaCita
tarifas = TarifaCita.objects.filter(activo=True).order_by('categoria', 'tipo')
for t in tarifas:
    print(f"{t.tipo} ({t.categoria}): ${t.precio}")
```

## How It Works

1. **Form Load**: View passes all active tarifas as JSON to template
2. **Type Selection**: User clicks "Médica" or "Peluquería" card
3. **Filtering**: JavaScript filterMotivos() is triggered
4. **Display**: Only tarifas matching selected categoria are shown
5. **Selection**: User selects motivo, which is a tariff from the selected category
6. **Email**: When appointment is created, the tariff price is included in the reminder email

## Files Modified

- `home/views/citas.py` - Added tariff JSON serialization to both add_cita and edit_cita
- `home/templates/appointments_form.html` - Replaced hardcoded motivo options with dynamic loading

## Next Steps

The dynamic tariff loading is complete. Users can now:
1. See all available tarifas from the database (organized by category)
2. Prices are displayed in the motivo dropdown
3. Email reminders include the correct tariff price
4. Appointment types are no longer hardcoded - they come from the tariff management system

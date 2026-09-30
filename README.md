# Fusion Checklist (multi-cliente)

Compara la configuración de Oracle Fusion Cloud entre las instancias de **cualquier cliente**
(PROD, TEST, DEV…, tantas como tenga) vía consultas SQL de BI Publisher.

Evolución genérica de [`fusion-checklist`](https://github.com/jrubioadies/fusion-checklist),
que estaba fijada a 4 entornos de un único cliente.

## Flujo

Al abrir la app aparece un asistente:

1. **Cliente** — elige un cliente guardado o crea uno nuevo.
2. **Instancias** — añade las instancias del cliente (nombre + URL) y marca cuáles comparar.
   «Evaluar» comprueba, sin credenciales, que la URL es una instancia Fusion con BI Publisher
   accesible, normaliza la URL y sugiere el nombre (`xxx-dev1.fa…` → `DEV1`).
3. **Usuarios y contraseñas** — usuario/contraseña por instancia. «Probar» valida el login y que
   el report ejecutor de SQL está desplegado, mostrando nº de ledgers, BUs y entidades legales.

Después, el comparador ejecuta los 39 items del checklist (GL, AP, AR, FA, CM, Compras,
Intercompany) contra las instancias marcadas, con vista de detalle, diferencias, filtro por BU,
export a Excel y delta FBDI/REST entre dos instancias.

## Checklists

En la barra de filtros se elige el checklist a comparar:

| Checklist | Origen | Tareas |
|---|---|---|
| **Financials** | `checklist.py` (GL, AP, AR, FA, CM, Compras, Intercompany) | 39 |
| **Service** | `checklists/service.json`, generado del implementation project `IMPLEMENTATION_PROJECT_1` (TEST) | 198 |

Los checklists de `checklists/*.json` se generan desde un implementation project de FSM:

```bash
python3 tools/fsm_checklist.py --project IMPLEMENTATION_PROJECT_1 --client <cliente> --env TEST \
    --name Service --out checklists/service.json --validate
```

El generador recorre las listas/tareas del proyecto y asigna a cada tarea su SQL de comprobación:

- **PERFIL** — profile options que gestiona la tarea según FSM (clave = `perfil [nivel] = valor`, así un valor distinto cuenta como diferencia)
- **LOOKUP** — lookup types de la tarea (`tipo.código (enabled)`)
- **PERFIL BU** — profiles por Business Unit de Service (`SVC_BU_PROFILE_VALUES`)
- **SQL** — consulta específica para objetos con tabla propia (tabla `MANUAL` del generador)
- **UI** — sin datos consultables (credenciales, IA, IDCS…): aparecen como revisión *manual*

`--validate` ejecuta cada conteo y pasa a UI las SQL que fallen en la instancia.

## Arranque

```bash
pip install -r requirements.txt
python app.py        # http://127.0.0.1:8900
```

## Dónde se guarda cada cosa

| Qué | Dónde |
|---|---|
| Perfil del cliente (instancias, usuarios, report SQL, origen/destino FBDI) | `~/.config/fusion-checklist/clients/<cliente>.json` (chmod 600) |
| Contraseñas | Llavero del sistema vía `keyring` (servicio `fusion-checklist`, cuenta `<cliente>/<instancia>`) |

Si `keyring` no está disponible las contraseñas solo se mantienen en memoria durante la sesión.

## Requisito en cada instancia

Las consultas se ejecutan mediante el report `/Custom/SQLTools/SQLConReport.xdo` sobre el data
model `SQLConDM`. Si «Probar» indica que no existe, hay que desplegarlo en esa instancia
(`fusion-client setup`) o indicar otra ruta en *Opciones avanzadas* del paso 1.

## Build ejecutable

```bash
bash build.sh      # Linux/macOS
build.bat          # Windows
```

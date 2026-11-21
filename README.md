# TFI Teoría de Control: control de velocidad de un ventilador de servidor

UTN FRBA · Tecnologías de Automatización (Teoría de Control) · K4521 · 2026-II
Alumnos: Matías Rainhart y Facundo Slaibe · Docente: Omar Civale

Simulación del lazo de velocidad de un ventilador de servidor (motor BLDC comandado por PWM, medición por tacómetro
Hall y controlador PI digital con período de 100 ms), usada en la memoria técnica del Trabajo Final Integrador.

## Recursos necesarios

- Python 3.9 o posterior (Windows, Linux o macOS).
- numpy y matplotlib: `pip install -r simulacion/requirements.txt`
- No requiere hardware.

## Cómo ejecutarlo

Desde la carpeta `simulacion`:

| Comando | Qué hace |
|---|---|
| `python tablero.py` | Tablero en tiempo real con las seis señales del lazo. Permite mover la temperatura, la tensión, la fricción y las ganancias, trabar el rotor y pasar de PI a P. |
| `python escenarios.py` | Corre los 8 escenarios de la memoria técnica, guarda los gráficos en `figuras/` y los valores medidos en `resultados.json`. |
| `python analisis.py` | Linealización, diseño del PI, arreglo de Routh y constantes de error. |

## Archivos

- `modelo.py`: parámetros, modelo del ventilador, medición por tacómetro, controlador PI y supervisión.
- `escenarios.py`, `tablero.py`, `analisis.py`: ver la tabla anterior.
- `diagrama_bloques.py`, `senales_pwm_tacometro.py`: generan dos figuras de la memoria técnica.

## Para probar en el tablero

- Poner Ki = 0: aparece el error permanente (sistema de Tipo 0).
- Con la temperatura en 20 °C, multiplicar Kp por 4 (≈ 0,18): oscilación sostenida, el límite lo impone el muestreo.
- Bajar la tensión a 10,8 V o subir el par adicional: el error vuelve a cero y el PWM queda más alto.
- Trabar el rotor: la medición cae a 0 y a los 2 s entra el modo seguro.

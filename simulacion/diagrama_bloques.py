"""Genera la Figura 2 del informe: diagrama de bloques del lazo de velocidad (con el punto
suma por donde ingresan las perturbaciones)."""
import os
import logging
import matplotlib
matplotlib.use('Agg')
logging.getLogger('matplotlib.font_manager').setLevel(logging.ERROR)
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Circle, Rectangle

plt.rcParams['font.family'] = ['Carlito', 'DejaVu Sans']
AZ, FONDO, NAR, FN, ROJO, GRIS = '#1F4E79', '#E9EFF8', '#B5650D', '#FFF3E0', '#A52A2A', '#555555'

fig, ax = plt.subplots(figsize=(11, 5.0))
ax.set_xlim(0, 120)
ax.set_ylim(0, 55)
ax.axis('off')


def bloque(x, y, w, h, titulo, cuerpo, fc=FONDO, ec=AZ, tc=AZ):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0.25,rounding_size=0.6',
                                fc=fc, ec=ec, lw=2))
    ax.text(x + w / 2, y + h - 2.0, titulo, ha='center', va='top', fontsize=11.5, color=tc, fontweight='bold')
    ax.text(x + w / 2, y + h - 4.6, cuerpo, ha='center', va='top', fontsize=10.5, linespacing=1.2)


def flecha(x0, y0, x1, y1=None, c='k', lw=2.0):
    y1 = y0 if y1 is None else y1
    ax.annotate('', xy=(x1, y1), xytext=(x0, y0),
                arrowprops=dict(arrowstyle='-|>', color=c, lw=lw, mutation_scale=16, shrinkA=0, shrinkB=0))


def linea(xs, ys, c='k', lw=2.0):
    ax.plot(xs, ys, color=c, lw=lw, solid_capstyle='butt')


YL = 30.0   # altura de la línea principal
FS = 10.5
# Referencia
bloque(1, 23.5, 14, 13, 'Referencia', 'Generador de\nconsigna (BMC,\nlazo térmico)')
ax.text(8, 50, 'Temperatura\n[°C]', ha='center', va='center', fontsize=FS)
flecha(8, 46.5, 8, 36.8)
# Comparador
cx = 24.5
ax.add_patch(Circle((cx, YL), 1.9, fc='white', ec=AZ, lw=2))
ax.plot([cx - 1.35, cx + 1.35], [YL - 1.35, YL + 1.35], color=AZ, lw=1.6)
ax.plot([cx - 1.35, cx + 1.35], [YL + 1.35, YL - 1.35], color=AZ, lw=1.6)
flecha(15.25, YL, cx - 1.9)
ax.text(19.0, YL + 1.0, 'θi\n[rpm]', ha='center', va='bottom', fontsize=FS)
ax.text(cx - 3.2, YL - 3.6, '+', fontsize=13, fontweight='bold')
ax.text(cx + 0.8, YL - 4.8, '−', fontsize=15, fontweight='bold')
ax.text(cx - 1, YL + 7.8, 'Comparador', ha='center', fontsize=9.5, color=GRIS)
# Controlador (punteado)
ax.add_patch(Rectangle((32.0, 19.0), 37.0, 21.5, fill=False, ec='#2E75B6', lw=1.8, ls=(0, (5, 3))))
ax.text(50.5, 17.8, 'Controlador (amplificador de error)', ha='center', va='top', fontsize=FS,
        color='#2E75B6', fontweight='bold')
bloque(35, 23.5, 11.5, 13, 'Control', 'Algoritmo PI\n(EMC2305)')
flecha(cx + 1.9, YL, 34.75, YL)
ax.text(29.6, YL + 1.0, 'e\n[rpm]', ha='center', va='bottom', fontsize=FS)
bloque(51.5, 23.5, 15.5, 13, 'Corrección', 'Generador PWM\n25 kHz + driver\ndel ventilador')
flecha(46.75, YL, 51.25, YL)
ax.text(49.0, YL + 1.0, 'u\n[%]', ha='center', va='bottom', fontsize=FS)
# Alimentación
ax.text(59.25, 51, 'Alimentación 12 V CC\n(perturbación ΔV)', ha='center', va='center', fontsize=FS, color=GRIS)
flecha(59.25, 47.8, 59.25, 36.8, c=GRIS)
# Proceso
bloque(76, 23.5, 12, 13, 'Proceso', 'Motor BLDC\n+ hélice')
flecha(67.25, YL, 75.75, YL)
ax.text(72.6, YL + 1.0, 'V media\n[V]', ha='center', va='bottom', fontsize=FS)
# Punto suma de perturbaciones
sx = 93.0
ax.add_patch(Circle((sx, YL), 2.0, fc='white', ec=ROJO, lw=2))
ax.text(sx, YL, 'Σ', ha='center', va='center', fontsize=12.5, color=ROJO, fontweight='bold')
flecha(88.25, YL, sx - 2.0)
ax.text(sx - 3.6, YL + 0.9, '+', fontsize=12, fontweight='bold')
ax.text(sx + 0.9, YL + 2.0, '−', fontsize=14, fontweight='bold', color=ROJO)
ax.text(sx, 51, 'Perturbaciones: fricción,\npolvo, obstrucción del flujo', ha='center', va='center',
        fontsize=FS, color=ROJO)
flecha(sx, 47.8, sx, YL + 2.0, c=ROJO)
# Salida y carga
flecha(sx + 2.0, YL, 105.75, YL)
ax.plot(99.0, YL, 'o', color='k', ms=6)
ax.text(100.5, YL + 1.0, 'θo\n[rpm]', ha='center', va='bottom', fontsize=FS)
bloque(106, 23.5, 13.2, 13, 'Carga', 'Caudal de aire\nhacia CPU,\nRAM y discos', fc=FN, ec=NAR, tc=NAR)
# Realimentación
bloque(45, 1.5, 30, 10.5, 'Elemento de medición', 'Sensor Hall (2 pulsos por vuelta) +\nmedición de período (EMC2305)')
linea([99.0, 99.0, 75.6], [YL, 6.8, 6.8])
flecha(76.0, 6.8, 75.25, 6.8)
ax.text(87.5, 7.6, 'giro del eje', ha='center', va='bottom', fontsize=FS)
linea([44.75, cx, cx], [6.8, 6.8, 20])
flecha(cx, 20, cx, YL - 1.9)
ax.text(34.0, 7.6, 'f: velocidad medida [rpm]', ha='center', va='bottom', fontsize=FS)

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'figuras', 'fig_diagrama_bloques.png')
fig.savefig(out, dpi=200, bbox_inches='tight', pad_inches=0.05)

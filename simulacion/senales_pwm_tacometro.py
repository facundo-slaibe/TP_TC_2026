"""Genera la figura de las señales PWM y de tacómetro (relación entre señales analógicas y digitales)."""
import os
import logging
import numpy as np
import matplotlib
matplotlib.use('Agg')
logging.getLogger('matplotlib.font_manager').setLevel(logging.ERROR)
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

plt.rcParams.update({'font.family': ['Carlito', 'DejaVu Sans'], 'font.size': 10,
                     'axes.spines.top': False, 'axes.spines.right': False})
COMA = FuncFormatter(lambda x, _: f'{x:g}'.replace('.', ','))
fig, ax = plt.subplots(2, 1, figsize=(7.2, 4.2))

t = np.linspace(0, 120, 4000)              # microsegundos, período PWM 40 us (25 kHz)
for k, d in enumerate((0.25, 0.50, 0.75)):
    y0 = 3.4 - 1.7 * k
    pwm = ((t % 40) < 40 * d).astype(float)
    ax[0].plot(t, y0 + pwm, color='#1F4E79', lw=1.4)
    ax[0].hlines(y0 + d, 0, 120, color='#B22222', ls='--', lw=1)
    ax[0].text(123, y0 + 0.5, f'ciclo {d * 100:.0f} %: valor medio {d:.2f}'.replace('.', ','), va='center', fontsize=9)
ax[0].set_yticks([])
ax[0].set_xlim(0, 160)
ax[0].set_xticks(range(0, 121, 20))
ax[0].spines['bottom'].set_bounds(0, 120)
ax[0].set_xlabel('Tiempo [µs] (período de 40 µs, 25 kHz)')
ax[0].set_title('a) Señal de control PWM: el ciclo de trabajo fija la tensión media aplicada al motor', loc='left')

t = np.linspace(0, 80, 4000)               # milisegundos
for k, (n, per) in enumerate(((1500, 20), (3000, 10))):
    y0 = 1.7 - 1.7 * k
    tach = (((t % per) < per / 2)).astype(float)
    ax[1].plot(t, y0 + tach, color='#548235', lw=1.4)
    ax[1].text(83, y0 + 0.5, f'{n} rpm: {2 * n // 60} Hz (período {per} ms)', va='center', fontsize=9)
ax[1].set_yticks([])
ax[1].set_xlim(0, 115)
ax[1].set_xticks(range(0, 81, 20))
ax[1].spines['bottom'].set_bounds(0, 80)
ax[1].set_xlabel('Tiempo [ms]')
ax[1].set_title('b) Señal del tacómetro: 2 pulsos por vuelta, frecuencia proporcional a la velocidad', loc='left')
for a in ax:
    a.xaxis.set_major_formatter(COMA)
fig.tight_layout(h_pad=1.2)
fig.savefig(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'figuras', 'fig_pwm_tacometro.png'),
            dpi=200, bbox_inches='tight')

"""
tablero.py - Tablero de control en tiempo real del lazo de velocidad del ventilador.

Cada cuadro avanza un período del controlador (100 ms) con la misma física y el mismo
PI de modelo.py, así que el tablero corre a velocidad real. Muestra las seis señales del
lazo (referencia, error, salida del controlador, respuesta, medición y perturbaciones)
y permite intervenir en vivo:

  - Temperatura del aire de entrada (genera la consigna por la curva térmica del BMC)
  - Tensión de alimentación (perturbación ΔV)
  - Par resistente adicional (fricción, polvo, obstrucción)
  - Kp y Ki (para ver qué pasa al sacar la acción integral o subir la ganancia)
  - Botones: trabar/liberar el rotor, P / PI, reiniciar

Uso:
    python tablero.py                       (ventana interactiva)
    python tablero.py --captura archivo.png (corre un guion de 60 s y guarda una captura)
"""
import sys
from collections import deque
import numpy as np
import matplotlib
if '--captura' in sys.argv:
    matplotlib.use('Agg')
import logging
logging.getLogger('matplotlib.font_manager').setLevel(logging.ERROR)
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button
from matplotlib.animation import FuncAnimation
import modelo as m

VENTANA = 30.0                       # segundos visibles
N = int(VENTANA / m.T)
plt.rcParams.update({'font.family': ['Carlito', 'DejaVu Sans'], 'font.size': 9,
                     'axes.grid': True, 'grid.alpha': 0.3})


class Tablero:
    def __init__(self):
        self.fig = plt.figure(figsize=(13, 8.2))
        self.fig.canvas.manager.set_window_title('TFI Teoría de Control - Lazo de velocidad del ventilador') \
            if hasattr(self.fig.canvas, 'manager') and self.fig.canvas.manager else None
        gs = self.fig.add_gridspec(6, 2, width_ratios=[3.2, 1], left=0.06, right=0.98,
                                   top=0.93, bottom=0.06, hspace=0.55, wspace=0.12)
        self.ax = [self.fig.add_subplot(gs[i, 0]) for i in range(6)]
        titulos = ['Referencia θi [rpm] (consigna del BMC)', 'Error e = θi − f [rpm]',
                   'Salida del controlador u [% PWM]', 'Respuesta θo: velocidad real [rpm]',
                   'Señal de medición f: tacómetro [rpm]', 'Perturbaciones: V alim. [V] / par adicional [mN·m]']
        for a, tt in zip(self.ax, titulos):
            a.set_title(tt, loc='left', fontsize=9)
            a.set_xlim(-VENTANA, 0)
        self.ax[-1].set_xlabel('Tiempo relativo [s]')
        cols = ['#1F4E79', '#B22222', '#C55A11', '#548235', '#7030A0', '#7F7F7F']
        self.lin = [a.plot([], [], color=c, lw=1.4)[0] for a, c in zip(self.ax, cols)]
        self.lin_ref_d = self.ax[3].plot([], [], color='#1F4E79', lw=0.8, ls='--')[0]
        self.ax5b = self.ax[5].twinx()
        self.lin_par = self.ax5b.plot([], [], color='#B22222', lw=1.4)[0]
        self.ax[0].set_ylim(700, 3200)
        self.ax[1].set_ylim(-1600, 1600)
        self.ax[2].set_ylim(-5, 105)
        self.ax[3].set_ylim(0, 3200)
        self.ax[4].set_ylim(0, 3200)
        self.ax[5].set_ylim(10.3, 12.8)
        self.ax5b.set_ylim(-0.1, 2.0)
        self.ax[1].axhline(0, color='k', lw=0.6)

        # panel de estado
        self.ax_txt = self.fig.add_subplot(gs[0:2, 1])
        self.ax_txt.axis('off')
        self.txt = self.ax_txt.text(0, 1, '', va='top', family='DejaVu Sans Mono', fontsize=8.5)

        # controles
        x0, w = 0.765, 0.19
        def slider(y, lab, a, b, v, fmt):
            axs = self.fig.add_axes([x0 + 0.04, y, w - 0.085, 0.025])
            return Slider(axs, lab, a, b, valinit=v, valfmt=fmt)
        self.s_temp = slider(0.53, 'T aire', 15, 36, 22.0, '%.1f °C')
        self.s_v = slider(0.48, 'V alim', 10.5, 12.6, 12.0, '%.2f V')
        self.s_par = slider(0.43, 'Par adic', 0, 1.8, 0.0, '%.2f mN·m')
        self.s_kp = slider(0.38, 'Kp', 0, 0.20, m.KP, '%.3f')
        self.s_ki = slider(0.33, 'Ki', 0, 0.50, m.KI, '%.3f')
        self.b_trabar = Button(self.fig.add_axes([x0, 0.25, w / 2 - 0.005, 0.045]), 'Trabar rotor')
        self.b_modo = Button(self.fig.add_axes([x0 + w / 2 + 0.005, 0.25, w / 2 - 0.005, 0.045]), 'Pasar a solo P')
        self.b_reset = Button(self.fig.add_axes([x0, 0.19, w, 0.045]), 'Reiniciar (ventilador detenido)')
        self.b_trabar.on_clicked(self.trabar)
        self.b_modo.on_clicked(self.modo)
        self.b_reset.on_clicked(lambda _: self.reiniciar())
        self.fig.suptitle('Lazo de velocidad del ventilador: PI digital (T = 100 ms) sobre motor BLDC con '
                          'medición por tacómetro Hall', fontsize=11)
        self.reiniciar()

    def reiniciar(self):
        self.lazo = m.Lazo(0.0)
        self.buf = {k: deque([np.nan] * N, maxlen=N) for k in ('ref', 'e', 'u', 'n', 'f', 'v', 'par')}

    def trabar(self, _):
        self.lazo.trabado = not self.lazo.trabado
        if not self.lazo.trabado:
            self.lazo.reiniciar_supervision()
        self.b_trabar.label.set_text('Liberar rotor' if self.lazo.trabado else 'Trabar rotor')

    def modo(self, _):
        self.lazo.pi.solo_p = not self.lazo.pi.solo_p
        self.b_modo.label.set_text('Volver a PI' if self.lazo.pi.solo_p else 'Pasar a solo P')

    def paso(self, _=None):
        self.lazo.pi.kp, self.lazo.pi.ki = self.s_kp.val, self.s_ki.val
        par = self.s_par.val / 1000.0
        reg, _f = self.lazo.ciclo(self.s_temp.val, self.s_v.val, par)
        for k in ('ref', 'e', 'u', 'n', 'f'):
            self.buf[k].append(reg[k])
        self.buf['v'].append(self.s_v.val)
        self.buf['par'].append(self.s_par.val)
        x = np.linspace(-VENTANA + m.T, 0, N)
        for ln, k in zip(self.lin, ('ref', 'e', 'u', 'n', 'f', 'v')):
            ln.set_data(x, list(self.buf[k]))
        self.lin_ref_d.set_data(x, list(self.buf['ref']))
        self.lin_par.set_data(x, list(self.buf['par']))
        e_pct = abs(reg['e']) / reg['ref'] * 100 if reg['ref'] else 0
        zona = ('FALLA' if reg['falla'] else 'ALERTA' if reg['alerta'] else
                'normal' if e_pct <= 2 else 'admisible' if e_pct <= 10 else 'fuera de rango')
        self.txt.set_text(
            f"t = {reg['t']:7.1f} s\n\n"
            f"Consigna θi   {reg['ref']:7.0f} rpm\n"
            f"Medición f    {reg['f']:7.0f} rpm\n"
            f"Velocidad θo  {reg['n']:7.0f} rpm\n"
            f"Error e       {reg['e']:+7.0f} rpm ({e_pct:4.1f} %)\n"
            f"PWM u         {reg['u']:7.1f} %\n"
            f"Caudal aprox. {reg['n'] / 3000 * 186.7:7.1f} m³/h\n\n"
            f"Ley de control: {'P' if self.lazo.pi.solo_p else 'PI'}\n"
            f"Zona de error:  {zona}\n"
            f"Pulsos tacóm.:  {'sí' if reg['pulsos'] else 'NO'}\n"
            f"Modo seguro:    {'ACTIVO' if reg['falla'] else 'no'}")
        self.txt.set_color('#B22222' if (reg['falla'] or reg['alerta']) else 'black')
        return self.lin


def captura(ruta):
    """Guion de demostración: arranque, escalón de temperatura, caída de tensión, fricción y falla."""
    tb = Tablero()
    guion = [(0, 'temp', 20.0), (6, 'temp', 27.0), (13, 'v', 10.8), (19, 'par', 0.9),
             (24, 'temp', 25.0), (29, 'trabar', None)]
    t = 0.0
    while t < 33.0:
        for (tt, k, v) in guion:
            if abs(t - tt) < 1e-6:
                if k == 'temp':
                    tb.s_temp.set_val(v)
                elif k == 'v':
                    tb.s_v.set_val(v)
                elif k == 'par':
                    tb.s_par.set_val(v)
                elif k == 'trabar':
                    tb.trabar(None)
        tb.paso()
        t = round(t + m.T, 10)
    tb.fig.savefig(ruta, dpi=150)


if __name__ == '__main__':
    if '--captura' in sys.argv:
        captura(sys.argv[sys.argv.index('--captura') + 1])
    else:
        tb = Tablero()
        anim = FuncAnimation(tb.fig, tb.paso, interval=int(m.T * 1000), blit=False, cache_frame_data=False)
        plt.show()

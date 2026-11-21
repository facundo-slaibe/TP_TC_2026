"""
escenarios.py - Corre los escenarios de la Tabla 17 del informe, genera los gráficos
(las seis señales del lazo) y guarda las métricas medidas en resultados.json.

Uso:  python escenarios.py            (crea la carpeta ./figuras)
Requiere numpy y matplotlib.
"""
import json
import os
import numpy as np
import logging
import matplotlib
logging.getLogger('matplotlib.font_manager').setLevel(logging.ERROR)
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import modelo as m

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'figuras')
os.makedirs(OUT, exist_ok=True)

plt.rcParams.update({
    'font.family': ['Carlito', 'DejaVu Sans'], 'font.size': 10,
    'axes.titlesize': 10.5, 'axes.labelsize': 9.5, 'legend.fontsize': 8.5,
    'axes.grid': True, 'grid.alpha': 0.3, 'axes.spines.top': False, 'axes.spines.right': False,
    'figure.dpi': 110, 'savefig.dpi': 200,
})
COMA = FuncFormatter(lambda x, _: f'{x:g}'.replace('.', ','))
AZUL, NARANJA, VERDE, ROJO, GRIS, VIOLETA = '#1F4E79', '#C55A11', '#548235', '#B22222', '#7F7F7F', '#7030A0'


def comas(ax):
    ax.xaxis.set_major_formatter(COMA)
    ax.yaxis.set_major_formatter(COMA)


def guardar(fig, nombre):
    fig.savefig(os.path.join(OUT, nombre), bbox_inches='tight')
    plt.close(fig)


# ---------------------------------------------------------------------------
# Corrida encadenada: los escenarios 1 a 7 uno detrás de otro (0-150 s)
# ---------------------------------------------------------------------------
TRAMOS = [  # (inicio, fin, etiqueta)
    (0, 10, '1'), (10, 20, '2'), (30, 70, '3'), (80, 95, '4'),
    (100, 115, '5'), (115, 140, '6'), (140, 150, '7')]


def temp_encadenada(t):
    if t < 10:
        return 20.0                          # 1. arranque (consigna 900 rpm)
    if t < 20:
        return 27.0                          # 2. escalón 20 -> 27 °C (900 -> 1800 rpm)
    if t < 30:
        return 22.0
    if t < 70:
        return 22.0 + (t - 30) * 8.0 / 40.0  # 3. rampa 22 -> 30 °C en 40 s
    if t < 115:
        return 27.0                          # 4 y 5 a 1800 rpm
    if t < 130:
        return 34.0                          # 6. saturación (consigna 3000 rpm)
    return 25.0


def v_encadenada(t):
    return 10.8 if 80 <= t < 95 else 12.0   # 4. caída de 12 a 10,8 V


PAR_FRICCION = 0.30 * m.KA * (1800 / m.RPM_PER_RADS) ** 2   # +30 % del par resistente a 1800 rpm


def par_encadenado(t):
    return PAR_FRICCION if t >= 100 else 0.0   # 5. aumento de fricción (queda hasta el final)


def figura_seis_senales(r, nombre, titulo, tramos=None, xlim=None):
    """Las seis señales pedidas: referencia, error, salida del controlador, respuesta,
    señal de medición y perturbación."""
    fig, ax = plt.subplots(6, 1, figsize=(7.2, 10.2), sharex=True)
    t = r['t']
    ax[0].step(t, r['ref'], where='post', color=AZUL, lw=1.4)
    ax[0].set_ylabel('θi [rpm]')
    ax[0].set_title('a) Referencia θi (consigna del BMC)', loc='left')
    a0b = ax[0].twinx()
    a0b.plot(t, r['temp'], color=GRIS, lw=0.9, ls=':')
    a0b.set_ylabel('T aire [°C]', color=GRIS)
    a0b.tick_params(axis='y', colors=GRIS)
    a0b.spines['right'].set_visible(True)
    a0b.yaxis.set_major_formatter(COMA)

    ax[1].plot(t, r['e'], color=ROJO, lw=1.0)
    ax[1].axhline(0, color='k', lw=0.6)
    ax[1].set_ylabel('e [rpm]')
    ax[1].set_title('b) Error e = θi − f', loc='left')

    ax[2].step(t, r['u'], where='post', color=NARANJA, lw=1.2)
    ax[2].set_ylabel('u [% PWM]')
    ax[2].set_ylim(-5, 108)
    ax[2].set_title('c) Salida del controlador u (ciclo de trabajo del PWM)', loc='left')

    ax[3].plot(r['tc'], r['nc'], color=VERDE, lw=1.3, label='θo (velocidad real)')
    ax[3].step(t, r['ref'], where='post', color=AZUL, lw=0.8, ls='--', label='θi')
    ax[3].set_ylabel('θo [rpm]')
    ax[3].legend(loc='lower right', ncol=2)
    ax[3].set_title('d) Respuesta θo (velocidad real del ventilador)', loc='left')

    ax[4].step(t, r['f'], where='post', color=VIOLETA, lw=1.0)
    ax[4].set_ylabel('f [rpm]')
    ax[4].set_title('e) Señal de medición f (tacómetro Hall, leída cada 100 ms)', loc='left')

    ax[5].step(t, r['v'], where='post', color=GRIS, lw=1.3, label='Alimentación [V]')
    ax[5].set_ylabel('V alim. [V]')
    ax[5].set_ylim(10.4, 12.4)
    a5b = ax[5].twinx()
    a5b.step(t, r['par'] * 1000, where='post', color=ROJO, lw=1.3, label='Par resistente adicional [mN·m]')
    a5b.set_ylabel('par adic. [mN·m]', color=ROJO)
    a5b.tick_params(axis='y', colors=ROJO)
    a5b.spines['right'].set_visible(True)
    a5b.set_ylim(-0.1, 1.6)
    a5b.yaxis.set_major_formatter(COMA)
    if r['falla'].any():
        tf = t[np.argmax(r['falla'])]
        for a in ax:
            a.axvline(tf, color='k', lw=0.8, ls=':')
        ax[2].text(tf - 0.8, 50, 'modo\nseguro', ha='right', va='center', fontsize=8)
    h1, l1 = ax[5].get_legend_handles_labels()
    h2, l2 = a5b.get_legend_handles_labels()
    ax[5].legend(h1 + h2, l1 + l2, loc='center left', fontsize=8)
    ax[5].set_title('f) Perturbaciones: tensión de 12 V y par resistente (fricción / obstrucción)', loc='left')
    ax[5].set_xlabel('Tiempo [s]')

    for a in ax:
        comas(a)
        if tramos:
            for (i0, i1, et) in tramos:
                a.axvspan(i0, i1, color='#DDEBF7', alpha=0.45, lw=0)
    if tramos:
        for (i0, i1, et) in tramos:
            ax[1].text((i0 + i1) / 2, 0.86, et, transform=ax[1].get_xaxis_transform(),
                       ha='center', va='center', fontsize=9, fontweight='bold', color=AZUL,
                       bbox=dict(boxstyle='circle,pad=0.2', fc='white', ec=AZUL, lw=0.8))
    if xlim:
        ax[0].set_xlim(*xlim)
    fig.suptitle(titulo, fontsize=11, y=0.995)
    fig.tight_layout(h_pad=0.5)
    guardar(fig, nombre)


def ventana(r, t0, t1, clave='t'):
    return (r[clave] >= t0) & (r[clave] < t1)


P_EQ = None


def main():
    global P_EQ
    res = {}
    # equilibrio del controlador P con consigna 900 (punto de partida de la comparación P vs PI)
    pre = m.simular(15, lambda t: 20.0, n0=900, solo_p=True)
    P_EQ = float(pre['n'][-10:].mean())

    # ---------------- Corrida encadenada -----------------
    r = m.simular(150, temp_encadenada, v_encadenada, par_encadenado, n0=0.0, trabar_en=140.0)
    figura_seis_senales(r, 'fig_corrida_encadenada.png',
                        'Corrida encadenada de los escenarios 1 a 7 (0 a 150 s)', TRAMOS)

    def nfin(t0, t1):
        w = ventana(r, t1 - 1.0, t1)
        return float(np.mean(r['n'][w]))

    # 1. Arranque
    w = ventana(r, 0, 10, 'tc')
    fuera = np.where(np.abs(r['nc'][w] - 900) > 18)[0]
    t_llega = r['tc'][w][fuera[-1]]
    res['1_arranque'] = dict(n_max=float(r['nc'][w].max()), t_2pct=float(t_llega),
                             n_final=nfin(0, 10), u_final=float(r['u'][ventana(r, 9, 10)].mean()))
    # 2. Escalón 900 -> 1800 (con limitador)
    s, tr, ts = m.metricas_escalon({'tc': r['tc'][ventana(r, 10, 20, 'tc')],
                                    'nc': r['nc'][ventana(r, 10, 20, 'tc')]}, 10, 900, 1800)
    res['2_escalon'] = dict(Mp=s, tr=tr, ts=ts, e_final=float(r['e'][ventana(r, 19, 20)].mean()),
                            u_final=float(r['u'][ventana(r, 19, 20)].mean()))
    # 3. Rampa: error medio en el tramo lineal de 22 a 27 °C y de 27 a 30 °C
    w1 = ventana(r, 36, 55)
    w2 = ventana(r, 58, 70)
    res['3_rampa'] = dict(e_medio_1=float(r['e'][w1].mean()), e_medio_2=float(r['e'][w2].mean()),
                          pend_1=(1800 - 900) / 7 * 0.2, pend_2=(3000 - 1800) / 5 * 0.2,
                          e_final_70_80=float(r['e'][ventana(r, 78, 80)].mean()))
    # 4. Caída de tensión
    w = ventana(r, 80, 95, 'tc')
    res['4_tension'] = dict(n_min=float(r['nc'][w].min()), caida=1800 - float(r['nc'][w].min()),
                            u_antes=float(r['u'][ventana(r, 79, 80)].mean()),
                            u_despues=float(r['u'][ventana(r, 94, 95)].mean()),
                            n_final=nfin(80, 95))
    w = ventana(r, 95, 100, 'tc')
    res['4_tension']['n_max_vuelta'] = float(r['nc'][w].max())
    # 5. Fricción
    w = ventana(r, 100, 115, 'tc')
    res['5_friccion'] = dict(par_mNm=PAR_FRICCION * 1000, n_min=float(r['nc'][w].min()),
                             u_antes=float(r['u'][ventana(r, 99, 100)].mean()),
                             u_despues=float(r['u'][ventana(r, 114, 115)].mean()),
                             n_final=nfin(100, 115))
    # 6. Saturación
    w = ventana(r, 115, 130)
    t_al = r['t'][w][np.argmax(r['alerta'][w])] if r['alerta'][w].any() else None
    w2 = ventana(r, 130, 140, 'tc')
    res['6_saturacion'] = dict(n_max=float(r['nc'][ventana(r, 115, 130, 'tc')].max()),
                               u_max=float(r['u'][w].max()), e_final=float(r['e'][ventana(r, 129, 130)].mean()),
                               t_alerta=(t_al - 115) if t_al is not None else None,
                               ref_vuelta=1542.857, n_min_vuelta=float(r['nc'][w2].min()),
                               n_max_vuelta=float(r['nc'][w2].max()),
                               ts_vuelta=float(m.metricas_escalon({'tc': r['tc'][w2], 'nc': r['nc'][w2]},
                                                                  130, 3000, 1542.857)[2]))
    # 7. Falla
    w = ventana(r, 140, 150)
    t_sin = r['t'][w][np.argmax(~r['pulsos'][w])] - 140
    t_f = r['t'][w][np.argmax(r['falla'][w])] - 140 if r['falla'][w].any() else None
    res['7_falla'] = dict(t_sin_pulsos=float(t_sin), t_modo_seguro=t_f, u_final=float(r['u'][-1]))

    # Figura de la corrida encadenada, solo los primeros 2 escenarios ampliados
    figura_seis_senales(r, 'fig_arranque_escalon.png',
                        'Ampliación: arranque (1) y escalón de temperatura 20 → 27 °C (2)',
                        TRAMOS[:2], xlim=(0, 20))

    # ---------------- 2 bis: verificación del diseño (sin limitador de rampa) ---------
    m.RAMPA_MAX = 100.0
    puntos = [(800, 900), (900, 990), (1200, 1320), (1636, 1800), (1800, 1980), (2700, 2970)]
    verif = []
    for a, b in puntos:
        rr = m.simular(12, consigna=lambda t, a=a, b=b: a if t < 5 else b, n0=a)
        s, tr, _ = m.metricas_escalon(rr, 5, a, b)
        tt, nn = rr['tc'], rr['nc']
        mk = tt >= 5
        fuera = np.where(np.abs(nn[mk] - b) > 0.02 * (b - a))[0]
        ts = float((tt[mk] - 5)[fuera[-1]]) if len(fuera) else 0.0
        verif.append(dict(desde=a, hasta=b, Mp=s, tr=tr, ts=ts))
    res['verificacion_puntos'] = verif
    sin_lim = m.simular(10, lambda t: 20 if t < 2 else 27, n0=900)
    m.RAMPA_MAX = 25.0
    con_lim = m.simular(10, lambda t: 20 if t < 2 else 27, n0=900)
    solo_p = m.simular(10, lambda t: 20 if t < 2 else 27, n0=P_EQ, solo_p=True)  # equilibrio del P con consigna 900
    s1 = m.metricas_escalon(sin_lim, 2, 900, 1800)
    s2 = m.metricas_escalon(con_lim, 2, 900, 1800)
    res['escalon_comparado'] = dict(sin_limitador=s1, con_limitador=s2,
                                    p_n_final=float(solo_p['n'][-5:].mean()),
                                    p_n_inicial=float(solo_p['n'][15:20].mean()),
                                    p_e_final=float(solo_p['e'][-5:].mean()))

    # Figura: P frente a PI (reemplaza a la Figura 4 del informe)
    fig, ax = plt.subplots(2, 1, figsize=(6.6, 4.6), sharex=True, gridspec_kw={'height_ratios': [2.2, 1]})
    ax[0].step(con_lim['t'], con_lim['ref'], where='post', color=AZUL, ls='--', lw=1, label='Consigna θi')
    ax[0].plot(con_lim['tc'], con_lim['nc'], color=VERDE, lw=1.6,
               label=f"PI (Kp = {m.KP:g} ; Ki = {m.KI:g}): error final ≈ 0 rpm".replace('.', ','))
    ax[0].plot(solo_p['tc'], solo_p['nc'], color=NARANJA, lw=1.4, ls='-.',
               label=f"Solo P (Kp = {m.KP:g}): error final ≈ {res['escalon_comparado']['p_e_final']:.0f} rpm".replace('.', ','))
    ax[0].set_ylabel('Velocidad [rpm]')
    ax[0].legend(loc='center right')
    ax[0].set_title('Escalón de temperatura 20 → 27 °C (consigna 900 → 1800 rpm)', loc='left')
    ax[1].step(con_lim['t'], con_lim['u'], where='post', color=VERDE, lw=1.3, label='PI')
    ax[1].step(solo_p['t'], solo_p['u'], where='post', color=NARANJA, lw=1.2, ls='-.', label='Solo P')
    ax[1].set_ylabel('u [% PWM]')
    ax[1].set_xlabel('Tiempo [s]')
    ax[1].legend(loc='lower right', ncol=2)
    for a in ax:
        comas(a)
    fig.tight_layout()
    guardar(fig, 'fig_p_vs_pi.png')

    # Figura: efecto del limitador de rampa
    fig, ax = plt.subplots(2, 1, figsize=(6.6, 4.4), sharex=True, gridspec_kw={'height_ratios': [2, 1]})
    ax[0].step(con_lim['t'], con_lim['ref'], where='post', color=AZUL, ls='--', lw=1, label='Consigna θi')
    ax[0].plot(sin_lim['tc'], sin_lim['nc'], color=GRIS, lw=1.3,
               label=f'Sin limitador: Mp = {s1[0]:.1f} %, ts = {s1[2]:.2f} s'.replace('.', ','))
    ax[0].plot(con_lim['tc'], con_lim['nc'], color=VERDE, lw=1.6,
               label=f'Con limitador (25 %/ciclo): Mp = {s2[0]:.1f} %, ts = {s2[2]:.2f} s'.replace('.', ','))
    ax[0].set_ylabel('θo [rpm]')
    ax[0].legend(loc='lower right')
    ax[1].step(sin_lim['t'], sin_lim['u'], where='post', color=GRIS, lw=1.2)
    ax[1].step(con_lim['t'], con_lim['u'], where='post', color=VERDE, lw=1.4)
    ax[1].set_ylabel('u [% PWM]')
    ax[1].set_xlabel('Tiempo [s]')
    ax[0].set_xlim(1, 6)
    for a in ax:
        comas(a)
    fig.tight_layout()
    guardar(fig, 'fig_limitador.png')

    # ---------------- Ajuste de Kp: diseño analítico (0,053) vs. adoptado ----------------
    TI = m.KP / m.KI
    ajuste = {}
    for kp in (0.053, m.KP):
        peores = []
        for a, b in [(800, 900), (900, 990), (1200, 1320), (1636, 1800), (1800, 1980), (2700, 2970)]:
            vals = []
            for d in (0, 3, 7, 11, 15):            # distintas fases entre pulsos y muestreo
                m.RAMPA_MAX = 100.0
                rr = m.simular(10, consigna=lambda t, a=a, b=b, d=d: (a + d) if t < 4 else b, n0=a + d, kp=kp, ki=kp / TI)
                mk = rr['tc'] >= 4
                vals.append(max(0.0, (rr['nc'][mk].max() - b) / (b - a - d) * 100))
            peores.append(max(vals))
        ajuste[f'{kp:g}'] = peores
    m.RAMPA_MAX = 25.0
    res['ajuste_kp'] = ajuste
    m.RAMPA_MAX = 100.0
    fig, ax = plt.subplots(figsize=(6.6, 3.2))
    for kp, col, ls in ((0.053, ROJO, '-.'), (m.KP, VERDE, '-')):
        rr = m.simular(4, consigna=lambda t: 800 if t < 1 else 900, n0=800, kp=kp, ki=kp / TI)
        mk = rr['tc'] >= 0.5
        ax.plot(rr['tc'][mk], rr['nc'][mk], color=col, ls=ls, lw=1.6,
                label=f'Kp = {kp:g} %/rpm'.replace('.', ','))
    m.RAMPA_MAX = 25.0
    ax.step(rr['t'], rr['ref'], where='post', color=AZUL, ls='--', lw=1, label='Consigna θi')
    ax.set_xlim(0.5, 4)
    ax.set_xlabel('Tiempo [s]')
    ax.set_ylabel('θo [rpm]')
    ax.legend(loc='lower right')
    ax.set_title('Escalón de 800 a 900 rpm (zona de baja velocidad, sin limitador)', loc='left')
    comas(ax)
    fig.tight_layout()
    guardar(fig, 'fig_ajuste_kp.png')

    # ---------------- 6 bis: windup (forma incremental vs. posicional sin protección) -----
    def temp_sat(t):
        return 27.0 if t < 2 else (34.0 if t < 32 else 25.0)
    par_sat = lambda t: PAR_FRICCION
    v_sat = lambda t: 10.8
    u_eq = m.duty_equilibrio(1800, 10.8, PAR_FRICCION)
    inc = m.simular(45, temp_sat, v_sat, par_extra=par_sat, n0=1800, u0=u_eq)
    # para la forma posicional hay que precargar la suma con el punto de trabajo
    pos_ctrl = m.Lazo(1800, incremental=False, u0=u_eq)
    pos_ctrl.pi.suma = u_eq / m.KI
    S = {k: [] for k in ('t', 'ref', 'u', 'n')}
    tc, nc = [], []
    for _ in range(450):
        tt = pos_ctrl.t
        reg, fino = pos_ctrl.ciclo(temp_sat(tt), 10.8, PAR_FRICCION)
        for k in S:
            S[k].append(reg[k])
        for a, b in fino:
            tc.append(a); nc.append(b)
    pos = {k: np.array(v) for k, v in S.items()}
    pos['tc'], pos['nc'] = np.array(tc), np.array(nc)
    w_inc = inc['tc'] >= 32
    w_pos = pos['tc'] >= 32
    res['windup'] = dict(
        inc_n_max_post=float(inc['nc'][w_inc].max()), pos_n_max_post=float(pos['nc'][w_pos].max()),
        inc_t_desat=float(inc['t'][(inc['t'] >= 32) & (inc['u'] < 99.9)][0] - 32),
        pos_t_desat=float(pos['t'][(pos['t'] >= 32) & (pos['u'] < 99.9)][0] - 32),
        inc_ts=float(m.metricas_escalon({'tc': inc['tc'][w_inc], 'nc': inc['nc'][w_inc]}, 32, 2800, 1542.857)[2]),
        pos_ts=float(m.metricas_escalon({'tc': pos['tc'][w_pos], 'nc': pos['nc'][w_pos]}, 32, 2800, 1542.857)[2]),
        n_sat=float(inc['n'][(inc['t'] > 30) & (inc['t'] < 32)].mean()),
        t_alerta=float(inc['t'][inc['alerta']][0] - 2) if inc['alerta'].any() else None)
    fig, ax = plt.subplots(2, 1, figsize=(6.6, 4.6), sharex=True, gridspec_kw={'height_ratios': [2, 1]})
    ax[0].step(inc['t'], inc['ref'], where='post', color=AZUL, ls='--', lw=1, label='Consigna θi')
    ax[0].plot(inc['tc'], inc['nc'], color=VERDE, lw=1.6, label='PI incremental (con anti-windup)')
    ax[0].plot(pos['tc'], pos['nc'], color=ROJO, lw=1.3, ls='-.', label='PI posicional sin anti-windup')
    ax[0].set_ylabel('θo [rpm]')
    ax[0].legend(loc='upper right', fontsize=8)
    ax[0].set_title('Saturación: 34 °C con 10,8 V y fricción aumentada (2 a 32 s), regreso a 25 °C', loc='left')
    ax[1].step(inc['t'], inc['u'], where='post', color=VERDE, lw=1.4)
    ax[1].step(pos['t'], pos['u'], where='post', color=ROJO, lw=1.2, ls='-.')
    ax[1].set_ylabel('u [% PWM]')
    ax[1].set_xlabel('Tiempo [s]')
    for a in ax:
        comas(a)
    fig.tight_layout()
    guardar(fig, 'fig_windup.png')

    # ---------------- 3 bis: rampa con consigna actualizada en cada ciclo (verifica Kv) --------
    m_tbmc = m.T_BMC
    m.T_BMC = m.T
    rr = m.simular(40, lambda t: 22.0 + max(0.0, t - 5) * 0.2 if t < 30 else 27.0, n0=1157.14)
    m.T_BMC = m_tbmc
    w = (rr['t'] > 10) & (rr['t'] < 25)
    res['rampa_continua'] = dict(e_medio=float(rr['e'][w].mean()),
                                 desvio_real=float((rr['ref'] - rr['n'])[w].mean()),
                                 pendiente=(1800 - 900) / 7 * 0.2)

    with open(os.path.join(OUT, '..', 'resultados.json'), 'w') as fh:
        json.dump(res, fh, indent=1, default=float)
    print(json.dumps(res, indent=1, default=float))


if __name__ == '__main__':
    main()

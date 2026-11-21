"""
analisis.py - Cálculos del Anexo A (modelo linealizado, diseño del PI, Routh, error).
Todos los números del informe salen de acá. Solo requiere numpy.
"""
import json
import math
import numpy as np
import modelo as m


def linealizar(n0):
    """Linealiza la carga aerodinámica en n0 [rpm]. Devuelve parámetros del proceso."""
    w0 = n0 / m.RPM_PER_RADS
    b = 2 * m.KA * w0                                   # fricción viscosa equivalente [N m s]
    v0 = m.R * m.KA * w0 ** 2 / m.KT + m.KB * w0        # tensión media necesaria [V]
    den = np.polymul([m.L, m.R], [m.J, b])
    den[-1] += m.KT * m.KB
    polos = np.roots(den)
    g0 = m.KT / (m.R * b + m.KT * m.KB)                 # [rad/s / V]
    tau = m.R * m.J / (m.R * b + m.KT * m.KB)           # [s]
    k = g0 * m.RPM_PER_RADS * m.V_NOM / 100             # [rpm / %]
    tau_h = m.T / 2 + 60.0 / n0                          # retención del PWM + antigüedad de la vuelta medida
    return dict(n0=n0, w0=w0, b=b, v0=v0, duty0=v0 / m.V_NOM * 100, den=den.tolist(),
                polos=sorted(polos.real.tolist()), g0=g0, tau=tau, K=k, tau_h=tau_h)


def routh(coef):
    """Arreglo de Routh (lista de filas) para un polinomio de grado 3 o 4."""
    c = [float(x) for x in coef]
    f1, f2 = c[0::2], c[1::2]
    while len(f2) < len(f1):
        f2.append(0.0)
    filas = [f1, f2]
    while len(filas) < len(c):
        a, bb = filas[-2], filas[-1]
        nueva = []
        for j in range(len(a) - 1):
            nueva.append((bb[0] * a[j + 1] - a[0] * bb[j + 1]) / bb[0])
        nueva.append(0.0)
        filas.append(nueva)
    return filas


def lazo(p, kp, ki):
    """Polinomio característico (modelo reducido): tau tau_h s^3 + (tau+tau_h) s^2 + (1+Kp K) s + Ki K."""
    a3 = p['tau'] * p['tau_h']
    a2 = p['tau'] + p['tau_h']
    a1 = 1 + kp * p['K']
    a0 = ki * p['K']
    coef = [a3, a2, a1, a0]
    norm = [x / a3 for x in coef]
    return dict(coef=coef, norm=norm, routh=routh(norm), polos=np.roots(norm).tolist(),
                Kv=ki * p['K'], Kpos_P=kp * p['K'])


if __name__ == '__main__':
    out = {}
    # 1) modelo físico
    out['fisico'] = dict(R=m.R, L=m.L, J=m.J, Kb=m.KB, Ka=m.KA, Vnom=m.V_NOM)
    # 2) diseño en el punto más exigente (piso de la consigna, 900 rpm)
    p = linealizar(900)
    zeta = 0.7
    ti = p['tau']
    wn = 1 / (2 * zeta * p['tau_h'])
    kp = wn ** 2 * p['tau_h'] * p['tau'] / p['K']
    out['diseno'] = dict(p=p, zeta=zeta, wn=wn, Ti=ti, Kp=kp, Ki=kp / ti,
                         Mp=100 * math.exp(-zeta * math.pi / math.sqrt(1 - zeta ** 2)),
                         ts=4 / (zeta * wn),
                         tr=(math.pi - math.acos(zeta)) / (wn * math.sqrt(1 - zeta ** 2)))
    # 3) Routh y error con los valores redondeados que usa el código
    out['puntos'] = {}
    for n0 in (900, 1800, 2700):
        q = linealizar(n0)
        out['puntos'][n0] = dict(p=q, lazo=lazo(q, m.KP, m.KI))
    # polinomio completo (con el polo eléctrico) en 900 rpm: Ti s (den) (tau_h s + 1) + Kp K' (Ti s + 1)(...)
    q = out['puntos'][900]['p']
    kvolt = m.KT * m.RPM_PER_RADS * m.V_NOM / 100      # [rpm/% por unidad de den]
    ti_c = m.KP / m.KI
    car = np.polyadd(np.polymul(np.polymul([ti_c, 0], q['den']), [q['tau_h'], 1]),
                     np.polymul([m.KP * kvolt * ti_c, m.KP * kvolt], [1]))
    out['completo_900'] = dict(coef=car.tolist(), polos=np.roots(car).tolist())
    print(json.dumps(out, indent=1, default=lambda x: [x.real, x.imag] if isinstance(x, complex) else str(x)))

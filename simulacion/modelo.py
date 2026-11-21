"""
modelo.py - Modelo del lazo de velocidad de un ventilador de servidor (TFI Teoría de Control)

Rainhart, Matías - Slaibe, Facundo - UTN FRBA, K4521

Contiene, en un solo lugar, todos los parámetros que usa el informe (Anexo A):
  - Proceso: motor BLDC del ventilador + hélice (modelo de motor de CC con carga
    aerodinámica cuadrática), simulado en tiempo continuo con paso fino.
  - Elemento de medición: sensor Hall (2 pulsos/vuelta) + medición del período de una
    vuelta con un reloj de 32,768 kHz, como el EMC2305.
  - Controlador: PI digital incremental, período T = 100 ms, salida 0-100 % de PWM.
  - Generador de consigna: curva térmica del BMC (lazo externo), actualizada cada 1 s.
  - Supervisión: zonas de error (Tabla 10), detección de ventilador detenido y modo seguro.

Solo requiere numpy.
"""
import math
import numpy as np

# ---------------------------------------------------------------------------
# Parámetros físicos del ventilador (Anexo A, Tabla 18)
# ---------------------------------------------------------------------------
V_NOM = 12.0                      # tensión nominal de alimentación [V]
R = 10.0                          # resistencia del bobinado [ohm]
L = 5e-3                          # inductancia del bobinado [H]
J = 4e-5                          # inercia del rotor + aspas [kg m^2]
N_MAX = 3000.0                    # velocidad a 100 % de PWM y 12 V [rpm] (datasheet)
I_MAX = 0.30                      # corriente a 100 % (3,6 W / 12 V) [A] (datasheet)
W_MAX = N_MAX * 2 * math.pi / 60  # [rad/s]
KB = (V_NOM - R * I_MAX) / W_MAX  # constante de fem [V s/rad]
KT = KB                           # constante de par [N m/A] (SI: Kt = Kb)
KA = KT * I_MAX / W_MAX ** 2      # coeficiente de par aerodinámico [N m s^2] (par = KA w^2)

RPM_PER_RADS = 60 / (2 * math.pi)

# ---------------------------------------------------------------------------
# Controlador (Anexo A.2) y tiempos de muestreo
# ---------------------------------------------------------------------------
T = 0.100        # período de actualización del controlador (EMC2305) [s]
T_BMC = 1.0      # período del lazo térmico externo (BMC) [s]
KP = 0.045       # ganancia proporcional [% / rpm] (diseño analítico 0,053, ajustado por simulación)
KI = 0.111       # ganancia integral [% / (rpm s)]  (Ki = Kp / Ti, Ti = 0,406 s)
DT = 1e-3        # paso de integración de la planta [s]

# Medición de velocidad (EMC2305)
F_CLK = 32768.0  # reloj de medición del tacómetro [Hz]
T_STALL = 0.25   # si una vuelta tarda más que esto, se considera "sin pulsos" [s]

# Rutina de arranque (spin-up) y limitador de rampa
SPINUP_T = 0.5       # duración máxima del arranque [s] (termina antes si f >= 50 % de la consigna)
SPINUP_PWM = 50.0   # PWM durante el arranque [%]
RAMPA_MAX = 25.0     # máximo cambio de PWM por ciclo [%]

# Supervisión (Tabla 10)
ALERTA_PCT = 10.0    # |e| > 10 % de la consigna ...
ALERTA_T = 3.0       # ... sostenido durante 3 s -> alerta
FAILSAFE_T = 2.0     # sin lectura válida durante 2 s -> modo seguro (OpenBMC)
FAILSAFE_PWM = 100.0


def consigna_desde_temperatura(t_aire):
    """Curva térmica del BMC (Figura 3): temperatura del aire [°C] -> consigna [rpm]."""
    if t_aire <= 20.0:
        return 900.0
    if t_aire <= 27.0:
        return 900.0 + (t_aire - 20.0) * (1800.0 - 900.0) / 7.0
    if t_aire <= 32.0:
        return 1800.0 + (t_aire - 27.0) * (3000.0 - 1800.0) / 5.0
    return 3000.0


def duty_equilibrio(n, v_alim=V_NOM, par_extra=0.0):
    """PWM [%] que sostiene la velocidad n [rpm] en régimen (equilibrio de la planta no lineal)."""
    w = n / RPM_PER_RADS
    i = (KA * w * w + par_extra) / KT
    return (R * i + KB * w) / v_alim * 100


class Ventilador:
    """Proceso: motor BLDC + hélice. Estados: corriente i [A], velocidad w [rad/s], ángulo [rev]."""

    def __init__(self, n0=0.0):
        self.w = n0 / RPM_PER_RADS
        self.i = 0.0
        self.rev = 0.0
        self.trabado = False

    def paso(self, duty_pct, v_alim, par_extra, dt=DT):
        v_media = max(0.0, min(100.0, duty_pct)) / 100.0 * v_alim   # PWM -> tensión media
        # ecuación eléctrica (solución exacta de 1er orden con w constante en el paso)
        tau_e = L / R
        i_ss = (v_media - KB * self.w) / R
        self.i = i_ss + (self.i - i_ss) * math.exp(-dt / tau_e)
        if self.trabado:
            self.w = 0.0
            return
        # ecuación mecánica: J dw/dt = Kt i - Ka w^2 - par_extra (los pares resistentes se oponen al giro)
        par_res = KA * self.w * abs(self.w) + par_extra * (1 if self.w > 0 else 0)
        self.w += dt * (KT * self.i - par_res) / J
        if self.w < 0:
            self.w = 0.0
        self.rev += self.w / (2 * math.pi) * dt

    @property
    def rpm(self):
        return self.w * RPM_PER_RADS


class Tacometro:
    """Elemento de medición: sensor Hall + conteo de ciclos de 32,768 kHz durante una vuelta."""

    def __init__(self):
        self.ultima_vuelta = None     # instante en que se completó la última vuelta
        self.periodo = None           # duración de la última vuelta [s]
        self._rev_entera = 0

    def actualizar(self, t, rev, w):
        if int(rev) > self._rev_entera:
            # instante exacto del pulso (interpolado dentro del paso de integración)
            frac = rev - int(rev)
            t_pulso = t - (frac / (w / (2 * math.pi)) if w > 0 else 0.0)
            if self.ultima_vuelta is not None:
                self.periodo = t_pulso - self.ultima_vuelta
            self.ultima_vuelta = t_pulso
            self._rev_entera = int(rev)

    def leer(self, t):
        """Devuelve (velocidad medida [rpm], hay_pulsos)."""
        if self.periodo is None or self.ultima_vuelta is None:
            return 0.0, False
        if (t - self.ultima_vuelta) > T_STALL or self.periodo > T_STALL:
            return 0.0, False
        cuentas = max(1, round(self.periodo * F_CLK))        # cuantización temporal
        return 60.0 * F_CLK / cuentas, True


class ControladorPI:
    """PI digital. Forma incremental (con anti-windup natural) o posicional sin protección."""

    def __init__(self, kp=KP, ki=KI, incremental=True, solo_p=False, u0=0.0):
        self.kp, self.ki = kp, ki
        self.incremental = incremental
        self.solo_p = solo_p
        self.u = u0
        self.e_ant = 0.0
        self.suma = 0.0

    def calcular(self, e):
        if self.solo_p:
            u = self.kp * e
        elif self.incremental:
            # u(k) = u(k-1) + Kp [e(k) - e(k-1)] + Ki T e(k)
            u = self.u + self.kp * (e - self.e_ant) + self.ki * T * e
        else:
            # forma posicional sin anti-windup: la suma sigue acumulando aunque el PWM sature
            self.suma += e * T
            u = self.kp * e + self.ki * self.suma
        # limitador de rampa
        u = max(self.u - RAMPA_MAX, min(self.u + RAMPA_MAX, u))
        u = max(0.0, min(100.0, u))            # saturación del actuador
        self.u, self.e_ant = u, e
        return u


class Lazo:
    """
    Lazo de velocidad completo. Cada llamada a ciclo() avanza un período del controlador
    (100 ms): lee el tacómetro, calcula el error, aplica la ley PI y deja correr la planta.
    Lo usan tanto la corrida por escenarios (simular) como el tablero en tiempo real.
    """

    def __init__(self, n0=0.0, incremental=True, solo_p=False, kp=KP, ki=KI, u0=None):
        self.fan = Ventilador(n0)
        self.tach = Tacometro()
        if n0 > 0:                                   # ya venía girando: hay una vuelta medida
            self.tach.periodo = 60.0 / n0
            self.tach.ultima_vuelta = 0.0
        if u0 is None:
            u0 = 0.0 if n0 == 0 else duty_equilibrio(n0)   # arranca en equilibrio
        self.pi = ControladorPI(kp, ki, incremental, solo_p, u0=u0)
        self.u = u0
        self.t = 0.0
        self.k = 0
        self.ref = None
        self.spin_hasta = SPINUP_T if n0 == 0 else -1.0
        self.t_alerta = 0.0
        self.t_sin_lectura = 0.0
        self.alerta = False
        self.falla = False
        self.trabado = False

    def reiniciar_supervision(self):
        self.falla = self.alerta = False
        self.t_alerta = self.t_sin_lectura = 0.0

    def ciclo(self, temp_aire=None, v_alim=V_NOM, par_extra=0.0, consigna=None):
        """Avanza T = 100 ms. temp_aire o consigna definen la referencia."""
        t = self.t
        # lazo externo (BMC): la consigna se recalcula cada 1 s
        if self.ref is None or (self.k % int(round(T_BMC / T)) == 0):
            self.ref = consigna if consigna is not None else consigna_desde_temperatura(temp_aire)
        ref = self.ref
        # lazo interno (EMC2305)
        f, hay_pulsos = self.tach.leer(t)
        e = ref - f
        if t < self.spin_hasta and f >= 0.5 * ref:
            self.spin_hasta = t                     # el ventilador ya gira: termina el arranque
            self.pi.u, self.pi.e_ant = ref / N_MAX * 100, e   # precarga: PWM estimado para la consigna
        if t < self.spin_hasta:
            u = SPINUP_PWM                          # rutina de arranque
        elif self.falla:
            u = FAILSAFE_PWM                        # modo seguro
        else:
            u = self.pi.calcular(e)
        self.u = u
        # supervisión (Tabla 10)
        activo = t >= self.spin_hasta
        self.t_alerta = self.t_alerta + T if (activo and ref > 0 and abs(e) > ALERTA_PCT / 100 * ref) else 0.0
        self.alerta = self.t_alerta >= ALERTA_T
        self.t_sin_lectura = self.t_sin_lectura + T if (activo and not hay_pulsos) else 0.0
        if self.t_sin_lectura >= FAILSAFE_T:
            self.falla = True
        reg = dict(t=t, ref=ref, e=e, u=u, n=self.fan.rpm, f=f, alerta=self.alerta,
                   falla=self.falla, pulsos=hay_pulsos)
        # planta en tiempo continuo durante el período (paso fino)
        fino = []
        self.fan.trabado = self.trabado
        for j in range(int(round(T / DT))):
            self.fan.paso(u, v_alim, par_extra)
            self.tach.actualizar(t + (j + 1) * DT, self.fan.rev, self.fan.w)
            if j % 10 == 9:
                fino.append((t + (j + 1) * DT, self.fan.rpm))
        self.t = round(t + T, 10)
        self.k += 1
        return reg, fino


def simular(duracion, temp_aire=lambda t: 20.0, v_alim=lambda t: V_NOM,
            par_extra=lambda t: 0.0, n0=0.0, trabar_en=None, incremental=True,
            solo_p=False, consigna=None, kp=KP, ki=KI, u0=None):
    """
    Corre el lazo y devuelve un diccionario de arrays con las señales.
    temp_aire(t): temperatura del aire de entrada [°C] (entrada del lazo externo)
    consigna(t):  si se indica, reemplaza a la curva térmica (consigna directa en rpm)
    v_alim(t), par_extra(t): perturbaciones (tensión de 12 V [V] y par resistente adicional [N m])
    """
    lazo = Lazo(n0, incremental, solo_p, kp, ki, u0)
    S = {k: [] for k in ('t', 'ref', 'e', 'u', 'n', 'f', 'temp', 'v', 'par',
                         'alerta', 'falla', 'pulsos')}
    tc, nc = [], []
    for _ in range(int(round(duracion / T))):
        t = lazo.t
        if trabar_en is not None and t >= trabar_en:
            lazo.trabado = True
        reg, fino = lazo.ciclo(temp_aire(t), v_alim(t), par_extra(t),
                               consigna(t) if consigna else None)
        reg.update(temp=temp_aire(t), v=v_alim(t), par=par_extra(t))
        for key in S:
            S[key].append(reg[key])
        for a, b in fino:
            tc.append(a)
            nc.append(b)
    out = {k: np.array(v) for k, v in S.items()}
    out['tc'] = np.array(tc)
    out['nc'] = np.array(nc)
    return out


def metricas_escalon(res, t0, n_ini, n_fin, banda=0.02):
    """Sobrepico, tiempo de subida (10-90 %) y de establecimiento (banda) sobre la velocidad real."""
    t, n = res['tc'], res['nc']
    m = t >= t0
    t, n = t[m] - t0, n[m]
    dn = n_fin - n_ini
    sobre = max(0.0, (n.max() - n_fin) / dn * 100) if dn > 0 else max(0.0, (n_fin - n.min()) / -dn * 100)
    y = (n - n_ini) / dn
    try:
        tr = t[np.argmax(y >= 0.9)] - t[np.argmax(y >= 0.1)]
    except ValueError:
        tr = float('nan')
    fuera = np.where(np.abs(n - n_fin) > banda * abs(n_fin))[0]
    ts = t[fuera[-1]] if len(fuera) else 0.0
    return sobre, tr, ts

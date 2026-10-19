from math import pi
import math


def Re(V, l, nu=1.5 * 10 ** (-5)):
    '''Reynolds number calculation
    :param V: Flow velocity
    :param l: linear reference size
    :param nu: Dynamic viscosity
    :return: Reynolds number
    :rtype: float
    '''
    return int(V * l / nu)


def CL_required(V, S, m, rho=1.22):
    '''wing level flight lift coefficient calculation
    :param V: Airspeed
    :param S: reference area (wing area)
    :param m: mass (take-off mass)
    :param rho: Air density
    :return: CL
    :rtype: float
    '''
    return (2 * m * 9.81 / (rho * V ** 2 * S))


def CDi(CL, AR, osvald_coef=0.9):
    '''induced drag calculation according to lift line theory
    :param CL: lift coefficient
    :param AR: wing aspect ratio
    :param osvald_coef: Oswald efficiency number in induced drag coefficient formula by the lifting line theory.
    Depends from wing plan form.
    :return: CD induced
    :rtype: float
    '''
    return (CL ** 2 / (pi * osvald_coef * AR))


def wing_area(TOM, g, Density, take_off_speed, CL_take_off):
    '''wing area calculation from the take off parameters.

    Uses the CL max coefficient and take-off speed to evaluate required wing area.
    :param TOM: take-off mass
    :param g: free fall acceleration
    :return: wing area [m^2]
    :rtype: float
    '''
    return 2 * TOM * g / (Density * take_off_speed ** 2 * CL_take_off)


def CL_cruise(TOM, cruise_speed, wing_area, g, Density):
    '''From given mass, wing area and speed calculates lift coefficient of flight.
    '''
    return 2 * TOM * g / (Density * cruise_speed ** 2 * wing_area)


def wingspan(AR, wing_area):
    '''Calculates wingspan from given aspect ratio and wing area.
    '''
    return (AR * wing_area) ** 0.5


def ba(AR, wing_area):
    '''Calculates mean aerodynamic chord from given aspect ratio and wing area.
    '''
    return (wing_area / AR) ** 0.5


def aft_area(A_aft, wing_area, ba, l_stab):
    '''Calculates horizontal stabilyzer area.
    :param A_aft: static moment of horizontal stab.
    :ba: mean aerodynamic chord.
    :l_stab: syabylizer leverage.
    '''
    return A_aft * wing_area * ba / l_stab


def keel_area(B_keel, wing_area, wing_span, l_stab):
    '''Calculates vertical stabilyzer area.
    :param B_keel: static moment of vertical stab.
    :l_stab: syabylizer leverage.
    '''
    return B_keel * wing_area * wing_span / l_stab


def gamma(keel_area, aft_area):
    '''Calculates the divergency angle for Vee-tail.

    :param keel_area: area of equivalent vertical stab.
    :param aft_area: area of equivalent horizontal stab.
    '''
    return math.atan((keel_area / aft_area) ** 0.5)


def stab_area(aft_area, gamma):
    '''Calculates the area of Vee-tail.

    Angle between horizontal plane and Vee-stab.

    :param aft_area: area of equivalent horizontal stab.
    :param gamma: divergency angle of Vee-tail.
    '''
    return aft_area / (math.cos(gamma)) ** 2


def P_cruise(TOM, K_cruise, eta_prop, g):
    '''Calculates required thrust.
    :param TOM: mass.
    :K_cruise: aerodynamic efficiency.
    :eta_prop: propeller efficiency coefficient for particular conditions.
    '''
    return TOM * g / (K_cruise * eta_prop)


def wire_length(wingspan, l_stab, wire_scale_coef):
    '''Servo wire length estimation.
    Has to be changed for particular aircraft.
    '''
    return wingspan + 2 * wire_scale_coef * l_stab

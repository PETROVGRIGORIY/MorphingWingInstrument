import math


def wing_area(TOM, g, Density, take_off_speed, CL_take_off):
    '''wing area calculation from the take off parameters.

    Uses the CL max coefficient and take-off speed to evaluate required wing area.
    :param TOM: take-off mass
    :param g: free fall acceleration
    :return: wing area [m^2]
    :rtype: float
    '''
    return 2 * TOM * g / (Density * take_off_speed ** 2 * CL_take_off)


def wingspan(AR, wing_area):
    '''Calculates wingspan from given aspect ratio and wing area.
    '''
    return (AR * wing_area) ** 0.5


def mean_aerodynamic_chord(AR, wing_area):
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

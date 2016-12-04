import math


def pitch(vessel):
    vessel_direction = vessel.direction(vessel.surface_reference_frame)

    # Get the direction of the vessel in the horizon plane
    horizon_direction = (0, vessel_direction[1], vessel_direction[2])

    # Compute the pitch
    pitch = angle_between_vectors(vessel_direction, horizon_direction)
    if vessel_direction[0] < 0:
        pitch = -pitch

    return pitch


def dot_product(x, y):
    return x[0] * y[0] + x[1] * y[1] + x[2] * y[2]


def magnitude(x):
    return math.sqrt(x[0]**2 + x[1]**2 + x[2]**2)


def angle_between_vectors(x, y):
    # Compute the angle between vector x and y
    dp = dot_product(x, y)
    if dp == 0:
        return 0
    xm = magnitude(x)
    ym = magnitude(y)
    return math.acos(dp / (xm * ym)) * (180. / math.pi)


def compute_circ_burn(vessel):
    mu = vessel.orbit.body.gravitational_parameter
    r = vessel.orbit.apoapsis
    a1 = vessel.orbit.semi_major_axis
    a2 = r
    v1 = math.sqrt(mu * ((2. / r) - (1. / a1)))
    v2 = math.sqrt(mu * ((2. / r) - (1. / a2)))
    delta_v = v2 - v1

    F = vessel.available_thrust
    Isp = vessel.specific_impulse * vessel.orbit.body.surface_gravity
    m0 = vessel.mass
    m1 = m0 / math.exp(delta_v / Isp)
    flow_rate = F / Isp
    burn_time = (m0 - m1) / flow_rate

    return {
        "delta_v": delta_v,
        "burn_time": burn_time
    }

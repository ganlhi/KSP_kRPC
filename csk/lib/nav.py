"""Utility functions for navigation purposes"""

import math
from .vector import angle_between_vectors


def pitch(vessel):
  """Computes current vessel pitch over horizon"""
  vessel_direction = vessel.direction(vessel.surface_reference_frame)

  # Get the direction of the vessel in the horizon plane
  horizon_direction = (0, vessel_direction[1], vessel_direction[2])

  # Compute the pitch
  pitch_degrees = angle_between_vectors(vessel_direction, horizon_direction)
  if vessel_direction[0] < 0:
    pitch_degrees = -pitch_degrees

  return pitch_degrees


def compute_circ_burn(vessel):
  """Computes burn parameters to circularize current orbit

    First parameter is deltaV needed for the burn

    Second one is the time needed to perform the burn using
    currently active engines
  """

  # Use vis-viva equation to compute required delta v
  mu = vessel.orbit.body.gravitational_parameter
  r = vessel.orbit.apoapsis
  a1 = vessel.orbit.semi_major_axis
  a2 = r
  v1 = math.sqrt(mu * ((2. / r) - (1. / a1)))
  v2 = math.sqrt(mu * ((2. / r) - (1. / a2)))
  delta_v = v2 - v1

  # Use rocket equation to compute burn time
  F = vessel.available_thrust
  Isp = vessel.specific_impulse * vessel.orbit.body.surface_gravity
  m0 = vessel.mass
  m1 = m0 / math.exp(delta_v / Isp)
  flow_rate = F / Isp
  burn_time = (m0 - m1) / flow_rate

  return {"delta_v": delta_v,
          "burn_time": burn_time
          }


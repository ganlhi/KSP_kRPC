"""
  Functions to be used as mission steps
  for a launch from Kerbin surface
"""

import time
import math
from lib.pid import PID
from lib.nav import compute_circ_burn
from lib.parts import find_all_fairings, jettison_fairing


def pre_launch(mission):
  """Configure vessel before launch"""
  started_since = mission.ut() - mission.current_step["start_ut"]
  if started_since > 10:
    mission.next()
  elif mission.current_step["first_call"]:
    vessel = mission.conn.active_vessel
    ap = vessel.auto_pilot

    ap.engage()
    ap.target_pitch_and_heading(90, 90)
    vessel.control.throttle = 1
    vessel.control.sas = False
    vessel.control.rcs = mission.parameters.get('use_rcs', False)


def launch(mission):
  """Ignite first stage and release clamps"""
  vessel = mission.conn.active_vessel

  turn_start_alt = mission.parameters.get('turn_start_alt', 1000)
  turn_start_speed = mission.parameters.get('turn_start_speed', 100)

  speed = vessel.flight(vessel.orbit.body.reference_frame).speed
  altitude = vessel.flight().mean_altitude

  if mission.current_step["first_call"]:
    first = True
    while len(vessel.parts.launch_clamps) > 0:
      if not first:
        time.sleep(1)
      vessel.control.activate_next_stage()
      first = False
  else:
    if altitude > turn_start_alt and speed > turn_start_speed:
      mission.parameters["turn_start_alt"] = altitude
      mission.next()


def gravity_turn(mission):
  """Progressively pitch over, and limit APT to X seconds"""
  vessel = mission.conn.active_vessel

  apoapsis = vessel.orbit.apoapsis_altitude
  altitude = vessel.flight().mean_altitude
  apo_time = vessel.orbit.time_to_apoapsis
  per_time = vessel.orbit.time_to_periapsis
  target_altitude = mission.parameters.get('target_altitude', 100000)
  turn_end_alt = mission.parameters.get('turn_end_alt', target_altitude * 0.6)
  turn_start_alt = mission.parameters.get('turn_start_alt', 1000)
  min_pitch = mission.parameters.get('min_pitch', 10)
  target_apt = mission.parameters.get('target_apt', 40)
  max_autostage = mission.parameters.get('max_autostage', 0)

  if mission.current_step["first_call"]:
    mission.parameters["pid"] = PID(0.2, 0.01, 0.1, 0.1, 1)

  if apoapsis > target_altitude:
    del mission.parameters["pid"]
    vessel.control.throttle = 0
    mission.next('coast_to_space')
    return

  if altitude() > vessel.orbit.body.atmosphere_depth:
    mission.next('burn_to_apo')
    return

  if vessel.flight().static_pressure < 100:
    target_apt = 60.0
    mission.parameters["target_apt"] = target_apt

    if len(find_all_fairings(vessel)) > 0:
      drop_fairings(vessel)

  auto_stage(vessel, max_autostage)

  frac_den = turn_end_alt - turn_start_alt
  frac_num = altitude - turn_start_alt
  turn_angle = 90 * frac_num / frac_den
  target_pitch = max(min_pitch, 90 - turn_angle)
  vessel.auto_pilot.target_pitch_and_heading(target_pitch, 90)
  mission.parameters["target_pitch"] = target_pitch

  if per_time < apo_time:
    new_thr = 1
  else:
    new_thr = mission.parameters["pid"].seek(target_apt, apo_time, mission.ut())

  vessel.control.throttle = new_thr


def burn_to_apo(mission):
  """Adjust pitch to limit APT to X seconds"""
  vessel = mission.conn.active_vessel

  apoapsis = vessel.orbit.apoapsis_altitude
  half_period = vessel.orbit.period / 2
  apo_time = vessel.orbit.time_to_apoapsis
  target_altitude = mission.parameters.get('target_altitude', 100000)
  target_apt = mission.parameters.get('target_apt', 40)
  max_autostage = mission.parameters.get('max_autostage', 0)
  min_pitch = mission.parameters.get('min_pitch', -10)
  max_pitch = mission.parameters.get('max_pitch', 30)

  if mission.current_step["first_call"]:
    mission.parameters["pid"] = PID(0.2, 0.01, 0.1, min_pitch, max_pitch)
    vessel.control.throttle = 1

  if apoapsis > target_altitude:
    del mission.parameters["pid"]
    vessel.control.throttle = 0
    mission.next('coast_to_space')
    return

  auto_stage(vessel, max_autostage)

  """Adjust pitch around 0 to control APT:

    si APT devient grand (mais < 1/2 periode) : diminuer pitch
    si APT tend vers 0 : augmenter pitch
    si APT devient grand (> 1/2 periode) : augmenter pitch

    si APT > .5 periode
      pitch = max
    sinon
      pitch = pid(-APT)
  """
  if half_period < apo_time:
    target_pitch = max_pitch
  else:
    apt_error = math.fabs(apo_time - target_apt)
    target_pitch = mission.parameters["pid"].seek(0, apt_error, mission.ut())

  vessel.auto_pilot.target_pitch_and_heading(target_pitch, 90)
  mission.parameters["target_pitch"] = target_pitch


def coast_to_space(mission):
  """Waiting for vessel to go above atmosphere"""
  vessel = mission.conn.active_vessel
  altitude = vessel.flight().mean_altitude
  ap = vessel.auto_pilot

  if mission.current_step["first_call"]:
    vessel.control.throttle = 0
    ap.reference_frame = vessel.orbital_reference_frame
    ap.target_direction = (0, 1, 0)

  if altitude > vessel.orbit.body.atmosphere_depth:
    mission.next()


def correct_apoapsis(mission):
  """Apply a correction to apoapsis altitude if needed"""
  vessel = mission.conn.active_vessel
  apoapsis = vessel.orbit.apoapsis_altitude
  target_altitude = mission.parameters.get('target_altitude', 100000)

  if mission.current_step["first_call"]:
    if apoapsis < target_altitude:
      vessel.control.throttle = 0.05

  if apoapsis > target_altitude:
    vessel.control.throttle = 0
    mission.next()


def prepare_circ_burn(mission):
  """Compute a circularization burn, then coast to it"""
  vessel = mission.conn.active_vessel
  apo_time = vessel.orbit.time_to_apoapsis
  ap = vessel.auto_pilot

  if mission.current_step["first_call"]:
    circ_burn = compute_circ_burn(vessel)
    circ_burn["burn_start_time"] = apo_time - (circ_burn["burn_time"] / 2.)
    circ_burn["node"] = vessel.control.add_node(mission.ut() + apo_time,
                                                prograde=circ_burn["delta_v"])

    mission.parameters["circ_burn"] = circ_burn
    ap.reference_frame = circ_burn["node"].reference_frame
    ap.target_direction = (0, 1, 0)

  elif ap.error < 1 and mission.ut() - mission.current_step["start_ut"] > 1:
    circ_burn = mission.parameters["circ_burn"]
    burn_ut = mission.ut() + circ_burn["burn_start_time"]
    lead_time = 15
    if burn_ut > mission.ut() + lead_time * 2:
      mission.conn.space_center.warp_to(burn_ut - lead_time)
    mission.next()


def coast_to_circ_burn(mission):
  """Wait time to burn"""
  circ_burn = mission.parameters["circ_burn"]

  if circ_burn["burn_start_time"] <= 0:
    mission.next()


def execute_circ_burn(mission):
  """Execute maneuver node to circularize"""
  vessel = mission.conn.active_vessel
  circ_burn = mission.parameters["circ_burn"]
  remaining_delta_v = circ_burn["node"].remaining_delta_v

  if mission.current_step["first_call"]:
    circ_burn["remaining_delta_v"] = remaining_delta_v

  if circ_burn["burn_time"] > 10:
    vessel.control.throttle = 1
  else:
    vessel.control.throttle = 0.05

  max_autostage = mission.parameters.get('max_autostage', 0)
  auto_stage(vessel, max_autostage)

  if (remaining_delta_v < 0 or
      remaining_delta_v > circ_burn["remaining_delta_v"]):
    vessel.control.throttle = 0
    circ_burn["node"].remove()
    del mission.parameters["circ_burn"]
    mission.next()

  circ_burn["remaining_delta_v"] = remaining_delta_v


def delay_completion(mission):
  """Wait some time to complete"""
  if mission.ut() - mission.current_step["start_ut"] > 5:
    vessel = mission.conn.active_vessel
    vessel.auto_pilot.disengage()
    mission.next()


###################################

all_steps = [
    {"name": "pre_launch", "function": pre_launch},
    {"name": "launch", "function": launch},
    {"name": "gravity_turn", "function": gravity_turn},
    {"name": "coast_to_space", "function": coast_to_space},
    {"name": "correct_apoapsis", "function": correct_apoapsis},
    {"name": "prepare_circ_burn", "function": prepare_circ_burn},
    {"name": "coast_to_circ_burn", "function": coast_to_circ_burn},
    {"name": "execute_circ_burn", "function": execute_circ_burn},
    {"name": "delay_completion", "function": delay_completion},
]

###################################

# Utility functions


def drop_fairings(vessel):
  """Drop all fairings not tagged as 'noauto'"""
  fairings = filter(lambda f: getattr(f, 'tag', None) != "noauto",
                    find_all_fairings(vessel))
  for f in fairings:
    jettison_fairing(f)


def auto_stage(vessel, max_autostage):
  """Stage if no thrust available"""
  if not vessel.available_thrust:
    active_stage = 99
    active_engines = [e for e in vessel.parts.engines if e.active]
    for engine in active_engines:
      active_stage = min(engine.part.stage, active_stage)

    if active_stage > max_autostage:
      old_thr = vessel.control.throttle
      vessel.control.throttle = 0

      while not vessel.available_thrust:
        time.sleep(0.5)
        vessel.control.activate_next_stage()

      vessel.control.throttle = old_thr

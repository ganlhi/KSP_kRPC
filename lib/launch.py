"""
  Functions to be used as mission steps
  for a launch from Kerbin surface
"""

import time
from lib.pid import PID
from lib.nav import pitch, compute_circ_burn
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
  target_altitude = mission.parameters.get('target_altitude', 100000)
  turn_end_alt = mission.parameters.get('turn_end_alt', 60000)
  turn_start_alt = mission.parameters.get('turn_start_alt', 1000)
  min_pitch = mission.parameters.get('min_pitch', 10)
  target_apt = mission.parameters.get('target_apt', 40)
  max_autostage = mission.parameters.get('max_autostage', 0)

  if mission.current_step["first_call"]:
    mission.parameters["pid"] = PID(0.2, 0.01, 0.1, 0.1, 1)

  if apoapsis > target_altitude:
    del mission.parameters["pid"]
    vessel.control.throttle = 0
    mission.next()
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

  new_thr = mission.parameters["pid"].seek(target_apt, apo_time, mission.ut())
  vessel.control.throttle = new_thr



def drop_fairings(vessel):
  fairings = filter(lambda f: f.tag != "noauto", find_all_fairings(vessel))
  for f in fairings:
    jettison_fairing(f)


def auto_stage(vessel, max_autostage):
  if not vessel.available_thrust:
    active_stage = 99
    active_engines = filter(lambda e: e.active, vessel.parts.engines)
    for engine in active_engines:
      active_stage = min(engine.part.stage, active_stage)

    if active_stage > max_autostage:
      old_thr = vessel.control.throttle
      vessel.control.throttle = 0

      while not vessel.available_thrust:
        time.sleep(0.5)
        vessel.control.activate_next_stage()

      vessel.control.throttle = old_thr



###################################

all_steps = [
  {"name": "pre_launch", "function": pre_launch},
  {"name": "launch", "function": launch},
]
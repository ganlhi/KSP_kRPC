"""
  Functions to be used as mission steps
  for a launch from Kerbin surface
"""

import time
from pid import PID
from nav import pitch, compute_circ_burn
from parts import find_all_fairings, jettison_fairing


def pre_launch(mission):
  """Configure vessel before launch"""
  if  mission.met > 10:
    mission.next()
  elif mission.current_step_first_call:
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

  if mission.current_step_first_call:
    while len(vessel.parts.launch_clamps) > 0:
      vessel.control.activate_next_stage()
      time.sleep(1)

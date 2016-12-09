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

  if mission.current_step["first_call"]:
    first = True
    while len(vessel.parts.launch_clamps) > 0:
      if not first:
        time.sleep(1)
      vessel.control.activate_next_stage()
      first = False

    mission.next()




all_steps = [
  {"name": "pre_launch", "function": pre_launch},
  {"name": "launch", "function": launch},
]
"""Utility functions to manipulate vessel parts"""

import time


def find_all_fairings(vessel):
  """Finds all vessel fairings, both stock and procedural ones"""
  stock_fairings = vessel.parts.fairings
  proc_fairings = vessel.parts.with_module("ProceduralFairingDecoupler")
  return stock_fairings + proc_fairings


def jettison_fairing(part):
  """Jetissons a fairing, either stock or procedural"""
  if hasattr(part, 'fairing'):
    part.fairing.jettison()
  elif callable(getattr(part, 'jettison', None)):
    part.jettison()
  else:
    for module in part.modules:
      if module.name == "ProceduralFairingDecoupler":
        module.trigger_event("Jettison")


def auto_stage(vessel, max_autostage=0, stage_wait=0.5):
  if not vessel.available_thrust:
    active_stage = 99
    active_engines = filter(lambda e: e.active, vessel.parts.engines)
    for engine in active_engines:
      active_stage = min(engine.part.stage, active_stage)

    if active_stage > max_autostage:
      old_thr = vessel.control.throttle
      vessel.control.throttle = 0

      while not vessel.available_thrust:
        time.sleep(stage_wait)
        vessel.control.activate_next_stage()

      vessel.control.throttle = old_thr

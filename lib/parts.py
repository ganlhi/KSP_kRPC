"""Utility functions to manipulate vessel parts"""

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

import time
from statistics import mean
from math import fabs
import krpc
from lib.scenario.launch import LaunchScenario
from lib.scenario.exec_node import ExecNodeScenario
from lib.nav import compute_circ_burn


def is_icarus_engine_active(vessel):
  icarus_eng = 'SSTU-SC-ENG-SuperDraco-L'
  engines = vessel.parts.engines
  eng = [e for e in engines if e.active and e.part.name == icarus_eng]
  return len(eng) == 1


def is_landed(vessel):
  return (vessel.situation.name == 'landed' or
          vessel.situation.name == 'splashed')


def perform_launch(conn, ksc, vessel):
  launch_params = {'target_altitude': 120000,
                   'target_apt': 50.0,
                   'turn_end_alt': 95000}

  LaunchScenario(context={'conn': conn}, parameters=launch_params).run()

  apo_time = vessel.orbit.time_to_apoapsis
  circ_burn = compute_circ_burn(vessel)
  node = vessel.control.add_node(ksc.ut + apo_time,
                                 prograde=circ_burn["delta_v"])

  ExecNodeScenario(context={'conn': conn},
                   parameters={'node': node}).run()


def wait_above_ksc(conn, ksc, vessel):
  ant = conn.remote_tech.comms(vessel).antennas[0]
  mod = [m for m in ant.part.modules if m.name == 'ModuleRTAntenna'][0]
  if mod.has_event('Activate'):
    mod.trigger_event('Activate')

  lat = conn.add_stream(getattr, vessel.flight(), 'latitude')
  lon = conn.add_stream(getattr, vessel.flight(), 'longitude')

  while True:
    lat_err = fabs(0 - lat())
    lon_err = fabs(-75 - lon())
    sun_exp = mean([p.sun_exposure for p in vessel.parts.solar_panels])

    if lon_err > 20 or sun_exp == 0:
      ksc.rails_warp_factor = 7

    elif lon_err > 2 and lon_err < 20:
      ksc.rails_warp_factor = 2

    elif lat_err < 1 and lon_err < 1 and sun_exp > 0:
      ksc.rails_warp_factor = 0
      break

    time.sleep(0.01)


def take_photo(conn, ksc, vessel):
  ap = vessel.auto_pilot

  vessel.control.rcs = True
  ap.engage()
  ap.reference_frame = vessel.orbital_reference_frame
  ap.target_direction = (1, 0, 0)
  ap.wait()

  cam = vessel.parts.with_name('hc.kazzelblad')[0]
  mod = [m for m in cam.modules if m.name == 'MuMechModuleHullCameraZoom'][0]
  if mod.has_event('Activate Camera'):
    mod.trigger_event('Activate Camera')


if __name__ == '__main__':
  conn = krpc.connect()
  ksc = conn.space_center
  vessel = ksc.active_vessel

  if vessel.situation.name == 'pre_launch':
    perform_launch(conn, ksc, vessel)

  elif vessel.situation.name == 'orbiting':
    wait_above_ksc(conn, ksc, vessel)
    take_photo(conn, ksc, vessel)


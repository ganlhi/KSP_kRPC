import time
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

  while not is_icarus_engine_active(vessel):
    vessel.control.activate_next_stage()

  apo_time = vessel.orbit.time_to_apoapsis
  circ_burn = compute_circ_burn(vessel)
  node = vessel.control.add_node(ksc.ut + apo_time,
                                 prograde=circ_burn["delta_v"])

  ExecNodeScenario(context={'conn': conn},
                   parameters={'node': node}).run()


def perform_return(conn, ksc, vessel):
  if len(vessel.control.nodes) == 0:
    print('No reentry maneuver')
    return

  node = vessel.control.nodes[0]
  ExecNodeScenario(context={'conn': conn},
                   parameters={'node': node}).run()

  altitude = conn.add_stream(getattr, vessel.flight(),
                             'mean_altitude')

  atm_alt = vessel.orbit.body.atmosphere_depth

  while altitude() > atm_alt:
    ksc.rails_warp_factor = 7
    time.sleep(0.01)

  ksc.rails_warp_factor = 0
  vessel.control.activate_next_stage()
  perform_reentry(conn, ksc, vessel)


def perform_reentry(conn, ksc, vessel):
  flight_ref = vessel.flight(vessel.orbit.body.reference_frame)
  altitude = conn.add_stream(getattr, vessel.flight(),
                             'mean_altitude')
  speed = conn.add_stream(getattr, flight_ref, 'speed')

  ap = vessel.auto_pilot

  ap.engage()
  ap.reference_frame = vessel.surface_velocity_reference_frame
  ap.target_direction = (0, -1, 0)

  while not is_landed(vessel):
    if altitude() < 10000 and speed() < 300:
      for ch in vessel.parts.parachutes:
        ch.deploy()
      ap.disengage()
      break

    time.sleep(0.1)


if __name__ == '__main__':
  conn = krpc.connect()
  ksc = conn.space_center
  vessel = ksc.active_vessel

  if vessel.situation.name == 'pre_launch':
    perform_launch(conn, ksc, vessel)

  elif vessel.situation.name == 'orbiting':
    perform_return(conn, ksc, vessel)

  elif vessel.situation.name == 'flying':
    perform_reentry(conn, ksc, vessel)

import time
from lib.pid import PID
from lib.nav import pitch, compute_circ_burn


def launch(conn):

  vessel = conn.space_center.active_vessel
  ap = vessel.auto_pilot

  target_altitude = 80000
  target_apt = 40.0
  final_pitch = 20
  turn_start_alt = 1000
  turn_start_speed = 100
  turn_step = 0

  pid = PID(0.2, 0.01, 0.1, 0.1, 1)

  # Set up streams for telemetry
  ut = conn.add_stream(getattr, conn.space_center, 'ut')
  speed = conn.add_stream(getattr, vessel.flight(vessel.orbit.body.reference_frame), 'speed')
  altitude = conn.add_stream(getattr, vessel.flight(), 'mean_altitude')
  apo_time = conn.add_stream(getattr, vessel.orbit, 'time_to_apoapsis')
  apoapsis = conn.add_stream(getattr, vessel.orbit, 'apoapsis_altitude')
  # periapsis = conn.add_stream(getattr, vessel.orbit, 'periapsis_altitude')

  # Pre-launch
  ap.engage()
  ap.target_pitch_and_heading(90, 90)
  vessel.control.throttle = 1
  vessel.control.sas = False
  vessel.control.rcs = False

  # Launch
  while len(vessel.parts.launch_clamps) > 0:
    time.sleep(1)
    vessel.control.activate_next_stage()

  last_log = ut()
  # Ascent loop
  while True:

    # End this loop to coast to apoapsis
    if apoapsis() > target_altitude:
      break

    # Begin grav turn
    if turn_step == 0 and altitude() > turn_start_alt and speed() > turn_start_speed:
      print("Begin grav turn")
      ap.target_pitch_and_heading(80, 90)
      turn_step = 1

    # Lock steering to surf prograde
    if turn_step == 1 and pitch(vessel) - 80 < 5:
      print("Lock steering to surf prograde")
      ap.reference_frame = vessel.surface_velocity_reference_frame
      ap.target_direction = (0, 1, 0)
      turn_step = 2

    # Lock steering to prograde
    if turn_step == 2 and altitude() > 40000:
      print("Lock steering to prograde")
      ap.reference_frame = vessel.orbital_reference_frame
      ap.target_direction = (0, 1, 0)
      turn_step = 3

    # Final pitch
    if turn_step == 3 and pitch(vessel) < (final_pitch + 2):
      print("Final pitch")
      # ap.target_pitch_and_heading(final_pitch, 90)
      turn_step = 4

    new_thr = pid.seek(target_apt, apo_time(), ut())
    vessel.control.throttle = new_thr

    if ut() - last_log > 5:
      print("Speed: %d" % speed())
      print("Alt: %d" % altitude())
      print("Thr: %f" % new_thr)
      last_log = ut()

  # MECO
  vessel.control.throttle = 0
  ap.reference_frame = vessel.orbital_reference_frame
  ap.target_direction = (0, 1, 0)
  while altitude() < 70000:
    pass

  # Compute circularization burn
  circ_burn = compute_circ_burn(vessel)
  node = vessel.control.add_node(ut() + apo_time(), prograde=circ_burn["delta_v"])

  print('Orientating ship for circularization burn')
  ap.reference_frame = node.reference_frame
  ap.target_direction = (0, 1, 0)
  ap.wait()

  # Wait until burn
  print('Waiting until circularization burn')
  burn_ut = ut() + apo_time() - (circ_burn["burn_time"] / 2.)
  lead_time = 15
  if burn_ut > ut() + lead_time:
    conn.space_center.warp_to(burn_ut - lead_time)

  # Execute burn
  print('Ready to execute burn')
  while apo_time() - (circ_burn["burn_time"] / 2.) > 0:
    pass
  print('Executing burn')
  vessel.control.throttle = 1

  remaining_delta_v = conn.add_stream(getattr, node, 'remaining_delta_v')
  while remaining_delta_v() > 10:
    pass

  print('Fine tuning')
  vessel.control.throttle = 0.05

  last_remaining = remaining_delta_v()
  while remaining_delta_v() > 0 and remaining_delta_v() > last_remaining:
    last_remaining = remaining_delta_v()
    time.sleep(0.01)

  vessel.control.throttle = 0
  node.remove()

  time.sleep(5)
  ap.disengage()

  print('Launch complete')

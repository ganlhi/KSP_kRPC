import time
from lib.pid import PID
from lib.nav import pitch, compute_circ_burn
from lib.parts import find_all_fairings, jettison_fairing


def launch(conn, max_autostage=0, target_altitude=100000, use_rcs=False):

  ui = init_ui(conn)

  vessel = conn.space_center.active_vessel
  ap = vessel.auto_pilot

  all_fairings = find_all_fairings(vessel)
  has_fairings = len(all_fairings) > 0

  target_apt = 40.0
  turn_end_alt = 60000
  turn_start_alt = 1000
  turn_start_speed = 100
  turn_step = 0
  target_pitch = 90
  min_pitch = 10

  pid = PID(0.2, 0.01, 0.1, 0.1, 1)

  # Set up streams for telemetry
  ut = conn.add_stream(getattr, conn.space_center, 'ut')
  speed = conn.add_stream(getattr, vessel.flight(vessel.orbit.body.reference_frame), 'speed')
  altitude = conn.add_stream(getattr, vessel.flight(), 'mean_altitude')
  apo_time = conn.add_stream(getattr, vessel.orbit, 'time_to_apoapsis')
  apoapsis = conn.add_stream(getattr, vessel.orbit, 'apoapsis_altitude')
  static_pressure = conn.add_stream(getattr, vessel.flight(), 'static_pressure')

  # Pre-launch
  ap.engage()
  ap.target_pitch_and_heading(target_pitch, 90)
  vessel.control.throttle = 1
  vessel.control.sas = False
  vessel.control.rcs = use_rcs

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
      turn_start_alt = altitude()
      turn_step = 1

    # Compute new pitch
    if turn_step == 1:
      frac_den = turn_end_alt - turn_start_alt
      frac_num = altitude() - turn_start_alt
      turn_angle = 90 * frac_num / frac_den
      target_pitch = max(min_pitch, 90 - turn_angle)
      vessel.auto_pilot.target_pitch_and_heading(target_pitch, 90)

      # Staging
      auto_stage(vessel, max_autostage)

    # Throttle control
    if altitude() > 40000:
      target_apt = 60.0

    new_thr = pid.seek(target_apt, apo_time(), ut())
    vessel.control.throttle = new_thr

    # Fairings
    if has_fairings:
      if static_pressure() < 100:
        drop_fairings(vessel)

    # Logging
    if ut() - last_log > 1:
      ui['texts']['speed'].content = "Speed: %d m/s" % speed()
      ui['texts']['throttle'].content = "Throttle: %.1f %%" % (new_thr * 100.0)
      ui['texts']['altitude'].content = "Altitude: %d m" % altitude()
      ui['texts']['target_pitch'].content = "Tgt. pitch: %d °" % target_pitch
      ui['texts']['current_pitch'].content = "Cur. pitch: %d °" % pitch(vessel)
      ui['texts']['target_apt'].content = "Tgt. APT: %.1f s" % target_apt
      ui['texts']['current_apt'].content = "Cur. APT: %.1f s" % apo_time()
      last_log = ut()

    time.sleep(0.01)

  # MECO
  vessel.control.throttle = 0
  ap.reference_frame = vessel.orbital_reference_frame
  ap.target_direction = (0, 1, 0)
  while altitude() < 70000:
    pass

  # Correct apoapsis
  if apoapsis() < target_altitude:
    vessel.control.throttle = 0.05
    while apoapsis() <= target_altitude:
      time.sleep(0.01)
    vessel.control.throttle = 0

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
  if burn_ut > ut() + lead_time * 2:
    conn.space_center.warp_to(burn_ut - lead_time)

  # Execute burn
  print('Ready to execute burn')
  while apo_time() - (circ_burn["burn_time"] / 2.) > 0:
    time.sleep(0.01)

  print('Executing burn')
  remaining_delta_v = conn.add_stream(getattr, node, 'remaining_delta_v')

  if circ_burn["burn_time"] > 10:
    vessel.control.throttle = 1
  else:
    vessel.control.throttle = 0.05

  last_remaining = remaining_delta_v()
  while remaining_delta_v() > 0 and remaining_delta_v() <= last_remaining:
    if remaining_delta_v() < 10:
      vessel.control.throttle = 0.05
    auto_stage(vessel, max_autostage)
    last_remaining = remaining_delta_v()
    time.sleep(0.01)

  vessel.control.throttle = 0
  node.remove()

  time.sleep(5)
  ap.disengage()

  print('Launch complete')


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


def drop_fairings(vessel):
  fairings = filter(lambda f: f.tag != "noauto", find_all_fairings(vessel))
  for f in fairings:
    jettison_fairing(f)


def init_ui(conn):
  canvas = conn.ui.stock_canvas

  # Get the size of the game window in pixels
  screen_size = canvas.rect_transform.size

  # Add a panel to contain the UI elements
  panel = canvas.add_panel()

  # Position the panel on the left of the screen
  rect = panel.rect_transform
  rect.size = (300, 160)
  rect.position = (110 - (screen_size[0] / 2), 0)

  texts = {}

  texts['speed'] = panel.add_text("Speed: 0 m/s")
  texts['speed'].rect_transform.position = (0, 50)
  texts['speed'].color = (1, 1, 1)
  texts['speed'].size = 16

  texts['throttle'] = panel.add_text("Throttle: 0 %")
  texts['throttle'].rect_transform.position = (0, 30)
  texts['throttle'].color = (1, 1, 1)
  texts['throttle'].size = 16

  texts['altitude'] = panel.add_text("Altitude: 0 m")
  texts['altitude'].rect_transform.position = (0, 10)
  texts['altitude'].color = (1, 1, 1)
  texts['altitude'].size = 16

  texts['target_pitch'] = panel.add_text("Tgt. pitch: 0 °")
  texts['target_pitch'].rect_transform.position = (0, -10)
  texts['target_pitch'].color = (1, 1, 1)
  texts['target_pitch'].size = 16

  texts['current_pitch'] = panel.add_text("Cur. pitch: 0 °")
  texts['current_pitch'].rect_transform.position = (0, -30)
  texts['current_pitch'].color = (1, 1, 1)
  texts['current_pitch'].size = 16

  texts['target_apt'] = panel.add_text("Tgt. APT: 0 s")
  texts['target_apt'].rect_transform.position = (0, -50)
  texts['target_apt'].color = (1, 1, 1)
  texts['target_apt'].size = 16

  texts['current_apt'] = panel.add_text("Cur. APT: 0 s")
  texts['current_apt'].rect_transform.position = (0, -70)
  texts['current_apt'].color = (1, 1, 1)
  texts['current_apt'].size = 16

  return {'panel': panel, 'texts': texts}

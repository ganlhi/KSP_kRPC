"""Generic mission to launch to orbit around orbit"""

import time
import krpc
from csk.lib.mission import Mission
from csk.lib.nav import pitch
from csk.lib.steps.launch import all_steps


def init_ui(conn):
  canvas = conn.ui.stock_canvas

  # Get the size of the game window in pixels
  screen_size = canvas.rect_transform.size

  # Add a panel to contain the UI elements
  panel = canvas.add_panel()

  # Position the panel on the left of the screen
  rect = panel.rect_transform
  rect.size = (300, 180)
  rect.position = (160 - screen_size[0] / 2, screen_size[1] / 2 - 160)

  texts = {}

  texts['step'] = panel.add_text("Step: N/A")
  texts['step'].rect_transform.position = (-50, 65)
  texts['step'].color = (.2, .5, 1)
  texts['step'].size = 14

  texts['speed'] = panel.add_text("Speed: 0 m/s")
  texts['speed'].rect_transform.position = (-50, 40)
  texts['speed'].color = (1, 1, 1)
  texts['speed'].size = 14

  texts['throttle'] = panel.add_text("Throttle: 0 %")
  texts['throttle'].rect_transform.position = (-50, 20)
  texts['throttle'].color = (1, 1, 1)
  texts['throttle'].size = 14

  texts['altitude'] = panel.add_text("Altitude: 0 m")
  texts['altitude'].rect_transform.position = (-50, 00)
  texts['altitude'].color = (1, 1, 1)
  texts['altitude'].size = 14

  texts['target_pitch'] = panel.add_text("Tgt. pitch: 0 °")
  texts['target_pitch'].rect_transform.position = (-50, -20)
  texts['target_pitch'].color = (1, 1, 1)
  texts['target_pitch'].size = 14

  texts['current_pitch'] = panel.add_text("Cur. pitch: 0 °")
  texts['current_pitch'].rect_transform.position = (-50, -40)
  texts['current_pitch'].color = (1, 1, 1)
  texts['current_pitch'].size = 14

  texts['target_apt'] = panel.add_text("Tgt. APT: 0 s")
  texts['target_apt'].rect_transform.position = (-50, -60)
  texts['target_apt'].color = (1, 1, 1)
  texts['target_apt'].size = 14

  texts['current_apt'] = panel.add_text("Cur. APT: 0 s")
  texts['current_apt'].rect_transform.position = (-50, -80)
  texts['current_apt'].color = (1, 1, 1)
  texts['current_apt'].size = 14

  return {'panel': panel, 'texts': texts}


if __name__ == "__main__":
  conn = krpc.connect()
  vessel = conn.space_center.active_vessel

  params = {'target_altitude': 140000,
            'turn_end_alt': 110000,
            'target_apt': 60}

  mission = Mission(conn, all_steps, params)
  ui = init_ui(conn)

  orbit_frame = vessel.orbit.body.reference_frame

  ut = conn.add_stream(getattr, conn.space_center, 'ut')
  speed = conn.add_stream(getattr, vessel.flight(orbit_frame), 'speed')
  altitude = conn.add_stream(getattr, vessel.flight(), 'mean_altitude')
  apo_time = conn.add_stream(getattr, vessel.orbit, 'time_to_apoapsis')
  thr = conn.add_stream(getattr, vessel.control, 'throttle')

  mission.start()
  last_log = ut()

  while mission.running:
    mission.update()

    if ut() - last_log > 1:
      target_apt = mission.parameters.get('target_apt')
      target_pitch = mission.parameters.get('target_pitch', None)

      step_name = mission.current_step['name'].replace('_', ' ').title()

      if target_pitch is None:
        ui['texts']['target_pitch'].content = "Tgt. pitch: N/A"
      else:
        ui['texts']['target_pitch'].content = "Tgt. pitch: %d °" % target_pitch
      ui['texts']['speed'].content = "Speed: %d m/s" % speed()
      ui['texts']['throttle'].content = "Throttle: %.1f %%" % (thr() * 100.0)
      ui['texts']['altitude'].content = "Altitude: %d m" % altitude()
      ui['texts']['current_pitch'].content = "Cur. pitch: %d °" % pitch(vessel)
      ui['texts']['target_apt'].content = "Tgt. APT: %.1f s" % target_apt
      ui['texts']['current_apt'].content = "Cur. APT: %.1f s" % apo_time()
      ui['texts']['step'].content = "Step: %s" % step_name
      last_log = ut()

    time.sleep(0.1)

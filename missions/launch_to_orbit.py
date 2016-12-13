"""Generic mission to launch to orbit around orbit"""

import time
import krpc
from lib.mission import Mission
from lib.nav import pitch
from lib.steps.launch import all_steps


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


if __name__ == "__main__":
  conn = krpc.connect()
  vessel = conn.space_center.active_vessel

  params = {'target_altitude': 110000,
            'turn_end_alt': 90000,
            'target_apt': 50}

  mission = Mission(conn, all_steps, params).run()
  ui = init_ui(conn)

  orbit_frame = vessel.orbit.body.reference_frame

  ut = conn.add_stream(getattr, conn.space_center, 'ut')
  speed = conn.add_stream(getattr, vessel.flight(orbit_frame), 'speed')
  altitude = conn.add_stream(getattr, vessel.flight(), 'mean_altitude')
  apo_time = conn.add_stream(getattr, vessel.orbit, 'time_to_apoapsis')
  thr = conn.add_stream(getattr, vessel.control, 'throttle')

  last_log = ut()

  while next(mission):
    if ut() - last_log > 1:
      target_apt = mission.parameters.get('target_apt')
      target_pitch = mission.parameters.get('target_pitch', None)

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
      last_log = ut()

    time.sleep(0.01)

from math import sqrt
from .scenario import Scenario
from ..parts import auto_stage, find_all_fairings, jettison_fairing
from ..pid import PID
from ..nav import pitch


class LaunchScenario(Scenario):

  parameters = {'use_rcs': False,
                'max_autostage': 0,
                'target_altitude': 120000,
                'target_apt': 40.0,
                'turn_end_alt': 80000,
                'turn_start_alt': 1000,
                'turn_start_speed': 100,
                'turn_style': 'square_root',
                'min_pitch': 0,
                'pitch_offset': 30,
                'stage_wait': 1}

  events = {
    'high_altitude': {
      'condition': lambda s: s.stat_press() < 100,
      'action': lambda s: s.on_high_alt()
    }
  }

  def pre_run(self):
    self.conn = self.context['conn']
    self.ksc = self.conn.space_center
    self.vessel = self.ksc.active_vessel
    self.control = self.vessel.control
    self.ap = self.vessel.auto_pilot
    self.start_ut = self.ksc.ut
    self.target_apt = self.parameters['target_apt']

    flight_ref = self.vessel.flight(self.vessel.orbit.body.reference_frame)

    self.ut = self.conn.add_stream(getattr, self.ksc, 'ut')
    self.speed = self.conn.add_stream(getattr,
                                      flight_ref, 'speed')
    self.altitude = self.conn.add_stream(getattr, self.vessel.flight(),
                                         'mean_altitude')
    self.apo_time = self.conn.add_stream(getattr, self.vessel.orbit,
                                         'time_to_apoapsis')
    self.per_time = self.conn.add_stream(getattr, self.vessel.orbit,
                                         'time_to_periapsis')
    self.apoapsis = self.conn.add_stream(getattr, self.vessel.orbit,
                                         'apoapsis_altitude')
    self.stat_press = self.conn.add_stream(getattr,
                                           self.vessel.flight(),
                                           'static_pressure')

    self.thr_pid = PID(0.2, 0.01, 0.1, 0.1, 1)
    self.pitch_pid = PID(0.5, 0.05, 0.2, 0, self.parameters['pitch_offset'])

    self.init_ui()

  def step(self):
    self.update_ui()

    if self.apoapsis() >= self.parameters['target_altitude']:
      self.meco()
      self.context['step_name'] = 'Coasting'
      # stop this scenario if above atmo and target apo achieved
      if self.altitude() > self.vessel.orbit.body.atmosphere_depth:
        return False

    if self.vessel.situation.name == 'pre_launch':
      self.context['step_name'] = 'Pre-launch'
      return self.handle_prelaunch()

    auto_stage(self.vessel,
               max_autostage=self.parameters['max_autostage'],
               stage_wait=self.parameters['stage_wait'])

    self.context['step_name'] = 'Launch'
    if self.speed() > self.parameters['turn_start_speed']:
      self.context['step_name'] = 'Gravity turn'
      self.grav_turn()

  def handle_prelaunch(self):
    if self.ut() - self.start_ut < 1:
      self.ap.engage()
      self.ap.target_pitch_and_heading(90, 90)
      self.control.throttle = 1
      self.control.sas = False
      self.control.rcs = self.parameters['use_rcs']

    else:
      while len(self.vessel.parts.launch_clamps) > 0:
        self.control.activate_next_stage()

  def grav_turn(self):
    if 'turn_start_alt' not in self.context:
      self.context['turn_start_alt'] = self.altitude()

    if 'turn_start_ut' not in self.context:
      self.context['turn_start_ut'] = self.ut()

    frac_den = self.parameters['turn_end_alt'] - self.context['turn_start_alt']
    frac_num = self.altitude() - self.context['turn_start_alt']

    if self.parameters['turn_style'] == 'linear':
      turn_angle = 90 * frac_num / frac_den
    else:
      turn_angle = 90 * sqrt(frac_num / frac_den)

    target_pitch = max(self.parameters['min_pitch'], 90 - turn_angle)

    if self.per_time() < self.apo_time():
      new_thr = 1
      set_pitch = target_pitch + self.parameters['pitch_offset']
    else:
      apt = self.apo_time()
      new_thr = self.thr_pid.seek(self.target_apt, apt, self.ut())
      if self.context.get('adjust_pitch', False):
        pitch_adj = self.pitch_pid.seek(self.target_apt, apt, self.ut())
        set_pitch = target_pitch + pitch_adj
      else:
        self.context['adjust_pitch'] = (apt < (self.target_apt * 0.8) and
                                        apt < self.context.get('last_apt', 0) and
                                        self.stat_press() < 100)
        set_pitch = target_pitch

    if self.altitude() > self.vessel.orbit.body.atmosphere_depth:
      apo_err = self.parameters['target_altitude'] - self.apoapsis()
      if apo_err < 10:
        new_thr = .1

    if self.ut() - self.context['turn_start_ut'] < 1:
      new_thr = 1

    self.control.throttle = new_thr
    self.ap.target_pitch_and_heading(set_pitch, 90)

    self.context['set_pitch'] = set_pitch

    ut = self.ut()
    last_ut = self.context.get('last_apt_ut', 0)
    if ut - last_ut > 1:
      if last_ut > 0:
        self.context['last_apt'] = self.apo_time()
      self.context['last_apt_ut'] = ut

  def post_run(self):
    self.context['ui']['panel'].remove()

  def on_high_alt(self):
    if len(find_all_fairings(self.vessel)) > 0:
      fairings = filter(lambda f: getattr(f, 'tag', None) != "noauto",
                        find_all_fairings(self.vessel))
      for f in fairings:
        jettison_fairing(f)

  def meco(self):
    self.control.throttle = 0
    self.ap.reference_frame = self.vessel.orbital_reference_frame
    self.ap.target_direction = (0, 1, 0)

  def init_ui(self):
    canvas = self.conn.ui.stock_canvas

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

    self.context['ui'] = {'panel': panel, 'texts': texts}

  def update_ui(self):
    target_apt = self.target_apt
    target_pitch = self.context.get('set_pitch', None)

    step_name = self.context.get('step_name')

    texts = self.context['ui']['texts']

    if target_pitch is None:
      texts['target_pitch'].content = "Tgt. pitch: N/A"
    else:
      texts['target_pitch'].content = "Tgt. pitch: %d °" % target_pitch
    texts['speed'].content = "Speed: %d m/s" % self.speed()
    texts['throttle'].content = "Throttle: %.1f %%" % (self.control.throttle * 100.0)
    texts['altitude'].content = "Altitude: %d m" % self.altitude()
    texts['current_pitch'].content = "Cur. pitch: %d °" % pitch(self.vessel)
    texts['target_apt'].content = "Tgt. APT: %.1f s" % target_apt
    texts['current_apt'].content = "Cur. APT: %.1f s" % self.apo_time()
    texts['step'].content = "Step: %s" % step_name

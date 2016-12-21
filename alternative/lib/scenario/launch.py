from .scenario import Scenario
from ..parts import auto_stage, find_all_fairings, jettison_fairing
from ..pid import PID

class LaunchScenario(Scenario):

  parameters = {'use_rcs': False,
                'max_autostage': 0,
                'target_altitude': 120000,
                'target_apt': 40.0,
                'turn_end_alt': 90000,
                'turn_start_alt': 1000,
                'turn_start_speed': 100,
                'min_pitch': 10,
                'pitch_offset': 15}

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

    min_pitch = self.parameters['min_pitch'] - self.parameters['pitch_offset']
    max_pitch = self.parameters['min_pitch'] + self.parameters['pitch_offset']
    self.pitch_pid = PID(0.5, 0.05, 0.2, min_pitch, max_pitch)

  def step(self):
    if self.apoapsis() >= self.parameters['target_altitude']:
      self.meco()
      # stop this scenario if above atmo and target apo achieved
      if self.vessel.situation.name == 'sub_orbital':
        return False

    if self.vessel.situation.name == 'pre_launch':
      self.handle_prelaunch()
    else:
      auto_stage(self.vessel, self.parameters['max_autostage'])

    if self.vessel.situation.name == 'flying':
      if self.speed() > self.parameters['turn_start_speed']:
        self.grav_turn()

    if (self.vessel.situation.name == 'sub_orbital' and
       self.apoapsis() < self.parameters['target_altitude']):
      self.burn_to_apo()

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
    if not hasattr(self, 'turn_start_alt'):
      self.turn_start_alt = self.altitude()

    frac_den = self.parameters['turn_end_alt'] - self.turn_start_alt
    frac_num = self.altitude() - self.turn_start_alt
    turn_angle = 90 * frac_num / frac_den
    target_pitch = max(self.parameters['min_pitch'], 90 - turn_angle)
    self.ap.target_pitch_and_heading(target_pitch, 90)

    if self.per_time() < self.apo_time():
      new_thr = 1
    else:
      new_thr = self.thr_pid.seek(self.target_apt, self.apo_time(), self.ut())

    self.control.throttle = new_thr

  def burn_to_apo(self):
    apo_err = self.parameters['target_altitude'] - self.apoapsis()
    if apo_err < 1000:
      self.control.throttle = .1
    else:
      self.control.throttle = 1

    half_period = self.vessel.orbit.period / 2
    if half_period < self.apo_time():
      tgt_pitch = self.parameters['min_pitch'] + self.parameters['pitch_offset']
    else:
      tgt_pitch = self.pitch_pid.seek(self.target_apt, self.apo_time(), self.ut())

    self.ap.target_pitch_and_heading(tgt_pitch, 90)

  def on_high_alt(self):
    self.target_apt = 60
    if len(find_all_fairings(self.vessel)) > 0:
      fairings = filter(lambda f: getattr(f, 'tag', None) != "noauto",
                        find_all_fairings(self.vessel))
      for f in fairings:
        jettison_fairing(f)

  def meco(self):
    self.control.throttle = 0
    self.ap.reference_frame = self.vessel.orbital_reference_frame
    self.ap.target_direction = (0, 1, 0)
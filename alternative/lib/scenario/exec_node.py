from .scenario import Scenario
from ..nav import compute_burn_time


class ExecNodeScenario(Scenario):

  parameters = {'lead_time': 15,
                'use_rcs': True}

  def pre_run(self):
    self.conn = self.context['conn']
    self.ksc = self.conn.space_center
    self.vessel = self.ksc.active_vessel
    self.control = self.vessel.control
    self.ap = self.vessel.auto_pilot

    self.ut = self.conn.add_stream(getattr, self.ksc, 'ut')
    self.rem_dv = self.conn.add_stream(getattr, self.parameters['node'],
                                       'remaining_delta_v')

    self.init_ui()

  def step(self):
    # check node
    if 'node' not in self.parameters:
      return False

    self.update_ui()

    if self.context.get('burning', False):
      self.burn()
    else:
      self.pre_burn()

  def post_run(self):
    self.context['ui']['panel'].remove()

  def pre_burn(self):
    burn_start_ut = self.burn_start_ut()

    # burn start ut has passed?
    if self.ut() >= burn_start_ut:
      self.point_to_node()
      self.context['burning'] = True
      return

    # enough time to warp?
    lead_time = self.parameters['lead_time']
    if self.ut() < (burn_start_ut - lead_time * 2):
      self.ksc.rails_warp_factor = 7
    elif self.ut() < (burn_start_ut - lead_time):
      self.ksc.rails_warp_factor = 2
    else:
      self.ksc.rails_warp_factor = 0
      self.point_to_node()

  def burn(self):
    rem_dv = self.rem_dv()
    node = self.parameters['node']

    if rem_dv - self.context.get('last_remaining', rem_dv) > 0.01:
      self.control.throttle = 0
      self.ap.disengage()
      self.parameters['node'].remove()
      del self.parameters['node']
      return

    part_done = max(0, round((node.delta_v - rem_dv) / node.delta_v, 2))
    self.control.throttle = 1 - part_done

    self.context['last_remaining'] = rem_dv

  def point_to_node(self):
    node = self.parameters['node']
    self.control.rcs = self.parameters['use_rcs']
    self.ap.engage()
    self.ap.reference_frame = node.reference_frame
    self.ap.target_direction = (0, 1, 0)

  def burn_start_ut(self):
    node = self.parameters['node']
    burn_time = compute_burn_time(self.vessel, node.delta_v)
    return node.ut - burn_time / 2

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

    texts['step'] = panel.add_text("Step: Execute node")
    texts['step'].rect_transform.position = (-50, 65)
    texts['step'].color = (.2, .5, 1)
    texts['step'].size = 14

    texts['burning'] = panel.add_text("Burning: False")
    texts['burning'].rect_transform.position = (-50, 40)
    texts['burning'].color = (1, 1, 1)
    texts['burning'].size = 14

    texts['node_ut'] = panel.add_text("Node in: 0 s")
    texts['node_ut'].rect_transform.position = (-50, 20)
    texts['node_ut'].color = (1, 1, 1)
    texts['node_ut'].size = 14

    texts['node_dv'] = panel.add_text("Total dV: 0 m/s")
    texts['node_dv'].rect_transform.position = (-50, 00)
    texts['node_dv'].color = (1, 1, 1)
    texts['node_dv'].size = 14

    texts['rem_dv'] = panel.add_text("Rem. dV: 0 m/s")
    texts['rem_dv'].rect_transform.position = (-50, -20)
    texts['rem_dv'].color = (1, 1, 1)
    texts['rem_dv'].size = 14

    texts['last_rem_dv'] = panel.add_text("Prev rem. dV: 0 m/s")
    texts['last_rem_dv'].rect_transform.position = (-50, -40)
    texts['last_rem_dv'].color = (1, 1, 1)
    texts['last_rem_dv'].size = 14

    self.context['ui'] = {'panel': panel, 'texts': texts}

  def update_ui(self):
    texts = self.context['ui']['texts']
    node = self.parameters['node']
    last_rem_dv = self.context.get('last_remaining', self.rem_dv())

    texts['burning'].content = "Burning: %s" % self.context.get('burning', False)
    texts['node_ut'].content = "Node in: %d s" % (node.ut - self.ut())
    texts['node_dv'].content = "Total dV: %.1f m/s" % node.delta_v
    texts['rem_dv'].content = "Rem. dV: %.1f m/s" % self.rem_dv()
    texts['last_rem_dv'].content = "Prev rem. dV: %.1f m/s" % last_rem_dv

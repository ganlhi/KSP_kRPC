"""Mission runner module

  Expected format of mission steps:
  [
    {"name": "step_name", "function": step_func},
    ...
  ]

  with step_func being a function like:

  def step_func(mission):
    ...
"""

class Mission:
  """Mission runner

    Handles a multi-steps mission, providing an API to
    cycle through an update cycle and advance further
    in mission steps
  """

  conn = None
  done = False
  running = False
  current_step = {"name": None, "first_call": True, "start_ut": None}
  steps = None
  steps_names = None
  parameters = {}
  ut = None

  def __init__(self, conn, steps, parameters=None):
    """Stores kRPC connection and mission steps"""
    self.conn = conn
    self.steps = steps
    self.steps_names = [s["name"] for s in steps]
    if type(parameters) is dict:
      self.parameters = parameters
    self.ut = conn.add_stream(getattr, conn.space_center, 'ut')

  def run(self, starting_step=None):
    """Run as a generator"""
    self.start(starting_step)
    while self.running:
      self.update()
      yield

  def terminate(self):
    """Explicitly stops the update cycle"""
    self.done = True
    self.running = False
    print("[mission]", "Terminating")

  def start(self, step=None):
    """Start running the update cycle

      Optionally, a starting step other than the
      first one can be chosen (to restart an
      ongoing mission).
    """
    if len(self.steps) == 0:
      self.terminate()
    else:
      if step is None:
        step = self.steps_names[0]

      self.current_step["name"] = step
      self.current_step["start_ut"] = self.ut()
      self.current_step["first_call"] = True

      self.running = True
      self.done = False

      print("[mission]", "Starting at step", step)

  def update(self):
    """Executes the current step if mission is running"""
    if self.running:
      self.steps[self.current_step["name"]]["function"](self)
      self.current_step["first_call"] = False

  def next(self, auto_terminate=True):
    """Advances to the next step, if there is one

      Unless auto_terminate is True, if no other step,
      the mission is automatically terminated
    """
    cur_pos = self.steps_names.index(self.current_step["name"])
    if cur_pos >= len(self.steps_names):
      if auto_terminate:
        self.terminate()
    else:
      self.current_step["name"] = self.steps_names[cur_pos + 1]
      self.current_step["first_call"] = True
      self.current_step["start_ut"] = self.ut()
      print("[mission]", "Switching to step", self.current_step["name"])

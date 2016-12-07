"""Mission runner module

  Expected format of mission steps:
  dict({
    "step_name": step_func,
    ...
  })

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
  current_step = None
  steps = None
  steps_names = None

  def __init__(self, conn, steps):
    """Stores kRPC connection and mission steps"""
    self.conn = conn
    self.steps = steps
    self.steps_names = list(self.steps.keys())

  def terminate(self):
    """Explicitly stops the update cycle"""
    self.done = True
    self.running = False

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

      self.current_step = step
      self.running = True
      self.done = False

  def update(self):
    """Executes the current step if mission is running"""
    if self.running:
      self.steps[self.current_step](self)

  def next(self, auto_terminate=True):
    """Advances to the next step, if there is one

      Unless auto_terminate is True, if no other step,
      the mission is automatically terminated
    """
    cur_pos = self.steps_names.index(self.current_step)
    if cur_pos >= len(self.steps_names):
      if auto_terminate:
        self.terminate()
    else:
      self.current_step = self.steps_names[cur_pos + 1]

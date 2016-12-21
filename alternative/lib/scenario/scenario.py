import time

class Scenario:

  parameters = {}
  events = {}
  context = {}

  def __init__(self, parameters=None, events=None, context=None, stepfunc=None):
    if type(parameters) is dict:
      self.parameters = {**self.parameters, **parameters}

    if type(events) is dict:
      self.events = {**self.events, **events}

    if type(context) is dict:
      self.context = {**self.context, **context}

    self.stepfunc = stepfunc

  def handle_events(self):
    stop = False

    for name in list(self.events):
      event = self.events[name]
      if event['condition'](self) is True:
        res_event = event['action'](self)
        stop = stop or res_event is False
        if not getattr(event, 'preserve', False):
          del self.events[name]

    return not stop

  def pre_run(self):
    pass

  def run(self):
    self.pre_run()
    while True:
      res_step = self.step()
      res_events = self.handle_events()

      if res_step is False or res_events is False:
        break

      time.sleep(0.1)

    self.post_run()

  def post_run(self):
    pass

  def step(self):
    if callable(self.stepfunc):
      return self.stepfunc(self)

import time

class Scenario:

  def __init__(self, parameters=None, events=None, context=None, stepfunc=None):
    if type(parameters) is not dict:
      self.parameters = {}
    else:
      self.parameters = parameters

    if type(events) is not dict:
      self.events = {}
    else:
      self.events = events

    if type(context) is not dict:
      self.context = {}
    else:
      self.context = context

    self.stepfunc = stepfunc


  def handle_events(self):
    stop = False

    for name, event in self.events.items():
      print('Handling event %s' % name)
      if event['condition'](self.context) is True:
        print('Action on %s' % name)
      stop = stop or (event['action'](self.context) is False)

    return not stop


  def run(self):
    while True:
      res_step = self.step()
      res_events = self.handle_events()

      if res_step is False or res_events is False:
        break

      time.sleep(0.1)


  def step(self):
    if callable(self.stepfunc):
      self.stepfunc(self)
    else:
      pass

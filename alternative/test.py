import time
from lib.scenario import Scenario

def long_task(parameters=None, events=None):
  if parameters is None:
    parameters = {}

  if events is None:
    events = {}

  print('Init long task')

  n = 0
  max_n = parameters.get('max_n', 10)

  while True:
    n += 1
    print('Loop %d' % n)

    if n >= max_n:
      break

    res_events = handle_events(events, {'n': n})
    if res_events is False:
      break

    time.sleep(0.1)


def handle_events(events, context=None):
  if type(events) is not dict:
    raise Exception('Bad parameter')

  print('Handling events')

  stop = False

  for name, event in events.items():
    print('Handling event %s' % name)
    if event['condition'](context) is True:
      print('Action on %s' % name)
      stop = stop or (event['action'](context) is False)

  return not stop


if __name__ == '__main__':
  # print('# First try')
  # long_task()

  # print('# Second try')
  # long_task(parameters={'max_n': 12})

  # print('# Third try')

  events = {
    'just_log': {
      'condition': lambda scen: scen.context['n'] % 2 == 0,
      'action': lambda _: print('n is even')
    },

    'stop_at_8': {
      'condition': lambda scen: scen.context['n'] == 8,
      'action': lambda _: False
    }
  }
  # long_task(events=events)

  def step(scen):
    scen.context['n'] += 1
    print('Loop %d' % scen.context['n'])
    if scen.context['n'] >= 10:
      return False

  s = Scenario(context={'n': 0}, stepfunc=step, events=events)
  s.run()

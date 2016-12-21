from lib.scenario import Scenario


def step(scen):
  scen.context['n'] += 1
  print('Loop %d' % scen.context['n'])
  if scen.context['n'] >= 10:
    return False


if __name__ == '__main__':
  print('# First try')
  Scenario(context={'n': 0}, stepfunc=step).run()

  print('# Second try')

  events = {
    'just_log': {
      'condition': lambda scen: scen.context['n'] % 2 == 0,
      'action': lambda scen: print('%d is even' % scen.context['n'])
    },

    'stop_at_8': {
      'condition': lambda scen: scen.context['n'] == 8,
      'action': lambda _: False
    }
  }


  Scenario(context={'n': 0}, stepfunc=step, events=events).run()

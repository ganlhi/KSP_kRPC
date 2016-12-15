import time

def runner():
  n = 0
  while True:
    print('n', n)
    yield n < 10
    n += 1


def main():
  print('begin main')
  r = runner()
  while next(r):
    print('begin main loop')
    time.sleep(0.5)
    print('end main loop')
  print('end main')


if __name__ == '__main__':
  main()

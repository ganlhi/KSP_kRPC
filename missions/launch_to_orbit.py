"""Generic mission to launch to orbit around orbit"""

import time
import krpc
from lib.mission import Mission
from lib.steps.launch import all_steps


if __name__ == "__main__":
  conn = krpc.connect()
  mission = Mission(conn, all_steps).run()

  while next(mission):
    time.sleep(0.01)

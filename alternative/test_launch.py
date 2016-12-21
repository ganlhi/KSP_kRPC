import krpc
from lib.scenario.launch import LaunchScenario


if __name__ == '__main__':
    conn = krpc.connect()
    LaunchScenario(context={'conn': conn}).run()
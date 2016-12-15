import time
import importlib
import krpc


def watch():
    conn = None
    vessel = None

    while True:
        try:
            if conn is None:
                try:
                    conn = krpc.connect()
                except krpc.error.NetworkError:
                    conn = None
                    print("[watch] Waiting for kRPC connection")
                    time.sleep(10)
                    continue

            old_vessel = vessel
            if conn.krpc.current_game_scene.name == 'flight':
                vessel = conn.space_center.active_vessel
            else:
                vessel = None

            if vessel is None:
                print("[watch] Waiting for active vessel")
                time.sleep(10)
                continue
            else:
                if old_vessel is None:
                    boot(vessel)
                elif old_vessel.name != vessel.name:
                    boot(vessel)
                else:
                    time.sleep(10)

            time.sleep(0.1)
        except ConnectionError:
            conn = None
            time.sleep(10)


def boot(vessel):
    try:
        module = importlib.import_module('boot.' + vessel.name)
        module.boot()
    except ImportError:
        print("[watch] No boot script for vessel", vessel.name)
    except AttributeError:
        print("[watch] Boot file for vessel", vessel.name,
              "does not have a boot function")


if __name__ == "__main__":
    watch()

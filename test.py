import krpc
from launch_apt40_guided import launch

conn = krpc.connect()

launch(conn, use_rcs=True)

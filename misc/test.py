import krpc
from launch_apt40_guided import launch

conn = krpc.connect()

launch(conn, target_altitude=120000)

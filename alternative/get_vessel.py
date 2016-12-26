import krpc

conn = krpc.connect()
ksc = conn.space_center
vessel = ksc.active_vessel

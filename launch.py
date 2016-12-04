import time
import math
import krpc

conn = krpc.connect(name='Test launch')
vessel = conn.space_center.active_vessel

turn_start_altitude = 1000
turn_end_altitude = 45000
target_altitude = 80000

# Set up streams for telemetry
ut = conn.add_stream(getattr, conn.space_center, 'ut')
altitude = conn.add_stream(getattr, vessel.flight(), 'mean_altitude')
apoapsis = conn.add_stream(getattr, vessel.orbit, 'apoapsis_altitude')
periapsis = conn.add_stream(getattr, vessel.orbit, 'periapsis_altitude')
eccentricity = conn.add_stream(getattr, vessel.orbit, 'eccentricity')
lqd_fuel = conn.add_stream(vessel.resources.amount, 'LiquidFuel')


# function for staging (used twice below)
def drop_stage1():
    time.sleep(0.5)
    vessel.control.activate_next_stage()
    time.sleep(1)
    vessel.control.activate_next_stage()


while not vessel.control.get_action_group(9):
    time.sleep(1)

print('Countdown...')
vessel.auto_pilot.target_pitch_and_heading(90, 90)
vessel.auto_pilot.engage()
vessel.control.throttle = 1
vessel.control.sas = False
vessel.control.rcs = False
vessel.control.set_action_group(9, False)
time.sleep(5)

print('Launch!')
vessel.control.activate_next_stage()
time.sleep(1)
vessel.control.activate_next_stage()

stage1_sep = False
turn_angle = 0
while True:

    # Gravity turn
    if altitude() > turn_start_altitude and altitude() < turn_end_altitude:
        turn_alt_diff = turn_end_altitude - turn_start_altitude
        frac = (altitude() - turn_start_altitude) / turn_alt_diff
        new_turn_angle = frac * 90
        if abs(new_turn_angle - turn_angle) > 0.5:
            turn_angle = new_turn_angle
            vessel.auto_pilot.target_pitch_and_heading(90-turn_angle, 90)

    # Staging
    if not stage1_sep:
        if lqd_fuel() < 0.1:
            vessel.control.throttle = 0
            drop_stage1()
            stage1_sep = True
            vessel.control.throttle = 1

    # Decrease throttle when approaching target apoapsis
    if apoapsis() > target_altitude*0.9:
        print('Approaching target apoapsis')
        break

# Disable engines when target apoapsis is reached
vessel.control.throttle = 0.25
while apoapsis() < target_altitude:
    pass

print('Target apoapsis reached')
vessel.control.throttle = 0

# Wait until out of atmosphere
print('Coasting out of atmosphere')
while altitude() < 70500:
    pass

# Drop first stage if needed
if not stage1_sep:
    drop_stage1()


# Plan circularization burn (using vis-viva equation)
print('Planning circularization burn')
mu = vessel.orbit.body.gravitational_parameter
r = vessel.orbit.apoapsis
a1 = vessel.orbit.semi_major_axis
a2 = r
v1 = math.sqrt(mu*((2./r)-(1./a1)))
v2 = math.sqrt(mu*((2./r)-(1./a2)))
delta_v = v2 - v1
node = vessel.control.add_node(
    ut() + vessel.orbit.time_to_apoapsis,
    prograde=delta_v
)

# Calculate burn time (using rocket equation)
F = vessel.available_thrust
Isp = vessel.specific_impulse * 9.82
m0 = vessel.mass
m1 = m0 / math.exp(delta_v/Isp)
flow_rate = F / Isp
burn_time = (m0 - m1) / flow_rate

# Orientate ship
print('Orientating ship for circularization burn')
vessel.auto_pilot.reference_frame = node.reference_frame
vessel.auto_pilot.target_direction = (0, 1, 0)
vessel.auto_pilot.wait()

# Wait until burn
print('Waiting until circularization burn')
burn_ut = ut() + vessel.orbit.time_to_apoapsis - (burn_time/2.)
lead_time = 5
if burn_ut > ut() + lead_time:
    conn.space_center.warp_to(burn_ut - lead_time)

# Execute burn
print('Ready to execute burn')
time_to_apoapsis = conn.add_stream(getattr, vessel.orbit, 'time_to_apoapsis')
while time_to_apoapsis() - (burn_time/2.) > 0:
    pass
print('Executing burn')
vessel.control.throttle = 1
time.sleep(burn_time - 0.1)
print('Fine tuning')
vessel.control.throttle = 0.05
remaining_burn = conn.add_stream(
    node.remaining_burn_vector, node.reference_frame
)
while remaining_burn()[1] > 0:
    pass
vessel.control.throttle = 0
node.remove()

print('Launch complete')

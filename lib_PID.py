class PID:

    def __init__(self, Kp=0.2, Ki=0.0, Kd=0.0, cMin=0, cMax=1):

        self.Kp = Kp
        self.Ki = Ki
        self.Kd = Kd
        self.cMin = cMin
        self.cMax = cMax

        self.seekP = 0.0
        self.P = 0.0
        self.I = 0.0
        self.D = 0.0
        self.oldT = -1
        self.oldInput = 0.0

    def seek(self, seekVal, curVal, ut):

        P = seekVal - curVal
        D = self.D
        I = self.I
        newInput = self.oldInput
        t = ut
        dT = t - self.oldT

        if self.oldT >= 0:
            if dT > 0:
                D = (P - self.P) / dT
                onlyPD = self.Kp * P + self.Kd * D

                if (self.I > 0 or onlyPD > self.cMin) and (self.I < 0 or onlyPD < self.cMax):
                    I = self.I + P * dT

                newInput = onlyPD + self.Ki * I

        newInput = max(self.cMin, min(self.cMax, newInput))

        self.seekP = seekVal
        self.P = P
        self.I = I
        self.D = D
        self.oldT = t
        self.oldInput = newInput

        return newInput

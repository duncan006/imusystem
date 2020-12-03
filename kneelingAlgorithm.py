#!/usr/bin/env python3
import math
import time

class kneelingDetection:
    def __init__(self, NMKG, mass, height, alpha, torqueCutoff, rampDelay, rampHold, rampSlope, torqueType, front_pid_proportion, rear_pid_proportion):
        self.NMKG = NMKG
        self.mass = mass
        self.height = height
        self.alpha = alpha
        self.torqueCutoff = torqueCutoff
        self.controllerType = torqueType
        self.front_pid_proportion = front_pid_proportion
        self.rear_pid_proportion = rear_pid_proportion
        
        #Inputs updated on the first loop
        self.thighAngleR = 0
        self.shankAngleR = 0
        
        self.thighAngleL = 0
        self.shankAngleL = 0
        
        self.thighRAngV  = 0
        self.shankRAngV  = 0
        
        self.thighLAngV  = 0
        self.shankLAngV  = 0
        
        self.kneeAngleR = 0
        self.kneeAngleL = 0
        
        #Perpetual variables for kneelingDetection()
        self.movingAvgLen = 50
        self.movingAvgGyThighR = []
        self.movingAvgGyThighL = []
        self.Rcounter = 0
        self.Lcounter = 0
        self.isKneeling = False
        self.wasKneeling = False
        self.stdMultiplier = 2
        self.counterDetectionLimit = 2
        self.startingToStand = False
        self.legWasForward = "X"
        
        #Perpetual values for torqueEstimation()
        self.A = 0.012
        self.B = -0.002
        self.C = -0.075
        
        #torqueWindow()
        self.timeLastKneeling = time.time()
        self.run_loop = False
        self.timeKneelStart = time.time()
        
        self.legForward = "X"
        self.lastLeg = "X"
        
        #torqueRamping()
        self.ramp_time_delay = rampDelay
        self.ramp_slope = rampSlope
        self.ramp_time_hold = rampHold
        
        self.ramp_time_increase = self.NMKG * self.mass / self.ramp_slope
        self.ramp_time_decrease = self.NMKG * self.mass / self.ramp_slope
        
        self.rampTorque = 0
        self.time_last_ramp_loop = 0
        
        
        #YuSu Torque Controller Values
        self.Mb = mass * (52.2/81.4) #kg
        self.Mt = mass * (19.6/81.4) #kg
        
        self.g = 9.81 #m/s
        
        self.Lb = height * 0.160901
        self.Lt = height * (0.441 / 1.784)
        self.Ltc = height * (0.245 / 1.784)
    
    
    
    
    
    
    
    #Main function to run for third party input and export
    def getTorque(self, rThigh, rShank, lThigh, lShank, loBack):
        
        self.thighAngleR = rThigh.zAngleZeroed
        self.shankAngleR = rShank.zAngleZeroed
        
        self.thighAngleL = lThigh.zAngleZeroed
        self.shankAngleL = lShank.zAngleZeroed
        
        self.thighRAngV  = rThigh.gyZ
        self.shankRAngV  = rShank.gyZ
        
        self.thighLAngV  = lThigh.gyZ
        self.shankLAngV  = lShank.gyZ
        
        self.loBackAng = loBack.zAngleZeroed
        
        if (self.legForward == "L"):
            self.lastLeg = "L"
        if (self.legForward == "R"):
            self.lastLeg = "R"
        if (self.legForward == "2"):
            self.lastLeg = "2"
        
        self.kneeAngleL = self.thighAngleL - self.shankAngleL
        self.kneeAngleR = self.thighAngleR - self.shankAngleR

        self.kneelingDetection()
        
        torqueR = 0
        torqueL = 0
        
        if self.controllerType == "pid":
            torqueL, torqueR = self.torqueEstimation(self.kneeAngleR, self.thighRAngV, self.kneeAngleL, self.thighLAngV)
        
        if self.controllerType == "yusu":
            torqueL = self.torqueYuSu("LEFT", self.thighAngleL, self.loBackAng)
            torqueR = self.torqueYuSu("RIGHT", self.thighAngleR, self.loBackAng)
            
        if self.controllerType == "ramp":
            if self.legForward == "R":
                torqueR = self.torqueRamping()
                torqueL = 0
            elif self.legForward == "L":
                torqueL = self.torqueRamping()
                torqueR = 0
        
            
        return torqueR, torqueL, self.kneeAngleR, self.kneeAngleL, self.legForward
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    def getTorqueFromVicon(self, rThigh, rShank, lThigh, lShank, RTA, LTA, BA):
        
        self.thighAngleR = RTA
        self.shankAngleR = rShank.zAngleZeroed
        
        self.thighAngleL = LTA
        self.shankAngleL = lShank.zAngleZeroed
        
        self.thighRAngV  = rThigh.gyZ
        self.shankRAngV  = rShank.gyZ
        
        self.thighLAngV  = lThigh.gyZ
        self.shankLAngV  = lShank.gyZ
        
        self.loBackAng = BA
        
        if (self.legForward == "L"):
            self.lastLeg = "L"
        if (self.legForward == "R"):
            self.lastLeg = "R"
        if (self.legForward == "2"):
            self.lastLeg = "2"
        
        self.kneeAngleL = self.thighAngleL - self.shankAngleL
        self.kneeAngleR = self.thighAngleR - self.shankAngleR

        self.kneelingDetection()
        
        #torqueL, torqueR = self.torqueEstimation(self.kneeAngleR, self.thighRAngV, self.kneeAngleL, self.thighLAngV)
        torqueL = self.torqueYuSu("LEFT", self.thighAngleL, self.loBackAng)
        torqueR = self.torqueYuSu("RIGHT", self.thighAngleR, self.loBackAng)
            
        return torqueR, torqueL, self.kneeAngleR, self.kneeAngleL, self.legForward
    
    
    
    
    
        
        
        
        
        
        
        
        
        
        
        
        
        
    
    
    def torqueYuSu(self, leg, thetaT, thetaB):
        TqEst1 = self.Mb * self.g * (   (self.Lb * math.sin(math.radians(thetaB)))   +   (self.Lt * math.sin(math.radians(-thetaT)))   )
        TqEst2 = self.Mt * self.g * self.Ltc * math.sin(math.radians(-thetaT))
        TqEst = (-0.5) * (TqEst1 + TqEst2)
        
        Tr = (self.alpha) * TqEst
        
        if True:   #alternate: (self.torqueWindow(leg)):
            if Tr <= self.torqueCutoff:
                return Tr
            else:
                return self.torqueCutoff
            
            if Tr < 0:
                return 0
            else:
                return Tr
            
        else:
            return 0
        
        
        
        
    
    
    
    
    
    
    
    
    
    
    
    def torqueRamping(self):
        if (self.time_last_ramp_loop != 0):
            timeStep = time.time() - self.time_last_ramp_loop
        else: 
            timeStep = 0.02
        
        timeFromKneelStart = time.time() - self.timeKneelStart
        rampingCurveEnd = self.ramp_time_delay + self.ramp_time_increase + self.ramp_time_hold + self.ramp_time_decrease
        
        #Test if kneeling, activate after delay. Configuration options in userinput.py
        if (timeFromKneelStart > self.ramp_time_delay) and (timeFromKneelStart < rampingCurveEnd) and (self.isKneeling == True):
            if (timeFromKneelStart < self.ramp_time_delay + self.ramp_time_increase):
                #increasing
                self.rampTorque = self.rampTorque + (timeStep * self.ramp_slope)
            elif (timeFromKneelStart < self.ramp_time_delay + self.ramp_time_increase + self.ramp_time_hold):
                #holding
                self.rampTorque = self.rampTorque
            elif (timeFromKneelStart < self.ramp_time_delay + self.ramp_time_increase + self.ramp_time_hold + self.ramp_time_delay):
                #decreasing
                self.rampTorque = self.rampTorque - (timeStep * self.ramp_slope)
                
            
            if (self.rampTorque > self.torqueCutoff):
                self.rampTorque = self.torqueCutoff
            elif (self.rampTorque < 0):
                self.rampTorque = 0
            
            self.time_last_ramp_loop = time.time()
            
        else:
            self.rampTorque = 0
            
        return self.rampTorque
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    def torqueEstimation(self, kneeAngleR, thighGyR, kneeAngleL, thighGyL):
        #NMKG - Newton-meters per kilogram (for initial tests, 0.15, 0.30, 0.45)
        #mass - kilograms of subject
        #angVel and kneeAngle are for leg with device. angVel is for thigh.
        #Knee angles oriented with staight leg at 0 degrees
        
        
        if True: # (self.torqueWindow("RIGHT")):
            torqueOutputR = (self.A * (kneeAngleR)) + (self.B * thighGyR) + self.C
            torqueOutputR = torqueOutputR * self.NMKG * self.mass * (12/15)
            if torqueOutputR > self.torqueCutoff:
                torqueOutputR = torqueCutoff
        else:
            torqueOutputR = 0
        
        
        if True: # (self.torqueWindow("LEFT")):
            torqueOutputL = (self.A * (kneeAngleL)) + (self.B * thighGyL) + self.C
            torqueOutputL = torqueOutputL * self.NMKG * self.mass * (12/15)
            if torqueOutputL > self.torqueCutoff:
                torqueOutputL = torqueCutoff
        else:
            torqueOutputL = 0
        
        
        if self.legForward[0] == "R":
            torqueOutputR = torqueOutputR * self.front_pid_proportion
            torqueOutputL = torqueOutputR * self.rear_pid_proportion
            
        if self.legForward[0] == "L":
            torqueOutputR = torqueOutputR * self.rear_pid_proportion
            torqueOutputL = torqueOutputR * self.front_pid_proportion
        

        return torqueOutputL, torqueOutputR
    
    
    
    
    
    
    
    
    
    
    
    def torqueWindow(self, leg):
        #Knee angles oriented with staight leg at 0 degrees
        #leg = "RIGHT" or "LEFT"
        import time
        
        if (leg == "RIGHT"):
            localKneeAngle = self.kneeAngleR
            match = "R"
        
        if (leg == "LEFT"):
            localKneeAngle = self.kneeAngleL
            match = "L"
            
        if (self.legForward == "2"):
            localKneeAngle = (self.kneeAngleL + self.kneeAngleR) / 2
        
        #self.run_loop is a single-trip-switch, that shuts off torque after 
        if time.time() - self.timeLastKneeling < .6 and localKneeAngle > 10 and self.run_loop:
            self.run_loop = True
        else:
            self.run_loop = False
        
        
        #Condition 1: self.legForward == match
        c1 = (self.legForward == match)
        
        #Condition 2: self.legForward == "2"
        c2 = (self.legForward == "2")
        
        #Condition 3: self.legForward == X and lastLeg == match and single-trip-switch
        c3 = ((self.legForward == "X") and (self.lastLeg == match) and (self.run_loop))
        
        #Condition 4: self.legForward == X and lastLeg == "2" and single-trip-switch
        c4 = ((self.legForward == "X") and (self.lastLeg == 2) and (self.run_loop))
            
        if c1 or c2 or c3 or c4:
            deliverTorque = True
            self.run_loop = True
            if self.isKneeling == True:
                self.timeLastKneeling = time.time()
        else:
            deliverTorque = False
            
        return deliverTorque
        
        
        
        
        
        
        
        
        
        
        
        
        
    def kneelingDetection(self):
        #Knee angles oriented with staight leg at 180 degrees
        import numpy as np
        
        #sets kneel start time when the switch from not kneeling to kneeling occurs
        if (self.isKneeling == True) and (self.wasKneeling == False):
            self.timeKneelStart = time.time()
        self.wasKneeling = self.isKneeling
        
        
    #Calculate mean and standard deviation of gyroscope data outside of if statements so that moving array is not compromised.
        self.movingAvgGyThighR.append(self.thighRAngV)
        self.movingAvgGyThighL.append(self.thighLAngV)

        if len(self.movingAvgGyThighR) > self.movingAvgLen:
            self.movingAvgGyThighR.pop(0)
        if len(self.movingAvgGyThighL) > self.movingAvgLen:
            self.movingAvgGyThighL.pop(0)

        Rmean = np.mean(self.movingAvgGyThighR)
        Rsd = np.std(self.movingAvgGyThighR) * self.stdMultiplier
            
        Lmean = np.mean(self.movingAvgGyThighL)
        Lsd = np.std(self.movingAvgGyThighL) * self.stdMultiplier
        
        if Rsd < 5:
            Rsd = Rsd * 2
        if Lsd < 5:
            Lsd = Lsd * 2
            
        R_upper_limit = Rmean + Rsd
        R_lower_limit = Rmean - Rsd
        
        L_upper_limit = Lmean + Lsd
        L_lower_limit = Lmean - Lsd
        
        R_thighR_shankL_angV = self.shankLAngV - self.thighRAngV
        L_thighL_shankR_angV = self.shankRAngV - self.thighLAngV
        
        
        
        
        
    #Implement early kneeling down detection via gyroscopes
        
        
        
        
        
        
        
    #Test if angle is past a rather large and easy to determine threshold (60 degrees from straight)
    #re-work to use sum of angles for a closer detection
        if (self.kneeAngleL > 60) and (self.kneeAngleR > 60):
            self.isKneeling = True
        else:
            self.isKneeling = False
            self.legForward = "X"
            

            
            
            
    #Test which foot is forward (or if both are backwards) using the angle of the shin to the horizontal.
    #Leg with horizontal shin is backwards, if both shins horizontal then both legs down.
    #To expand for kneeling on an angle, use the difference between the shin angles with a window for how close they can be, and the lesser/greater one is forward once it passes the threshold
        
        if self.isKneeling == True:
            legForwardThreshold = 30
            if abs(self.shankAngleR - self.shankAngleL) < legForwardThreshold:
                self.legForward = "2"
            #deep flexion test
                #if (rightKneeAngle < 60) and (leftKneeAngle < 60):
                    #self.legForward += "d"
            else:
                if self.shankAngleL > self.shankAngleR:
                    self.legForward = "L"
                    self.legWasForward = "L"
                elif self.shankAngleR > self.shankAngleL:
                    self.legForward = "R"
                    self.legWasForward = "R"
                    
                    
                    
                    
                    

#Detect a spike as the moment that the subject starts to stand up.
            if (self.thighRAngV < R_lower_limit) and (R_thighR_shankL_angV > R_upper_limit) and len(self.movingAvgGyThighR) > 20:
                #self.movingAvgGyThighR.pop(len(self.movingAvgGyThighR)-1)
                self.Rcounter = self.Rcounter + 1
            else:
                self.Rcounter = 0
                
            if (self.thighLAngV < L_lower_limit) and (L_thighL_shankR_angV > L_upper_limit) and len(self.movingAvgGyThighL) > 20:
                #self.movingAvgGyThighL.pop(len(self.movingAvgGyThighL)-1)
                self.Lcounter = self.Lcounter + 1
            else:
                self.Lcounter = 0
               
            
            
            
            
#Check for consecutive signals before setting to "standing up" mode.
            if (self.Rcounter >= self.counterDetectionLimit and self.legForward == "R") or (self.Lcounter >= self.counterDetectionLimit and self.legForward == "L"):
                self.startingToStand = True
            #((self.Rcounter >=1 and self.Lcounter >=1) and self.legForward == "2")
            
        if self.startingToStand == True:
            if (self.legWasForward == "R" and self.kneeAngleR > 20) or (self.legWasForward == "L" and self.kneeAngleL < 20):
                self.startingToStand = False
                self.legWasForward = "X"
            #self.legForward += "s"

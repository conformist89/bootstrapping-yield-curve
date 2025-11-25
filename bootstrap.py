import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import date
import bisect
from dataclasses import dataclass



def yearfrac(start_day, end_day, day_count = 360):
    return (end_day - start_day).days / day_count



class DiscountCurve:
    def __init__(self, spot_date):
        self.spot_date = spot_date
        self.sorted_dates = []
        self.rates = {}  # {maturity: yield}
        self.disc_factors = {}   # {maturity: discount_factor}
        
        
    def add_entry(self, dt, rate):
        """ Adding maturity and yield information """
        self.rates[dt] = rate
        self.sorted_dates.append(dt)

    def get_spot_rate_libor(self, dt):
        # if dt date coincides with the maturity date -> return the yield as rate 
        if dt in self.rates:
            return self.rates[dt]

        # find insertion position in sorted maturities
        i = bisect.bisect_left(self.sorted_dates, dt)


        if i == 0 or i == len(self.sorted_dates):
            raise ValueError("Date is outside discount curve range for interpolation.")


        d1 = self.sorted_dates[i-1]
        d2 = self.sorted_dates[i]


        t1 = yearfrac(dt, d2)
        t2 = yearfrac(d1, d2)
        

        r1 = self.rates[d1]
        r2 = self.rates[d2]

        q = t1 / t2

        # yield curve is linear in time
        return r1 * q + (1 - q) * r2

    def get_discount_factor_libor(self, dt):
        r = self.get_spot_rate_libor(dt) 

        T = yearfrac(self.spot_date, dt)

        disc_factor = 1.0 / (1.0 + r*T)

        return disc_factor



@dataclass
class LiborDeposit:
    spot_date: object
    maturity_date: object
    quote_pct: float 

    def add_to_curve(self, curve: DiscountCurve):
        r = self.quote_pct / 100.0
        curve.add_entry(self.maturity_date, r)

    def get_discount_factor(self, dt):
        r = self.quote_pct / 100.0
        T = yearfrac(self.spot_date, dt)
        disc_factor = 1.0 / (1.0 + r*T)

        return disc_factor 
    



@dataclass
class ForwardsDeposit:
    start_date: object
    maturity_date: object
    quote_pct: float   

    def add_to_curve(self, curve: DiscountCurve):
        frate = 1 - (self.quote_pct / 100.0)
        curve.add_entry(self.maturity_date, frate)

    def get_discount_factor(self, prev_disc_factor):
        delt = yearfrac(self.start_date, self.maturity_date)
        frate = 1 - (self.quote_pct / 100.0)
        # print("dT in days: ", delt)
        # print("Quote in pct: ", self.quote_pct)
        # print("Frate: ", frate)
        next_disc_factor = prev_disc_factor / (1 + frate * delt)

        return next_disc_factor
    
    def get_spot_rate(self, disc_factor, spot_date):
        
        delt = yearfrac(spot_date, self.maturity_date)
        spot_rate = (1 / disc_factor - 1)/ delt
        # print("discount factor: ", disc_fact)
        # print("delt: ", delt)
        return spot_rate
    


def bootstrap_curve(spot, instruments):
    curve = DiscountCurve(spot)
    # sort by final maturity
    instruments_sorted = sorted(instruments, key=lambda inst: inst.maturity_date)
    for inst in instruments_sorted:
        inst.add_to_curve(curve)
    return curve
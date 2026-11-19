class AllMetric:
    RatedPower = 'RatedPower'
    CumulativeEnergyPurchased = 'CumulativeEnergyPurchased'
    CumulativeGridFeedIn = 'CumulativeGridFeedIn'
    CumulativeConsumption = 'CumulativeConsumption'
    SOC = 'SOC'
    TotalChargeEnergy = 'TotalChargeEnergy'
    TotalDischargeEnergy = 'TotalDischargeEnergy'
    GeneratorFrequency = 'GeneratorFrequency'
    TotalGeneratorProduction = 'TotalGeneratorProduction'
    GenVoltage = 'GenVoltage'
    UPSLoadPower = 'UPSLoadPower'
    MIPower = 'MIPower'
    DCVoltagePV1 = 'DCVoltagePV1'
    DCVoltagePV2 = 'DCVoltagePV2'
    DCVoltagePV3 = 'DCVoltagePV3'
    DCVoltagePV4 = 'DCVoltagePV4'
    DCCurrentPV1 = 'DCCurrentPV1'
    DCCurrentPV2 = 'DCCurrentPV2'
    DCCurrentPV3 = 'DCCurrentPV3'
    DCCurrentPV4 = 'DCCurrentPV4'
    DCPowerPV1 = 'DCPowerPV1'
    DCPowerPV2 = 'DCPowerPV2'
    DCPowerPV3 = 'DCPowerPV3'
    DCPowerPV4 = 'DCPowerPV4'
    TotalDCInputPower = 'TotalDCInputPower'
    ACVoltageRUA = 'ACVoltageRUA'
    ACCurrentRUA = 'ACCurrentRUA'
    ACOutputFrequencyR = 'ACOutputFrequencyR'
    TotalActiveProduction = 'TotalActiveProduction'
    InverterOutputPowerL1L2 = 'InverterOutputPowerL1L2'
    GridFrequency = 'GridFrequency'
    GridVoltageL1L2 = 'GridVoltageL1L2'
    GridCurrentL1L2 = 'GridCurrentL1L2'
    ExternalCTPowerL1L2 = 'ExternalCTPowerL1L2'
    LoadVoltageL1L2 = 'LoadVoltageL1L2'
    TotalConsumptionPower = 'TotalConsumptionPower'
    BatteryVoltage = 'BatteryVoltage'
    BatteryCurrent = 'BatteryCurrent'
    BatteryPower = 'BatteryPower'
    DailyChargingEnergy = 'DailyChargingEnergy'
    DailyDischargingEnergy = 'DailyDischargingEnergy'
    DailyActiveProduction = 'DailyActiveProduction'
    TotalGridPower = 'TotalGridPower'
    DailyGridFeedIn = 'DailyGridFeedIn'
    DailyEnergyPurchased = 'DailyEnergyPurchased'
    DailyConsumption = 'DailyConsumption'
    DCTemperature = 'DC Temperature'
    ACTemperature = 'AC Temperature'
    TemperatureBattery = 'Temperature- Battery'

    @staticmethod
    def any(metric):
        return str(metric)


OBSERVER_METRICS = [
    AllMetric.SOC,
    AllMetric.BatteryPower,
    AllMetric.GridVoltageL1L2,
]

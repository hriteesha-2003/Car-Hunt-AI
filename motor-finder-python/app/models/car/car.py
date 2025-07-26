from pydantic import BaseModel, Field, field_validator, validator
from typing import Optional, List
from datetime import datetime



class BasicInfo(BaseModel):
    brand_id: str
    model: str
    year: int
    color: str
    registrationNumber:str
    vehicle_type:str
    mileage: Optional[str] = None
    fuel_type: Optional[str] = None
    fuel_capacity: Optional[str] = None
    engine_displacement: Optional[str] = None
    no_of_cylinders: Optional[str] = None
    max_power: Optional[str] = None
    max_torque: Optional[str] = None
    transmission_type: Optional[str] = None
    gearbox: Optional[str] = None
    drive_type: Optional[str] = None
    body_type: Optional[str] = None
    handedness: Optional[str] = None
    daily_price: Optional[int] = None
    weekly_price: Optional[int] = None
    monthly_price: Optional[int] = None
    price: Optional[int] = None
    

class TechnicalSpecification(BaseModel):
    fuel_type: str
    transmission: str
    mileage: Optional[str] = None
    engineSize: Optional[str] = None
    seating_capacity: str
    

class Dimensions(BaseModel):
    seating_capacity: int
    no_of_doors: int
    boot_space: Optional[str]
    ground_clearance_unladen: Optional[str]
    length: Optional[str]
    width: Optional[str]
    height: Optional[str]
    wheel_base: Optional[str]

class SuspensionAndBrakes(BaseModel):
    front_suspension: str
    rear_suspension: str
    front_brake_type: str
    rear_brake_type: str
    steering_type: str
    steering_column: str

class ComfortFeatures(BaseModel):
    adjustable_steering: Optional[str]
    height_adjustable_driver_seat: Optional[bool]
    automatic_climate_control: Optional[bool]
    accessory_power_outlet: Optional[bool]
    vanity_mirror: Optional[bool]
    adjustable_headrest: Optional[bool]
    parking_sensors: Optional[str]
    keyless_entry: Optional[bool]
    cooled_glovebox: Optional[bool]
    usb_charger_front: Optional[bool]
    gear_shift_indicator: Optional[bool]
    follow_me_home_headlamps: Optional[bool]
    additional_features: Optional[str]

class InteriorFeatures(BaseModel):
    tachometer: Optional[bool]
    glove_box: Optional[bool]
    additional_features: Optional[str]
    upholstery: Optional[str]
    digital_cluster: Optional[bool]
    semi_digital_cluster_size: Optional[str]

class ExteriorFeatures(BaseModel):
    rain_sensing_wiper: Optional[bool]
    rear_window_wiper: Optional[bool]
    rear_window_washer: Optional[bool]
    rear_window_defogger: Optional[bool]
    wheel_covers: Optional[bool]
    rear_spoiler: Optional[bool]
    orvm_turn_indicators: Optional[bool]
    integrated_antenna: Optional[bool]
    roof_rails: Optional[bool]
    fog_lights_front: Optional[bool]
    antenna_type: Optional[str]
    boot_opening: Optional[str]
    puddle_lamps: Optional[bool]
    orvm_powered_folding: Optional[bool]
    tyre_size: Optional[str]
    tyre_type: Optional[str]
    wheel_size: Optional[str]
    led_drls: Optional[bool]
    led_headlamps: Optional[bool]
    additional_exterior_features: Optional[str]

class SafetyFeatures(BaseModel):
    abs: bool
    central_locking: bool
    no_of_airbags: int
    driver_airbag: bool
    passenger_airbag: bool
    side_airbag_rear: Optional[bool]
    day_night_rear_view_mirror: Optional[bool]
    ebd: Optional[bool]
    seat_belt_warning: Optional[bool]
    engine_immobilizer: Optional[bool]
    esc: Optional[bool]
    rear_camera: Optional[str]
    speed_sensing_auto_door_lock: Optional[bool]
    seatbelt_pretensioners: Optional[str]

class EntertainmentFeatures(BaseModel):
    radio: Optional[bool]
    bluetooth_connectivity: Optional[bool]
    touchscreen: Optional[bool]
    touchscreen_size: Optional[str]
    android_auto: Optional[bool]
    apple_carplay: Optional[bool]
    no_of_speakers: Optional[int]
    rear_touchscreen: Optional[bool]
    infotainment_additional_features: Optional[str]

# AddCar 
class AddCar(BaseModel):
    agent_id: Optional[str] = None  
    company_id: str 
    vehicle_type: Optional[List[str]] = None
    is_featured: Optional[bool] = None
    basic_info: BasicInfo
    technical_specification: TechnicalSpecification
    description: str
    dimensions: Optional[Dimensions] = None
    suspension_and_brakes: Optional[SuspensionAndBrakes] = None
    comfort_features: Optional[ComfortFeatures] = None
    interior_features: Optional[InteriorFeatures] = None
    exterior_features: Optional[ExteriorFeatures] = None
    safety_features: Optional[SafetyFeatures] = None
    entertainment_features: Optional[EntertainmentFeatures] = None
    @field_validator("vehicle_type", mode="before")
    @classmethod
    def split_vehicle_type(cls, value):
        if isinstance(value, str):
            return [v.strip() for v in value.split(",")]
        return value

class UpdateBasicInfo(BaseModel):
    brand_id: Optional[str] = None
    model: Optional[str] = None
    year: Optional[int] = None
    color: Optional[str] = None
    mileage: Optional[str] = None
    fuel_type: Optional[str] = None
    fuel_capacity: Optional[str] = None
    engine_displacement: Optional[str] = None
    no_of_cylinders: Optional[int] = None
    max_power: Optional[str] = None
    max_torque: Optional[str] = None
    transmission_type: Optional[str] = None
    gearbox: Optional[str] = None
    drive_type: Optional[str] = None
    body_type: Optional[str] = None
    description: Optional[str]
    handedness: Optional[str] = None
    price: Optional[int] = None
    daily_price: Optional[int] = None
    weekly_price: Optional[int] = None
    monthly_price: Optional[int] = None

class UpdateTechnicalSpecification(BaseModel):
    fuel_type: Optional[str] = None
    transmission: Optional[str] = None
    mileage: Optional[str] = None
    engineSize: Optional[str] = None
    seating_capacity: Optional[str] = None  

class UpdateDimensions(BaseModel):
    seating_capacity: Optional[int] = None
    no_of_doors: Optional[int] = None
    boot_space: Optional[str] = None
    ground_clearance_unladen: Optional[str] = None
    length: Optional[str] = None
    width: Optional[str] = None
    height: Optional[str] = None
    wheel_base: Optional[str] = None

class UpdateSuspensionAndBrakes(BaseModel):
    front_suspension: Optional[str] = None
    rear_suspension: Optional[str] = None
    front_brake_type: Optional[str] = None
    rear_brake_type: Optional[str] = None
    steering_type: Optional[str] = None
    steering_column: Optional[str] = None

class UpdateComfortFeatures(BaseModel):
    adjustable_steering: Optional[str] = None
    height_adjustable_driver_seat: Optional[bool] = None
    automatic_climate_control: Optional[bool] = None
    accessory_power_outlet: Optional[bool] = None
    vanity_mirror: Optional[bool] = None
    adjustable_headrest: Optional[bool] = None
    parking_sensors: Optional[str] = None
    keyless_entry: Optional[bool] = None
    cooled_glovebox: Optional[bool] = None
    usb_charger_front: Optional[bool] = None
    gear_shift_indicator: Optional[bool] = None
    follow_me_home_headlamps: Optional[bool] = None
    additional_features: Optional[str] = None

class UpdateInteriorFeatures(BaseModel):
    tachometer: Optional[bool] = None
    glove_box: Optional[bool] = None
    additional_features: Optional[str] = None
    upholstery: Optional[str] = None
    digital_cluster: Optional[bool] = None
    semi_digital_cluster_size: Optional[str] = None

class UpdateExteriorFeatures(BaseModel):
    rain_sensing_wiper: Optional[bool] = None
    rear_window_wiper: Optional[bool] = None
    rear_window_washer: Optional[bool] = None
    rear_window_defogger: Optional[bool] = None
    wheel_covers: Optional[bool] = None
    rear_spoiler: Optional[bool] = None
    orvm_turn_indicators: Optional[bool] = None
    integrated_antenna: Optional[bool] = None
    roof_rails: Optional[bool] = None
    fog_lights_front: Optional[bool] = None
    antenna_type: Optional[str] = None
    boot_opening: Optional[str] = None
    puddle_lamps: Optional[bool] = None
    orvm_powered_folding: Optional[bool] = None
    tyre_size: Optional[str] = None
    tyre_type: Optional[str] = None
    wheel_size: Optional[str] = None
    led_drls: Optional[bool] = None
    led_headlamps: Optional[bool] = None
    additional_exterior_features: Optional[str] = None

class UpdateSafetyFeatures(BaseModel):
    abs: Optional[bool] = None
    central_locking: Optional[bool] = None
    no_of_airbags: Optional[int] = None
    driver_airbag: Optional[bool] = None
    passenger_airbag: Optional[bool] = None
    side_airbag_rear: Optional[bool] = None
    day_night_rear_view_mirror: Optional[bool] = None
    ebd: Optional[bool] = None
    seat_belt_warning: Optional[bool] = None
    engine_immobilizer: Optional[bool] = None
    esc: Optional[bool] = None
    rear_camera: Optional[str] = None
    speed_sensing_auto_door_lock: Optional[bool] = None
    seatbelt_pretensioners: Optional[str] = None

class UpdateEntertainmentFeatures(BaseModel):
    radio: Optional[bool] = None
    bluetooth_connectivity: Optional[bool] = None
    touchscreen: Optional[bool] = None
    touchscreen_size: Optional[str] = None
    android_auto: Optional[bool] = None
    apple_carplay: Optional[bool] = None
    no_of_speakers: Optional[int] = None
    rear_touchscreen: Optional[bool] = None
    infotainment_additional_features: Optional[str] = None

# Update car model
class UpdateCar(BaseModel):
    agent_id: Optional[str] = None
    company_id: Optional[str] = None
    vehicle_type: Optional[List[str]] = None
    is_featured: Optional[bool] = None
    basic_info: Optional[UpdateBasicInfo] = None
    technical_specification: Optional[UpdateTechnicalSpecification] = None
    dimensions: Optional[UpdateDimensions] = None
    suspension_and_brakes: Optional[UpdateSuspensionAndBrakes] = None
    comfort_features: Optional[UpdateComfortFeatures] = None
    interior_features: Optional[UpdateInteriorFeatures] = None
    exterior_features: Optional[UpdateExteriorFeatures] = None
    safety_features: Optional[UpdateSafetyFeatures] = None
    entertainment_features: Optional[UpdateEntertainmentFeatures] = None

    @field_validator("vehicle_type", mode="before")
    @classmethod
    def parse_vehicle_type(cls, value):
        if isinstance(value, str):
            return [v.strip() for v in value.split(",")]
        return value

class vehicle_type(BaseModel):
    type: str


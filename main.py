from astropy.coordinates import EarthLocation, AltAz, get_body
from astropy.time import Time
from astroplan import Observer
import astropy.units as u
from datetime import datetime
import pytz


location = EarthLocation(lat=28.6139*u.deg, lon=77.2090*u.deg, height=216*u.m)
observer = Observer(location=location, timezone="Asia/Kolkata")


planets = ['mercury', 'venus', 'mars', 'jupiter', 'saturn', 'uranus', 'neptune']


def check_planet_visibility(planet_name, observation_time=None):
    
    if observation_time is None:
        observation_time = Time(datetime.now(pytz.timezone("Asia/Kolkata")))
    
   
    try:
        planet_coord = get_body(planet_name.lower(), observation_time, location)
    except ValueError:
        return f"Error: '{planet_name}' is not recognized. Try one of: {', '.join(planets)}."
    
    
    altaz_frame = AltAz(obstime=observation_time, location=location)
    planet_altaz = planet_coord.transform_to(altaz_frame)
    
    
    altitude = planet_altaz.alt.deg
    azimuth = planet_altaz.az.deg
    
    
    if altitude > 10:
        return (f"{planet_name.capitalize()} is visible from New Delhi!\n"
                f"Altitude: {altitude:.2f} degrees\n"
                f"Azimuth: {azimuth:.2f} degrees\n"
                f"Time (IST): {observation_time.to_datetime(pytz.timezone('Asia/Kolkata'))}")
    else:
        return (f"{planet_name.capitalize()} is not visible from New Delhi at this time.\n"
                f"Altitude: {altitude:.2f} degrees (below 10 degrees or horizon).")


print("Enter planet names to check visibility from New Delhi, India.")
print(f"Supported planets: {', '.join(planets)}")
print("Type 'exit' to quit.\n")

while True:
    planet_input = input("Enter a planet name: ").strip().lower()
    if planet_input == 'exit':
        print("Exiting program.")
        break
    if planet_input not in planets:
        print(f"Error: '{planet_input}' is not recognized. Try one of: {', '.join(planets)}.")
        continue
    
    
    result = check_planet_visibility(planet_input)
    print(result)
    print()
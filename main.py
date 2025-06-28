import streamlit as st
try:
    from astropy.coordinates import EarthLocation, AltAz, get_body, SkyCoord
    from astropy.time import Time
    from astroplan import Observer
    import astropy.units as u
except ImportError as e:
    st.error(f"Failed to import Astropy modules: {e}. Please ensure 'astropy' and 'astroplan' are installed.")
    st.stop()

from datetime import datetime, timedelta
import pytz
import plotly.graph_objects as go
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import numpy as np
import warnings
try:
    from astropy.utils.iers import IERS_Auto
    from astropy.utils.data import download_file
except ImportError as e:
    st.error(f"Failed to import Astropy IERS modules: {e}. Using cached data.")
    IERS_Auto = None

# Suppress IERS warnings and handle SSL issue
warnings.filterwarnings('ignore', category=RuntimeWarning)
if IERS_Auto:
    try:
        IERS_Auto().open(download_file('finals2000A.all', allow_insecure=True))
    except Exception as e:
        st.warning(f"Could not update IERS data ({e}). Using cached data.")

# Supported celestial bodies and constellations (removed 'moon')
bodies = ['mercury', 'venus', 'mars', 'jupiter', 'saturn', 'uranus', 'neptune', 'sirius', 'vega']
constellations = {
    'sirius': 'Canis Major',
    'vega': 'Lyra'
}

# Telescope recommendations with magnitudes (removed 'moon')
telescope_recommendations = {
    'mercury': {'magnitude': 0.0, 'recommendation': 'Binoculars or 3-inch telescope (bright but small).'},
    'venus': {'magnitude': -4.6, 'recommendation': 'Naked eye or binoculars (very bright).'},
    'mars': {'magnitude': -2.0, 'recommendation': '4-inch telescope for surface details.'},
    'jupiter': {'magnitude': -2.7, 'recommendation': '4-inch telescope for moons and bands.'},
    'saturn': {'magnitude': 0.7, 'recommendation': '6-inch telescope for rings.'},
    'uranus': {'magnitude': 5.7, 'recommendation': '6-inch telescope in dark skies.'},
    'neptune': {'magnitude': 7.8, 'recommendation': '8-inch telescope in dark skies.'},
    'sirius': {'magnitude': -1.46, 'recommendation': 'Naked eye or binoculars (bright star).'},
    'vega': {'magnitude': 0.03, 'recommendation': 'Naked eye or binoculars (bright star).'}
}

# Function to check visibility and best time
def check_visibility(body_name, observation_time, location):
    try:
        if body_name.lower() in ['sirius', 'vega']:
            body_coord = SkyCoord.from_name(body_name.lower())
        else:
            body_coord = get_body(body_name.lower(), observation_time, location)
        altaz_frame = AltAz(obstime=observation_time, location=location)
        body_altaz = body_coord.transform_to(altaz_frame)
        altitude = body_altaz.alt.deg
        azimuth = body_altaz.az.deg
        best_time, max_altitude = find_best_time(body_name, observation_time, location)
        return {
            'altitude': altitude,
            'azimuth': azimuth,
            'visible': altitude > 10,
            'best_time': best_time,
            'max_altitude': max_altitude
        }, None, body_coord
    except Exception as e:
        return None, f"Error: Unable to find coordinates for '{body_name}' ({e}).", None

# Function to find best viewing time
def find_best_time(body_name, start_time, location):
    times = [start_time + timedelta(hours=i) for i in range(25)]
    max_altitude = -90
    best_time = start_time
    for t in times:
        try:
            if body_name.lower() in ['sirius', 'vega']:
                coord = SkyCoord.from_name(body_name.lower())
            else:
                coord = get_body(body_name.lower(), t, location)
            altaz = coord.transform_to(AltAz(obstime=t, location=location))
            if altaz.alt.deg > max_altitude:
                max_altitude = altaz.alt.deg
                best_time = t
        except:
            continue
    return best_time, max_altitude

# Function to plot visibility timeline
def plot_visibility_timeline(body_name, observation_time, location, days=1):
    hours = int(days * 24)
    times = [observation_time + timedelta(hours=i) for i in range(hours + 1)]
    altitudes = []
    for t in times:
        try:
            if body_name.lower() in ['sirius', 'vega']:
                coord = SkyCoord.from_name(body_name.lower())
            else:
                coord = get_body(body_name.lower(), t, location)
            altaz = coord.transform_to(AltAz(obstime=t, location=location))
            altitudes.append(altaz.alt.deg)
        except:
            altitudes.append(0)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=[t.to_datetime(pytz.timezone("Asia/Kolkata")) for t in times],
        y=altitudes, mode='lines+markers', name=body_name.capitalize()
    ))
    fig.add_hline(y=10, line_dash="dash", line_color="red", annotation_text="Visibility Threshold")
    fig.update_layout(
        title=f"{days}-Day Visibility for {body_name.capitalize()}",
        xaxis_title="Time (IST)", yaxis_title="Altitude (degrees)",
        yaxis=dict(range=[-90, 90]), width=600, height=400,
        paper_bgcolor='black', plot_bgcolor='black', font=dict(color='white')
    )
    return fig

# Function to plot interactive sky map
def plot_sky_map(body_names, body_coords, observation_time, location):
    fig = go.Figure()
    altaz_frame = AltAz(obstime=observation_time, location=location)
    np.random.seed(42)
    star_az = np.random.uniform(0, 360, 50)
    star_alt = np.random.uniform(0, 90, 50)
    fig.add_trace(go.Scatter(
        x=star_az, y=star_alt, mode='markers', marker=dict(size=3, color='white', opacity=0.5),
        name='Background Stars', showlegend=False
    ))
    for body_name, body_coord in zip(body_names, body_coords):
        body_altaz = body_coord.transform_to(altaz_frame)
        constellation = constellations.get(body_name.lower(), None)
        label = f"{body_name.capitalize()} ({constellation})" if constellation else body_name.capitalize()
        magnitude = telescope_recommendations[body_name.lower()]['magnitude']
        fig.add_trace(go.Scatter(
            x=[body_altaz.az.deg], y=[body_altaz.alt.deg], mode='markers+text',
            marker=dict(size=20, color='red', opacity=0.8), text=[f"{label} (Mag: {magnitude})"],
            textposition='top center', name=body_name.capitalize()
        ))
    fig.update_layout(
        title=f"Sky Position at {observation_time.to_datetime(pytz.timezone('Asia/Kolkata'))}",
        xaxis=dict(title="Azimuth (degrees)", range=[0, 360]),
        yaxis=dict(title="Altitude (degrees)", range=[0, 90]),
        showlegend=True, width=600, height=500,
        paper_bgcolor='black', plot_bgcolor='black', font=dict(color='white')
    )
    return fig

# Function to generate PDF report (remove moon phase logic)
def generate_pdf(body_names, visibility_infos, location_name):
    filename = f"visibility_report.pdf"
    c = canvas.Canvas(filename, pagesize=letter)
    y = 750
    c.drawString(100, y, "Visibility Report")
    c.drawString(100, y-20, f"Location: {location_name}")
    c.drawString(100, y-40, f"Time (IST): {visibility_infos[0]['best_time'].to_datetime(pytz.timezone('Asia/Kolkata'))}")
    for body_name, visibility_info in zip(body_names, visibility_infos):
        y -= 60
        c.drawString(100, y, f"Object: {body_name.capitalize()}")
        c.drawString(100, y-20, f"Visible: {'Yes' if visibility_info['visible'] else 'No'}")
        c.drawString(100, y-40, f"Altitude: {visibility_info['altitude']:.2f} degrees")
        c.drawString(100, y-60, f"Azimuth: {visibility_info['azimuth']:.2f} degrees")
        c.drawString(100, y-80, f"Best Viewing Time: {visibility_info['best_time'].to_datetime(pytz.timezone('Asia/Kolkata'))}")
        c.drawString(100, y-100, f"Max Altitude: {visibility_info['max_altitude']:.2f} degrees")
        c.drawString(100, y-120, f"Telescope: {telescope_recommendations[body_name.lower()]['recommendation']}")
        c.drawString(100, y-140, f"Magnitude: {telescope_recommendations[body_name.lower()]['magnitude']}")
        y -= 140
    c.drawString(100, y, "Tip: Observe from a dark location away from city lights.")
    c.save()
    return filename

# Streamlit app with improved dark theme and better blending
st.set_page_config(page_title="Astronomy Planner", layout="wide", page_icon="🌌")
st.markdown("""
    <style>
    html, body, .main, .stApp {
        background-color: #181818 !important;
        color: #f0f0f0 !important;
    }
    .stButton>button, .stDownloadButton>button {
        background-color: #4CAF50 !important;
        color: white !important;
        border-radius: 8px !important;
        font-size: 18px !important;
        border: none !important;
        padding: 0.5em 1.5em !important;
        margin-bottom: 0.5em !important;
    }
    /* Remove background and border from widget containers */
    [data-testid="stForm"], [data-testid="stVerticalBlock"], [data-testid="stHorizontalBlock"], [data-testid="stBlock"], .st-cg, .st-ce, .st-cf {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
    }
    /* Remove background and border from expander */
    .stExpander {
        border-radius: 8px !important;
        background-color: #232323 !important;
        border: none !important;
        box-shadow: none !important;
    }
    /* Remove background and border from sidebar */
    .stSidebar {
        background-color: #181818 !important;
        border: none !important;
        box-shadow: none !important;
    }
    /* Remove background and border from selectbox, multiselect, slider, dateinput, timeinput */
    [data-baseweb="select"], .stSelectbox, .stMultiSelect, .stDateInput, .stTimeInput, .stSlider {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
    }
    /* Remove background and border from input fields */
    input, textarea {
        background-color: #232323 !important;
        color: #f0f0f0 !important;
        border-radius: 8px !important;
        border: none !important;
        box-shadow: none !important;
    }
    /* Remove background and border from widget labels */
    label, .css-1cpxqw2, .css-1n76uvr, .css-1y4p8pa {
        background: transparent !important;
        color: #f0f0f0 !important;
    }
    /* Remove background and border from markdown and containers */
    .stContainer, .stMarkdown, .stDataFrame, .stAlert {
        background-color: transparent !important;
        border: none !important;
        box-shadow: none !important;
    }
    .stInfo, .stSuccess, .stWarning, .stError {
        border-radius: 8px !important;
        padding: 0.5em 1em !important;
        margin-bottom: 0.5em !important;
        background-color: #232323 !important;
        color: #f0f0f0 !important;
        border: none !important;
    }
    .stSubheader, .stHeader, .stTitle {
        color: #f0f0f0 !important;
    }
    .stPlotlyChart {
        background-color: #181818 !important;
        border-radius: 8px !important;
        padding: 0.5em !important;
    }
    /* Remove weird boxes and borders */
    [data-testid="stVerticalBlock"] {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
    }
    </style>
    """, unsafe_allow_html=True)

# Sidebar branding and help
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/9/99/Starsinthesky.jpg", use_column_width=True)
    st.title("🌠 Astro Planner")
    st.markdown("**Plan your night sky observations in India!**")
    st.markdown("---")
    st.info("Select your city, celestial objects, and observation time. Get instant visibility, best times, and sky maps!", icon="ℹ️")
    st.markdown("---")
    st.markdown("Made with ❤️ using [Astropy](https://www.astropy.org/) and [Streamlit](https://streamlit.io/)")

st.title("🌌 Astronomy Observation Planner")
st.markdown("Check visibility of planets and bright stars from your location in India!")

# Help section with tooltips
with st.expander("ℹ️ How to Use This App"):
    st.write("""
        - **Select City**: Choose your observation location.
        - **Select Bodies**: Pick one or more celestial objects (planets, stars).
        - **Set Date/Time**: Specify when to observe (in IST).
        - **Timeline Days**: Choose how many days to plot visibility (1-3).
        - **Results**: View altitude (height above horizon), azimuth (compass direction), and best viewing time.
        - **Sky Map**: Interactive plot showing object positions (red dots) with star background.
        - **Timeline**: Shows when objects are above 10° (visible).
        - **PDF Report**: Download a summary for planning.
        - **Tip**: Observe from dark locations away from city lights.
    """)

st.markdown("---")

# User inputs in columns with icons and spacing
col1, col2 = st.columns(2)
with col1:
    st.subheader("📍 Location")
    location_name = st.selectbox("Select City", ["New Delhi", "Mumbai", "Bangalore"], index=0, help="Choose your observation city.")
    locations = {
        "New Delhi": (28.6139, 77.2090, 216),
        "Mumbai": (19.0760, 72.8777, 14),
        "Bangalore": (12.9716, 77.5946, 920)
    }
    lat, lon, height = locations[location_name]
    location = EarthLocation(lat=lat*u.deg, lon=lon*u.deg, height=height*u.m)
    observer = Observer(location=location, timezone="Asia/Kolkata")

with col2:
    st.subheader("🔭 Observation Details")
    body_names = st.multiselect("Select Celestial Bodies:", bodies, default=['jupiter'], help="Select one or more objects to track.")
    date_input = st.date_input("Observation Date", value=datetime.now(pytz.timezone("Asia/Kolkata")), help="Choose the date for observation.")
    # Allow user to select time in any timezone
    time_input = st.time_input("Observation Time", value=datetime.now().time(), help="Set the time for observation.")
    timezone_list = pytz.all_timezones
    selected_timezone = st.selectbox("Time Zone", options=timezone_list, index=timezone_list.index("Asia/Kolkata"), help="Select the time zone for your observation time.")
    timeline_days = st.slider("Visibility Timeline Days", 1, 3, 1, help="Select how many days to show in the visibility timeline.")

# Convert selected time and timezone to UTC for Astropy
user_tz = pytz.timezone(selected_timezone)
dt_user = user_tz.localize(datetime.combine(date_input, time_input))
dt_utc = dt_user.astimezone(pytz.utc)
observation_time = Time(dt_utc)

st.markdown("---")

# Check visibility
if st.button("✨ Check Visibility", use_container_width=True):
    visibility_infos = []
    body_coords = []
    errors = []

    for body_name in body_names:
        visibility_info, error, body_coord = check_visibility(body_name, observation_time, location)
        if error:
            errors.append(error)
        else:
            visibility_infos.append(visibility_info)
            body_coords.append(body_coord)

    if errors:
        for error in errors:
            st.error(error)
    else:
        st.subheader(f"🔎 Results for {', '.join([b.capitalize() for b in body_names])} in {location_name}")
        for body_name, visibility_info in zip(body_names, visibility_infos):
            with st.container():
                if visibility_info['visible']:
                    st.success(f"✅ {body_name.capitalize()} is visible from {location_name}!")
                else:
                    st.warning(f"⚠️ {body_name.capitalize()} is not visible (altitude below 10 degrees).")

                st.markdown(f"""
                - **Altitude**: `{visibility_info['altitude']:.2f}` degrees (height above horizon)
                - **Azimuth**: `{visibility_info['azimuth']:.2f}` degrees (compass direction)
                - **Time (IST)**: `{observation_time.to_datetime(pytz.timezone('Asia/Kolkata'))}`
                - **Best Viewing Time**: `{visibility_info['best_time'].to_datetime(pytz.timezone("Asia/Kolkata"))}` (Altitude: `{visibility_info['max_altitude']:.2f}` degrees)
                - **Telescope Recommendation**: {telescope_recommendations[body_name.lower()]['recommendation']}
                - **Magnitude**: `{telescope_recommendations[body_name.lower()]['magnitude']}` (lower is brighter)
                """)
                if body_name.lower() in constellations:
                    st.info(f"Constellation: **{constellations[body_name.lower()]}**", icon="🌟")
                st.info("Observation Tip: Choose a dark location away from city lights.", icon="💡")
                st.markdown("---")

        # Sky map
        st.subheader("🗺️ Sky Position")
        fig = plot_sky_map(body_names, body_coords, observation_time, location)
        st.plotly_chart(fig, use_container_width=True)

        # Visibility timeline
        for body_name in body_names:
            st.subheader(f"📈 Visibility Timeline for {body_name.capitalize()} ({timeline_days} Days)")
            fig = plot_visibility_timeline(body_name, observation_time, location, days=timeline_days)
            st.plotly_chart(fig, use_container_width=True)

        # PDF download
        st.subheader("📄 Download Report")
        pdf_file = generate_pdf(body_names, visibility_infos, location_name)
        with open(pdf_file, "rb") as f:
            st.download_button("Download PDF Report", f, file_name=pdf_file, use_container_width=True)
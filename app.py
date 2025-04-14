#---------------updated-------------------
from flask import Flask, request, jsonify, render_template, send_file
import psycopg2
from datetime import datetime
from flask_cors import CORS
import pandas as pd
import json
import sys
import math
import folium
from folium.plugins import MeasureControl
from geopy.distance import geodesic
from pyproj import Proj, transform
import re
import geopandas as gpd
from shapely.geometry import Polygon
from shapely.ops import nearest_points
from werkzeug.utils import secure_filename
from docx import Document
from docx.shared import Pt, Inches
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
import requests
import os
import logging
from docx2pdf import convert
import platform
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.text import WD_BREAK
import base64
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from docx.shared import RGBColor
import subprocess




app = Flask(__name__)
CORS(app) 

# Database Configuration    
DB_HOST = "iwmsgis.pmc.gov.in"
DB_NAME = "MOD"
DB_USER = "postgres"
DB_PASS = "pmc992101"
DB_PORT = "5432" 

def get_db_connection():
    """Establish connection to PostgreSQL"""
    return psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASS
    )


# Database connection For Update_csv api
# DB_NAME = "mod"
# DB_USER = "postgres"
# DB_PASSWORD = "Mojani@992101"
# DB_HOST = "info.dpzoning.com"  #info.dpzoning.com
# DB_PORT = "5432"  

# DB_HOST = "103.167.184.133"
# DB_NAME = "MOD"
# DB_USER = "postgres"
# DB_PASS = "geopulse123"
# DB_PORT = "5435" 




# Login Route
@app.route('/admin_login', methods=['POST'])
def admin_login():
    conn = None
    cursor = None
    try:
        data = request.json
        username = data.get("username")
        password = data.get("password")

        if not username or not password:
            return jsonify({"error": "Username and password are required"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # Fetch user from DB
        cursor.execute("SELECT password FROM admin_users WHERE username = %s", (username,))
        user = cursor.fetchone()

        if not user:
            return jsonify({"error": "Invalid credentials"}), 401

        stored_password = user[0]

        # Compare password directly (plain text comparison)
        if password == stored_password:
            return jsonify({"message": "Login successful"}), 200
        else:
            return jsonify({"error": "Invalid credentials"}), 401

    except psycopg2.Error as e:
        return jsonify({"error": str(e)}), 500
    finally:
        # Close cursor and connection only if they were initialized
        if cursor:
            cursor.close()
        if conn:
            conn.close()



@app.route('/save_user', methods=['POST'])
def save_user():
    """API endpoint to insert user data into PostgreSQL"""
    try:
        data = request.json  # Get JSON input from request
        
        # Extract data from JSON payload
        name = data.get("name")
        mobilenumber = data.get("mobilenumber")
        nameoncertificate = data.get("nameoncertificate")
        gstnumber = data.get("gstnumber") if data.get("gstnumber") else None
        pannumber = data.get("pannumber") if data.get("pannumber") else None
        siteaddress = data.get("siteaddress")
        gutnumber = data.get("gutnumber") if data.get("gutnumber") else None 
        district = data.get("district")
        taluka = data.get("taluka")
        village = data.get("village")
        pincode = data.get("pincode") if data.get("pincode") else None
        correspondanceadress = data.get("correspondanceadress")
        # outwardnumber = data.get("outwardnumber")
        date = datetime.now()  # Store current timestamp

        if not all([name, nameoncertificate, district, taluka, village]):
            return jsonify({"error": "Missing required fields"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # SQL Query to Insert Data
        insert_query = """
        INSERT INTO public.userdata 
        (name, mobilenumber, nameoncertificate, gstnumber, pannumber, gutnumber, 
         district, taluka, village, pincode, correspondanceadress, date, siteaddress) 
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,%s)
        RETURNING outwardnumber
        """
        cursor.execute(insert_query, (name, mobilenumber, nameoncertificate, gstnumber, pannumber, 
                                       gutnumber, district, taluka, village, pincode, 
                                      correspondanceadress, date, siteaddress))

        outwardnumber = cursor.fetchone()[0]
        conn.commit()

        cursor.close()
        conn.close()

        return jsonify({"message": "User data saved successfully!",
                        "outwardnumber": outwardnumber})

    except psycopg2.Error as e:
        return jsonify({"error": str(e)}), 500
    

@app.route('/get_user/<string:outwardnumber>', methods=['GET'])
def get_user_by_outwardnumber(outwardnumber):
    """API endpoint to retrieve a single user by outwardnumber"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Query with explicit column selection to avoid incorrect mapping
        query = """SELECT outwardnumber, name, mobilenumber, nameoncertificate, gstnumber, 
                   pannumber, gutnumber, district, taluka, village, 
                   pincode, correspondanceadress, date FROM userdata WHERE outwardnumber = %s"""
        cursor.execute(query, (outwardnumber,))
        user = cursor.fetchone()

        cursor.close()
        conn.close()

        if user:
            # Define column names explicitly in the correct order
            columns = ["outwardnumber", "name", "mobilenumber", "nameoncertificate", "gstnumber", 
                       "pannumber", "gutnumber", "district", "taluka", "village", 
                       "pincode", "correspondanceadress", "date"]
 
            user_data = dict(zip(columns, user))  # Convert tuple to dictionary

            return jsonify({"user": user_data}), 200
        else:
            return jsonify({"message": "User not found"}), 404

    except psycopg2.Error as e:
        return jsonify({"error": str(e)}), 500



# API for the Coordinates Data
# Define UTM projection for Zone 43N
utm_proj = Proj(proj="utm", zone=43, datum="WGS84", south=False)
wgs84_proj = Proj(proj="latlong", datum="WGS84")

# Function to convert decimal degrees to DMS
def decimal_to_dms(decimal_degree):
    degrees = int(decimal_degree)
    minutes = int((abs(decimal_degree) - abs(degrees)) * 60)
    seconds = (abs(decimal_degree) - abs(degrees) - minutes / 60) * 3600
    return degrees, minutes, seconds

# Function to calculate distance using the Haversine formula
def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0  # Radius of Earth in kilometers
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

# def calculate_distance(lat1, lon1, lat2, lon2):
#     # Create Point objects
#     point1 = Point(lon1, lat1)
#     point2 = Point(lon2, lat2)
    
#     # Create a GeoDataFrame
#     gdf = gpd.GeoDataFrame(geometry=[point1, point2], crs="EPSG:4326")
    
#     # Calculate the distance
#     distance = gdf.distance(gdf.shift()).iloc[1]  # Distance between the two points
#     return distance / 1000  # Convert meters to kilometers




def convert_to_wgs84(x, y):
    lon, lat = transform(utm_proj, wgs84_proj, x, y)
    return lat, lon


def calculate_boundaryDistance(coords):

    wmsUrlNDALohgaonBOundary = "http://iwmsgis.pmc.gov.in/geoserver/ows?service=WFS&version=2.0.0&request=GetFeature&typeName=MOD:Aviation_Boundary&outputFormat=application/json"
    geoserver_layer = gpd.read_file(wmsUrlNDALohgaonBOundary)
    geoserver_layer = geoserver_layer.to_crs(epsg=32643) 
    polygon_nda = geoserver_layer[geoserver_layer["Aviation_N"] == "NDA"]
    polygon_lohgaon = geoserver_layer[geoserver_layer["Aviation_N"] == "Lohagaon"]
    

    # Create polygon from input coordinates
    polygon_layout = gpd.GeoDataFrame(
        {'geometry': [Polygon(coords)]},
        crs="EPSG:32643"  # Original CRS for input coordinates (WGS84)
    ).geometry.iloc[0]
   
    polygon_nda = polygon_nda.to_crs(epsg=32643).geometry.iloc[0]
    polygon_lohgaon = polygon_lohgaon.to_crs(epsg=32643).geometry.iloc[0]

    # calculate nearest point
    nearest_nda_point = nearest_points(polygon_layout, polygon_nda)[1]
    nearest_lohgaon_point = nearest_points(polygon_layout, polygon_lohgaon)[1]
    polygon_layout_NDA = nearest_points(polygon_nda,polygon_layout)[1]
    polygon_layout_Lohagaon = nearest_points(polygon_lohgaon,polygon_layout)[1]

    nearest_nda_point_wgs84 = convert_to_wgs84(nearest_nda_point.x, nearest_nda_point.y)
    nearest_lohgaon_point_wgs84 = convert_to_wgs84(nearest_lohgaon_point.x, nearest_lohgaon_point.y)
    nearest_polygon_layout_NDA_wgs84 = convert_to_wgs84(polygon_layout_NDA.x,polygon_layout_NDA.y)
    nearest_polygon_layout_Lohagaon_wgs84 = convert_to_wgs84(polygon_layout_Lohagaon.x,polygon_layout_Lohagaon.y)

     # calculate distance point
    distance_meters_nda = polygon_nda.distance(polygon_layout)
    distance_meters_lohgaon = polygon_lohgaon.distance(polygon_layout)
    distance_km_nda = distance_meters_nda / 1000

    # print(distance_km_nda,"ooooooooooooooooooooooooooooooooooooooooooooooooooooo")
    distance_km_lohgaon = distance_meters_lohgaon / 1000
    
    # Return the distances in a dictionary
    mindistance = {
        "NDAboundaryMinDistance": distance_km_nda,
        "LohgaonBoundaryMinDistance": distance_km_lohgaon
    }
    nearest_points_list = [
        [nearest_nda_point_wgs84, nearest_polygon_layout_NDA_wgs84],  # (lat, lon) format for folium
        [nearest_lohgaon_point_wgs84, nearest_polygon_layout_Lohagaon_wgs84]
    ] 
    return mindistance,nearest_points_list

# Route to handle CSV file upload and processing

ALLOWED_EXTENSIONS = {'csv'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/process_csv', methods=['POST'])
def process_csv():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if file and allowed_file(file.filename):
        try:
            filename = secure_filename(file.filename)
            data = pd.read_csv(file,header=None)

            print("Columns in CSV:", data.columns)
            
            if data.shape[1] < 3:
                return jsonify({"error": "CSV file must contain at least 3 columns (P name, UTM x, UTM y)"}), 400

            decimal_degrees = []
            fpoints = []
            utmpoints = []
            fpointswithlabel = []
            reference_points = {
                "NDA": {"utm_x": 371129.923, "utm_y": 2042927.865},
                "loh": {"utm_x": 385999.526, "utm_y": 2055079.640},
            }

            # Create transformer object for coordinate conversion
            utm = Proj('epsg:32643')  # UTM zone 43N
            wgs84 = Proj('epsg:4326')  # WGS84

            for ref_name, ref_coords in reference_points.items():
                # Convert reference points from UTM to WGS84
                lon, lat = transform(utm, wgs84, ref_coords["utm_x"], ref_coords["utm_y"])
                reference_points[ref_name]["latitude"] = float(lat)
                reference_points[ref_name]["longitude"] = float(lon)

            # Iterate through data rows using itertuples()
            for row in data.itertuples():
                p_name = str(row[1])  # First column
                x = float(row[2])     # Second column (UTM X)
                y = float(row[3])     # Third column (UTM Y)
                elevation_val = float(row[4]) if len(row) > 4 else None  # Fourth column if exists

                # Convert from UTM to WGS84
                lon, lat = transform(utm, wgs84, x, y)
                lat = float(lat)
                lon = float(lon)
                
                lat_dms = decimal_to_dms(lat)
                lon_dms = decimal_to_dms(lon)
                utmpoint = (x, y)
                utmpoints.append(utmpoint)
                
                distances = {}
                for ref_name, ref_coords in reference_points.items():
                    distances[ref_name] =(haversine(lat, lon, ref_coords["latitude"], ref_coords["longitude"]))

                if isinstance(p_name, str) and re.match(r"^\s*[Pp]", p_name):
                    points = (float(lat), float(lon))
                    pointslabel = (float(lat), float(lon), str(p_name))
                    fpoints.append(points)
                    fpointswithlabel.append(pointslabel)

                decimal_degrees.append({
                    "P_name": p_name,
                    "latitude": lat,
                    "longitude": lon,
                    "Height": elevation_val,
                    "longitude_dms": f"{lat_dms[0]}°{lat_dms[1]}'{lat_dms[2]:.2f}\"",
                    "latitude_dms": f"{lon_dms[0]}°{lon_dms[1]}'{lon_dms[2]:.2f}\"",
                    "distances_to_reference_points_km": distances,
                })

            boundary_distances, nearest_points_list = calculate_boundaryDistance(utmpoints)
            
            # Convert boundary distances to float
            boundary_distances = {
                "NDAboundaryMinDistance": float(boundary_distances["NDAboundaryMinDistance"]),
                "LohgaonBoundaryMinDistance": float(boundary_distances["LohgaonBoundaryMinDistance"])
            }
            print(fpoints, fpointswithlabel, nearest_points_list)
            # map_sattelite(fpoints, fpointswithlabel, nearest_points_list)

            result = {
                "decimal_degrees": decimal_degrees,
                "boundary_distances": boundary_distances,
                "Height of plot from sea surface":"573.7 + 15.35 = 589.05 M",
                "Height of building from sea surface":"573.4 + 15.35 = 588.05 M"
            }

            return jsonify(result), 200

        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"Error details: {error_details}")
            return jsonify({"error": str(e), "details": error_details}), 500

    return jsonify({"error": "Invalid file format. Only CSV files are allowed."}), 400


# for save the coordinates and user details in database in mod and points  table

@app.route('/update_csv', methods=['POST'])
def update_csv():
    # Get outward number from the form data
    outwardnumber = request.form.get('outwardNumber')
    if not outwardnumber:
        return jsonify({"error": "Outward number is required"}), 400
    
    file = request.files.get('file')  
    if file and allowed_file(file.filename):
        try:
            # First, fetch user data using the outward number
            conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST, port=DB_PORT)
            cur = conn.cursor()
            
           
            user_query = """
                SELECT name, district, taluka, village, date, correspondanceadress, gutnumber
                FROM userdata WHERE outwardnumber = %s
            """
            cur.execute(user_query, (outwardnumber,))
            user_data = cur.fetchone()
            
            if not user_data:
                return jsonify({"error": f"No user found with outward number: {outwardnumber}"}), 404
                
            # Extract user data
            user_name, district, taluka, village, date, address, gut = user_data
            
            # CSV processing
            filename = secure_filename(file.filename)
            data = pd.read_csv(file,header=None)
            pointplotCoordiantes, pointbuildingCoordiantes = [], []
            plotCoordiantes, buildingCoordiantes = [], []

            print("Columns in CSV:", data.columns)
            print(f"Using outward number: {outwardnumber}")

            if data.shape[1] < 3:
                return jsonify({"error": "CSV file must contain at least 3 columns (P name, UTM x, UTM y)"}), 400

            
            reference_points = {
                "NDA": {"utm_x": 371129.923, "utm_y": 2042927.865},
                "loh": {"utm_x": 385999.526, "utm_y": 2055079.640},
            }

            # Create transformer object for coordinate conversion
            utm = Proj('epsg:32643')  
            wgs84 = Proj('epsg:4326') 

            
            for ref_name, ref_coords in reference_points.items():
                lon, lat = transform(utm, wgs84, ref_coords["utm_x"], ref_coords["utm_y"])
                reference_points[ref_name]["latitude"] = float(lat)
                reference_points[ref_name]["longitude"] = float(lon)

            print(reference_points,"ppppopopiouiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiii")
            for index, row in data.iterrows():
                labelName, utmXcoordiantes, utmYcoordinates, Zcoordinates = row[0], row[1], row[2], row[3]
                print(labelName, utmXcoordiantes, utmYcoordinates, Zcoordinates)
                pattern = r"^\s*[Pp]"

                
                lon, lat = transform(utm, wgs84, float(utmXcoordiantes), float(utmYcoordinates))
                lat, lon = float(lat), float(lon)
                
            
                nda_distance = haversine(lat, lon, reference_points["NDA"]["latitude"], reference_points["NDA"]["longitude"])
                print(nda_distance,"VVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVV")
                loh_distance = haversine(lat, lon, reference_points["loh"]["latitude"], reference_points["loh"]["longitude"])

                # Check if the label name starts with "P" or "p" (with optional spaces)
                if re.match(pattern, labelName):
                    print("------------------------------------------------------")
                    pointplotCoordiantes.append((labelName, utmXcoordiantes, utmYcoordinates, Zcoordinates, nda_distance, loh_distance))
                    plotCoordiantes.append((utmXcoordiantes, utmYcoordinates, Zcoordinates))
                else:
                    pointbuildingCoordiantes.append((labelName, utmXcoordiantes, utmYcoordinates, Zcoordinates, nda_distance, loh_distance))
                    buildingCoordiantes.append((utmXcoordiantes, utmYcoordinates, Zcoordinates))


            if plotCoordiantes and plotCoordiantes[0] != plotCoordiantes[-1]:
                plotCoordiantes.append(plotCoordiantes[0])

            if buildingCoordiantes and buildingCoordiantes[0] != buildingCoordiantes[-1]:
                buildingCoordiantes.append(buildingCoordiantes[0])

            # Create the polygon for plotCoordiantes
            plot_polygon_wkt = "POLYGONZ((" + ", ".join(f"{x} {y} {z}" for x, y, z in plotCoordiantes) + "))"
            
            # Create the polygon for buildingCoordiantes
            building_polygon_wkt = "POLYGONZ((" + ", ".join(f"{x} {y} {z}" for x, y, z in buildingCoordiantes) + "))"

            # Insert building coordinates if available
            if buildingCoordiantes:
                for name, x, y, z, nda_dist, loh_dist in pointbuildingCoordiantes:
                    point_wkt = f"POINTZ({x} {y} {z})"
                    # Use quoted column names to preserve case and include user data
                    cur.execute("""
                        INSERT INTO points (pointname, geom, outward, typeofsite, "Distance_from_NDA", "Distance_from_lohgaon",
                                            name, districtname, talukaname, villagename, date, address, gut, "Height_AMSL") 
                        VALUES (%s, ST_GeomFromText(%s, 32643), %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                    """, (name, point_wkt, outwardnumber, "building", nda_dist, loh_dist,
                        user_name, district, taluka, village, date, address, gut, z))

                # Insert the building polygon into the `mod` table
                    cur.execute("""
                        INSERT INTO mod (
                            geom, pointname, outward, typeofsite, "Distance_from_NDA", "Distance_from_lohgaon",
                            name, districtname, talukaname, villagename, date, address, gut, "Height_AMSL"
                        )
                        VALUES (
                            ST_GeomFromText(%s, 32643), %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s, %s, %s
                        );
                    """, (
                        building_polygon_wkt, name, outwardnumber, "building", nda_dist, loh_dist,
                        user_name, district, taluka, village, date, address, gut, z
                    ))

            # Insert plot coordinates 
            if plotCoordiantes:
                for name, x, y, z, nda_dist, loh_dist in pointplotCoordiantes:
                    point_wkt = f"POINTZ({x} {y} {z})"
                    
                    cur.execute("""
                        INSERT INTO points (pointname, geom, outward, typeofsite, "Distance_from_NDA", "Distance_from_lohgaon",
                                            name, districtname, talukaname, villagename, date, address, gut, "Height_AMSL") 
                        VALUES (%s, ST_GeomFromText(%s, 32643), %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                    """, (name, point_wkt, outwardnumber, "plot", nda_dist, loh_dist,
                        user_name, district, taluka, village, date, address, gut, z))

                    cur.execute("""
                        INSERT INTO mod (
                            geom, pointname, outward, typeofsite, "Distance_from_NDA", "Distance_from_lohgaon",
                            name, districtname, talukaname, villagename, date, address, gut, "Height_AMSL"
                        )
                        VALUES (
                            ST_GeomFromText(%s, 32643), %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s, %s, %s
                        );
                    """, (
                        plot_polygon_wkt, name, outwardnumber, "plot", nda_dist, loh_dist,
                        user_name, district, taluka, village, date, address, gut, z
                    ))

           
            conn.commit()

            cur.close()
            conn.close()

            return jsonify({
                "message": "CSV data processed and inserted successfully!",
                "distances_added": True,
                "user_data_added": True
            })

        except Exception as e:
            print(f"Error occurred: {e}")
            import traceback
            error_details = traceback.format_exc()
            print(f"Error details: {error_details}")
            return jsonify({"error": f"An error occurred: {str(e)}", "details": error_details}), 500

    else:
        return jsonify({"error": "No file or invalid file format."}), 400




@app.route('/get_aviation_data/<string:outwardnumber>', methods=['GET'])
def get_aviation_data_and_geometry(outwardnumber):
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Step 1: Get the latest geometry for this outward number
        cur.execute("""
            SELECT geom FROM mod 
            WHERE outward = %s
            ORDER BY id DESC
        """, (outwardnumber,))

        result = cur.fetchone()

        if not result:
            return jsonify({"error": "No geometry found for this outward number"}), 404

        geometry = result[0]

        # Step 2: Query aviation data that intersects with the geometry
        cur.execute("""
            SELECT zone, elevation
            FROM "Aviation_data"
            WHERE ST_Intersects(geom, ST_Transform(ST_SetSRID(%s::geometry, 32643), 4326))
        """, (geometry,))

        aviation_data = cur.fetchall() 
    
        # Convert list of tuples to list of dictionaries
        aviation_data_list = [{"zone": row[0], "elevation": row[1]} for row in aviation_data] 
        print(aviation_data, aviation_data_list)
        # Add debug logging
        print(f"Found aviation data: {aviation_data_list}")

        cur.close()
        conn.close()

        return jsonify({
            "geometry": geometry,
            "aviation_data": aviation_data_list  
        }), 200

    except Exception as e:
        import traceback
        print(f"Error in get_aviation_data_and_geometry: {e}")
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500



# Set up logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def set_table_borders(table):
    tbl = table._element
    tbl_pr = tbl.find(qn("w:tblPr"))
    
    # Ensure tblPr exists
    if tbl_pr is None:
        tbl_pr = OxmlElement("w:tblPr")
        tbl.insert(0, tbl_pr)
    
    # Set the table borders
    tbl_borders = OxmlElement("w:tblBorders")
    for border_name in ["top", "left", "bottom", "right", "insideH", "insideV"]:
        border = OxmlElement(f"w:{border_name}")
        border.set(qn("w:val"), "single")
        border.set(qn("w:sz"), "5")  # Border size
        border.set(qn("w:space"), "0")  # Border space
        border.set(qn("w:color"), "000000")  # Border color
        tbl_borders.append(border)
    tbl_pr.append(tbl_borders)

    # Prevent table rows from splitting across pages
    cant_split = OxmlElement("w:cantSplit")
    cant_split.set(qn("w:val"), "true")
    tbl_pr.append(cant_split)
    
    # Keep the tblLook element too
    tbl_look = OxmlElement("w:tblLook")
    tbl_look.set(qn("w:val"), "04A0")
    tbl_pr.append(tbl_look)

def set_paragraph_format(paragraph):
    paragraph_format = paragraph.paragraph_format
    paragraph_format.line_spacing = 1.5  # Set line spacing
    paragraph_format.space_after = Pt(6)  # Space after paragraph
    paragraph_format.space_before = Pt(6)  # Space before paragraph

def set_cell_alignment(cell, vertical="center", horizontal="center", is_second_column=False):
    """
    Set cell alignment with special handling for second column
    vertical: "top", "center", or "bottom"
    horizontal: "left", "center", or "right"
    is_second_column: True if this is the second column (will be left-aligned)
    """
    try:
        # Get the cell's XML element
        tc = cell._element
        
        # Ensure the cell has a <w:tcPr> element
        tc_pr = tc.find(qn("w:tcPr"))
        if tc_pr is None:
            tc_pr = OxmlElement("w:tcPr")
            tc.insert(0, tc_pr)
        
        # Vertical alignment (applies to all cells)
        v_align = OxmlElement("w:vAlign")
        v_align.set(qn("w:val"), vertical)
        tc_pr.append(v_align)

        # Horizontal alignment - special handling for second column
        align = WD_ALIGN_PARAGRAPH.LEFT if is_second_column else {
            "left": WD_ALIGN_PARAGRAPH.LEFT,
            "center": WD_ALIGN_PARAGRAPH.CENTER,
            "right": WD_ALIGN_PARAGRAPH.RIGHT,
        }.get(horizontal, WD_ALIGN_PARAGRAPH.CENTER)

        for paragraph in cell.paragraphs:
            paragraph.alignment = align
            
    except Exception as e:
        print(f"Warning: Could not set cell alignment: {e}")


def adjust_table_cell_alignments(table):
    try:
        for row in table.rows:
            for i, cell in enumerate(row.cells):
                # Second column (index 1) gets left alignment, others get center
                set_cell_alignment(cell, 
                                 vertical="center",
                                 horizontal="center",
                                 is_second_column=(i == 1))
    except Exception as e:
        print(f"Warning: Could not adjust table alignments: {e}")
        
def prevent_row_split(row):
    """Prevent a table row from splitting across pages"""
    tr = row._tr
    trPr = tr.get_or_add_trPr()
    cantSplit = OxmlElement('w:cantSplit')
    cantSplit.set(qn('w:val'), "true")
    trPr.append(cantSplit)



# Pdf Document generation code 

@app.route('/generate_doc', methods=['POST'])
def generate_document():
    try:
        # Validate request data
        if not request.is_json:
            return jsonify({
                "success": False,
                "error": "Request must be JSON"
            }), 400

        # Get outward number and file data from request
        data = request.json
        if not data:
            return jsonify({
                "success": False,
                "error": "No JSON data received"
            }), 400

        outward_number = data.get('outwardNumber')
        # outward_number = '1069'
        coordinates_data = data.get('fileData')
        job_number = data.get('jobNumber', '') 
        # map_screenshots = data.get('mapScreenshots', {})

        logger.info(f"Received job number: {job_number}")
        logger.info(f"Job number type: {type(job_number)}")
        

        if not outward_number or not coordinates_data:
            return jsonify({
                "success": False,
                "error": "Missing required fields: outwardNumber or fileData"
            }), 400

        logger.info(f"Processing outward number: {outward_number}")
       
        logger.info(f"Coordinates data: {coordinates_data}")
        
        # logger.info(f"Received map screenshots: {True if map_screenshots else False}")

        # Fetch user data from API
        try:
            user_response = requests.get(f'http://127.0.0.1:5000/get_user/{outward_number}')
            user_response.raise_for_status()
            user_data = user_response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching user data: {str(e)}")
            return jsonify({
                "success": False,
                "error": f"Failed to fetch user data: {str(e)}"
            }), 500

        # Verify template file exists
        template_path = "MOD 3.docx"
        if not os.path.exists(template_path):
            return jsonify({
                "success": False,
                "error": "Template file not found"
            }), 500

        # Create document
        try:
            docmonarch = Document(template_path)

            if job_number:
                logger.info(f"Adding header with job number: {job_number}")
                
                for section_idx, section in enumerate(docmonarch.sections):
                    logger.info(f"Processing section {section_idx + 1}")
                    
                    # Disable Word's different first page / odd/even page headers
                    section.different_first_page_header_footer = False
                    
                    # Choose headers to update: main, first page, even page
                    headers_to_update = [
                        section.header,
                        section.first_page_header,
                        section.even_page_header
                    ]
                    
                    for header_type, header in zip(['Default', 'First Page', 'Even Page'], headers_to_update):
                        header_text_modified = False

                        for para in header.paragraphs:
                            if "MONARCH" in para.text and "PMC" in para.text:
                                if re.search(r'\d+', para.text):
                                    modified_text = re.sub(r'(\d+)', job_number, para.text)
                                else:
                                    modified_text = f"{para.text.strip()} AAI/AN_{job_number}"

                                para.clear()
                                run = para.add_run(modified_text)
                                run.font.name = 'Arial'
                                run.font.size = Pt(12)
                                run.font.bold = False

                                header_text_modified = True
                                logger.info(f"Updated {header_type} header in section {section_idx + 1}")
                                break
        except Exception as e:
            logger.error(f"Error creating document: {str(e)}")
            return jsonify({
                "success": False,
                "error": f"Failed to create document: {str(e)}"
            }), 500

        # Update user information
        try:
            name_on_certificate = user_data.get("user", {}).get("nameoncertificate", "")
            corresponding_Address = user_data.get("user", {}).get("correspondanceadress", "")
            gut_number = user_data.get("user", {}).get("gutnumber", "")
            Survey_no = f"Survey No:{gut_number}"
            
            village = user_data.get("user", {}).get("village", "")
            taluka = user_data.get("user", {}).get("taluka", "")
            district = user_data.get("user", {}).get("district", "")
            pincode = user_data.get("user", {}).get("pincode", "")
            site_adress = f"Village: {village} Taluka: {taluka} District: {district} Pincode: {pincode}"
            # Update date in all headers - Get current date in the desired format (DD/MM/YYYY)
            
            import datetime
            
            

            current_date = datetime.datetime.now().strftime("%d/%m/%Y")
            logger.info(f"Current Date: {current_date}")

            # Loop through all sections and update date in header
            for section_idx, section in enumerate(docmonarch.sections):
                section.different_first_page_header_footer = False  # ensure uniform headers
                headers = {
                    "Default": section.header,
                    "First Page": section.first_page_header,
                    "Even Page": section.even_page_header
                }

                for header_name, header in headers.items():
                    date_found = False

                    for para in header.paragraphs:
                        if re.search(r"\b\d{2}/\d{2}/\d{4}\b", para.text):
                            old_date = re.search(r"\b\d{2}/\d{2}/\d{4}\b", para.text).group()
                            para.text = para.text.replace(old_date, current_date)
                            para.alignment = WD_ALIGN_PARAGRAPH.RIGHT

                            run = para.runs[0] if para.runs else para.add_run()
                            run.font.name = 'Arial'
                            run.font.size = Pt(12)

                            logger.info(f"Updated {header_name} header date in section {section_idx + 1}")
                            date_found = True
                            break

                    if not date_found:
                        logger.info(f"Adding date to {header_name} header in section {section_idx + 1}")
                        new_para = header.add_paragraph(f"Date - {current_date}")
                        new_para.alignment = WD_ALIGN_PARAGRAPH.RIGHT

                        run = new_para.runs[0]
                        run.font.name = 'Arial'
                        run.font.size = Pt(12)
                        
            # Update paragraphs
            if len(docmonarch.paragraphs) > 6:
                paragraph = docmonarch.paragraphs[6]
                paragraph.clear()
                run = paragraph.add_run(name_on_certificate)
                run.font.name = 'Arial'
                run.font.size = Pt(12)
                run.font.bold = True
                set_paragraph_format(paragraph)

            if len(docmonarch.paragraphs) > 8:
                paragraph = docmonarch.paragraphs[9]
                paragraph.clear()
                run = paragraph.add_run(corresponding_Address)
                run.font.name = 'Arial'
                run.font.size = Pt(12)
                run.font.bold = True
                set_paragraph_format(paragraph)
                paragraph.paragraph_format.left_indent = Inches(0.2)

            if len(docmonarch.paragraphs) > 15:
                paragraph = docmonarch.paragraphs[7]  
                paragraph.clear()
                run = paragraph.add_run(Survey_no)
                run.font.name = 'Arial'
                run.font.size = Pt(12)
                run.font.bold = True
            
            if len(docmonarch.paragraphs) > 15:
                paragraph = docmonarch.paragraphs[13]  
                paragraph.clear()
                run = paragraph.add_run(Survey_no)
                run.font.name = 'Arial'
                run.font.size = Pt(12)
                # run.font.bold = True

            if len(docmonarch.paragraphs) > 17:
                paragraph = docmonarch.paragraphs[8]  
                paragraph.clear()
                run = paragraph.add_run(site_adress)
                run.font.name = 'Arial'
                run.font.size = Pt(12)
                run.font.bold = True

            if len(docmonarch.paragraphs) > 17:
                paragraph = docmonarch.paragraphs[15]  
                paragraph.clear()
                run = paragraph.add_run(site_adress)
                run.font.name = 'Arial'
                run.font.size = Pt(12)
                # run.font.bold = True

            # Update table with coordinates data
            if docmonarch.tables:
                if len(docmonarch.tables) > 1:
                    # Get references to both tables
                    table = docmonarch.tables[0]  # First table (for entries starting with P/p)
                    table1 = docmonarch.tables[1]  # Second table (for other entries)
                    row_index = 3  # Row index where data starts

                    # Clear existing data rows from both tables
                    for _ in range(len(table.rows) - row_index):
                        table._element.remove(table.rows[row_index]._element)

                    for _ in range(len(table1.rows) - row_index):
                        table1._element.remove(table1.rows[row_index]._element)

                    # Initialize separate counters for each table
                    serial_number_table = 1  # Counter for first table
                    serial_number_table1 = 1  # Counter for second table (will start from 1)

                    for entry in coordinates_data:
                        # Check if point name starts with P/p
                        if re.match(r"^\s*[Pp]", entry['P_name']):
                            # Process for FIRST table
                            new_row = table.add_row()
                            prevent_row_split(new_row)

                            for i, cell in enumerate(new_row.cells):
                                # Clear existing content
                                for paragraph in cell.paragraphs:
                                    paragraph._element.getparent().remove(paragraph._element)
                                
                                # Add new paragraph with controlled formatting
                                paragraph = cell.add_paragraph()
                                paragraph_format = paragraph.paragraph_format
                                paragraph_format.space_before = Pt(0)
                                paragraph_format.space_after = Pt(0)
                                paragraph_format.line_spacing = 1.0

                                # Add content based on column index
                                if i == 0:
                                    run = paragraph.add_run(str(serial_number_table))
                                elif i == 1:
                                    run = paragraph.add_run(f"Point No. {entry['P_name']} :- Differential GPS Observation taken on Ground IN STATIC mode")
                                elif i == 2:
                                    run = paragraph.add_run(entry['latitude_dms'])
                                elif i == 3:
                                    run = paragraph.add_run(entry['longitude_dms'])
                                elif i == 4:
                                    height_value = entry.get('Height', "N/A")
                                    run = paragraph.add_run(str(height_value) if height_value is not None else "N/A")
                                elif i == 5:
                                    if 'distances_to_reference_points_km' in entry and entry['distances_to_reference_points_km'] and 'NDA' in entry['distances_to_reference_points_km']:
                                        nda_distance = entry['distances_to_reference_points_km']['NDA']
                                        run = paragraph.add_run(f"{nda_distance:.2f} KM" if nda_distance is not None else "N/A")
                                    else:
                                        run = paragraph.add_run("N/A")
                                    
                                elif i == 6:
                                    if 'distances_to_reference_points_km' in entry and entry['distances_to_reference_points_km'] and 'loh' in entry['distances_to_reference_points_km']:
                                        loh_distance = entry['distances_to_reference_points_km']['loh']
                                        run = paragraph.add_run(f"{loh_distance:.2f} KM" if loh_distance is not None else "N/A")
                                    else:
                                        run = paragraph.add_run("N/A")
                                    
                                elif i == 7:
                                    nda_boundary = "N/A"
                                    lohgaon_boundary = "N/A"
                                    
                                    if 'boundary_distances' in entry and entry['boundary_distances']:
                                        if 'NDAboundaryMinDistance' in entry['boundary_distances'] and entry['boundary_distances']['NDAboundaryMinDistance'] is not None:
                                            nda_boundary = f"{entry['boundary_distances']['NDAboundaryMinDistance']:.2f} KM"
                                            
                                        if 'LohgaonBoundaryMinDistance' in entry['boundary_distances'] and entry['boundary_distances']['LohgaonBoundaryMinDistance'] is not None:
                                            lohgaon_boundary = f"{entry['boundary_distances']['LohgaonBoundaryMinDistance']:.2f} KM"
                                    
                                    run = paragraph.add_run(f"NDA Min Distance: {nda_boundary}\nLohgaon Min Distance: {lohgaon_boundary}")
                                
                                run.font.name = "Arial"
                                run.font.size = Pt(12)

                            serial_number_table += 1  # Increment only first table's counter

                        else:
                            # Process for SECOND table
                            new_row = table1.add_row()
                            prevent_row_split(new_row)

                            for i, cell in enumerate(new_row.cells):
                                # Clear existing content
                                for paragraph in cell.paragraphs:
                                    paragraph._element.getparent().remove(paragraph._element)
                                
                                # Add new paragraph with controlled formatting
                                paragraph = cell.add_paragraph()
                                paragraph_format = paragraph.paragraph_format
                                paragraph_format.space_before = Pt(0)
                                paragraph_format.space_after = Pt(0)
                                paragraph_format.line_spacing = 1.0

                                # Add content based on column index
                                if i == 0:
                                    run = paragraph.add_run(str(serial_number_table1))  # Starts from 1
                                elif i == 1:
                                    run = paragraph.add_run(f"Point No. {entry['P_name']} :- Differential GPS Observation taken on Ground IN STATIC mode")
                                elif i == 2:
                                    run = paragraph.add_run(entry['latitude_dms'])
                                elif i == 3:
                                    run = paragraph.add_run(entry['longitude_dms'])
                                elif i == 4:
                                    height_value = entry.get('Height', "N/A")
                                    run = paragraph.add_run(str(height_value) if height_value is not None else "N/A")
                                elif i == 5:
                                    if 'distances_to_reference_points_km' in entry and entry['distances_to_reference_points_km'] and 'NDA' in entry['distances_to_reference_points_km']:
                                        nda_distance = entry['distances_to_reference_points_km']['NDA']
                                        run = paragraph.add_run(f"{nda_distance:.2f} KM" if nda_distance is not None else "N/A")
                                    else:
                                        run = paragraph.add_run("N/A")
                                    
                                elif i == 6:
                                    if 'distances_to_reference_points_km' in entry and entry['distances_to_reference_points_km'] and 'loh' in entry['distances_to_reference_points_km']:
                                        loh_distance = entry['distances_to_reference_points_km']['loh']
                                        run = paragraph.add_run(f"{loh_distance:.2f} KM" if loh_distance is not None else "N/A")
                                    else:
                                        run = paragraph.add_run("N/A")
                                    
                                elif i == 7:
                                    nda_boundary = "N/A"
                                    lohgaon_boundary = "N/A"
                                    
                                    if 'boundary_distances' in entry and entry['boundary_distances']:
                                        if 'NDAboundaryMinDistance' in entry['boundary_distances'] and entry['boundary_distances']['NDAboundaryMinDistance'] is not None:
                                            nda_boundary = f"{entry['boundary_distances']['NDAboundaryMinDistance']:.2f} KM"
                                            
                                        if 'LohgaonBoundaryMinDistance' in entry['boundary_distances'] and entry['boundary_distances']['LohgaonBoundaryMinDistance'] is not None:
                                            lohgaon_boundary = f"{entry['boundary_distances']['LohgaonBoundaryMinDistance']:.2f} KM"
                                    
                                    run = paragraph.add_run(f"NDA Min Distance: {nda_boundary}\nLohgaon Min Distance: {lohgaon_boundary}")

                                # Formatting
                                run.font.name = "Arial"
                                run.font.size = Pt(12)

                            serial_number_table1 += 1  # Increment only second table's counter

                        # Apply cell alignment for all new rows
                        for i, cell in enumerate(new_row.cells):
                            set_cell_alignment(cell, 
                                            vertical="center",
                                            horizontal="center",
                                            is_second_column=(i == 1))
                    # Final table formatting
                    set_table_borders(table)
                    set_table_borders(table1)
                    adjust_table_cell_alignments(table)
                    adjust_table_cell_alignments(table1)

                    paragraph = docmonarch.add_paragraph()
                    run = paragraph.add_run()
                    run.add_break(WD_BREAK.PAGE)
                    
                    paragraph_after_table1 = docmonarch.add_paragraph()
                    p1 = paragraph_after_table1._element
                    br1 = OxmlElement('w:br')
                    br1.set(qn('w:type'), 'page')
                    p1.append(br1)
                    table._element.addnext(p1)  # Insert after first table

                    # ====== 2. Page Break After Second Table (table1) ======
                    paragraph_after_table2 = docmonarch.add_paragraph()
                    p2 = paragraph_after_table2._element
                    br2 = OxmlElement('w:br')
                    br2.set(qn('w:type'), 'page')
                    p2.append(br2)
                    table1._element.addnext(p2)


                    def add_maps_to_document(document, maps_folder="D:\\Monarch_Mod\\backend\\static"):
                        
                        # Get the map files
                        map_files = [
                            os.path.join(maps_folder, "Map1.png"),
                            os.path.join(maps_folder, "Map2.png"),
                            os.path.join(maps_folder, "Map3.png"),
                            os.path.join(maps_folder, "Map4.png")
                        ]
                        
                        # Add each map with proper sizing
                        for i, map_file in enumerate(map_files, 1):
                            if os.path.exists(map_file):
                                # Add page break before each map (except the first one)
                                if i > 1:
                                    page_break = document.add_paragraph()
                                    run = page_break.add_run()
                                    run.add_break(WD_BREAK.PAGE)
                                
                                # Add top margin space
                                for _ in range(3):  
                                    spacing_para = document.add_paragraph()
                                    spacing_para.paragraph_format.space_after = Pt(12)
                                
                                
                                try:
                                    document.add_picture(map_file, width=Inches(6))  # Adjust width as needed
                                    last_paragraph = document.paragraphs[-1]
                                    last_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                                    
                                except Exception as e:
                                    logger.error(f"Error adding map {i}: {str(e)}")
                                    # Add error message in the document
                                    error_para = document.add_paragraph(f"Error loading Map {i}: {str(e)}")
                                    error_para.runs[0].font.color.rgb = RGBColor(255, 0, 0)  # Red color for error
                            else:
                                logger.warning(f"Map file not found: {map_file}")
                                warning_para = document.add_paragraph(f"Map {i} file not found at: {map_file}")
                                warning_para.runs[0].font.color.rgb = RGBColor(255, 165, 0)  # Orange color for warning

                    
            
            output_dir = "generated_docs"

            # Create directory if it doesn't exist
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            # Save document
            output_docx = 'modified_output.docx'
            output_pdf = 'modified_output.pdf'

            # Create unique filenames based on outward number
            outward_docx = os.path.join(output_dir, f'{outward_number}.docx')
            outward_pdf = os.path.join(output_dir, f'{outward_number}.pdf')
            
            docmonarch.save(output_docx)  

            import shutil
            shutil.copy(output_docx, outward_docx)   
            
            docmonarch = None  # Release the document

            system = platform.system()
            
            if system == "Windows":
                # Windows: Use docx2pdf
                import pythoncom
                from docx2pdf import convert
                
                pythoncom.CoInitialize()  # Initialize COM for Windows
                convert(output_docx, output_pdf)
                convert(outward_docx, outward_pdf)
                pythoncom.CoUninitialize()  # Clean up COM
            
            else:  # Linux/macOS
                # Find the correct LibreOffice binary
                libreoffice_commands = ["libreoffice", "soffice"]
                command = next((cmd for cmd in libreoffice_commands if subprocess.run([cmd, "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False).returncode == 0), None)
                
                if not command:
                    logger.error("Neither LibreOffice nor soffice found. Please install LibreOffice.")
                    return jsonify({
                        "success": False,
                        "error": "LibreOffice not found. Please install LibreOffice."
                    }), 500

                # Convert standard output
                process_standard = subprocess.run(
                    [command, "--headless", "--convert-to", "pdf", "--outdir", os.path.dirname(output_pdf), output_docx],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False
                )

                if process_standard.returncode != 0:
                    logger.error(f"Error converting standard output with LibreOffice: {process_standard.stderr.decode()}")
                    return jsonify({
                        "success": False,
                        "error": f"Standard PDF conversion failed: {process_standard.stderr.decode()}"
                    }), 500
                
                # Convert outward-specific file
                process_outward = subprocess.run(
                    [command, "--headless", "--convert-to", "pdf", "--outdir", os.path.dirname(outward_pdf), outward_docx],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False
                )

                if process_outward.returncode != 0:
                    logger.error(f"Error converting outward-specific output with LibreOffice: {process_outward.stderr.decode()}")
                    return jsonify({
                        "success": False,
                        "error": f"Outward-specific PDF conversion failed: {process_outward.stderr.decode()}"
                    }), 500

            # Check if PDFs were created
            if not os.path.exists(output_pdf) or not os.path.exists(outward_pdf):
                raise Exception("One or more PDF files were not created")

            return jsonify({
                "success": True,
                "message": "Document generated successfully",
                "docPath": os.path.abspath(output_docx),
                "pdfPath": os.path.abspath(output_pdf),
                "outwardDocPath": os.path.abspath(outward_docx),
                "outwardPdfPath": os.path.abspath(outward_pdf)
            })

        except Exception as e:
            logger.error(f"Error during document generation: {str(e)}")
            return jsonify({
                "success": False,
                "error": f"Error during document generation: {str(e)}"
            }), 500

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }), 500



@app.route('/get-doc')
def get_document():
    try:
        return send_file(
            'modified_output.docx',
            as_attachment=True,
            download_name='modified_output.docx'
        )
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# API for a PDF viewer

@app.route('/view-pdf')
def view_pdf():
    try:
        return send_file(
            'modified_output.pdf',
            mimetype='application/pdf'
        )
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/download-pdf/<outward_number>')
def download_pdf(outward_number):
    try:
        return send_file(
            'modified_output.pdf',
            as_attachment=True,
            download_name=f'{outward_number}.pdf',
            mimetype='application/pdf'
        )
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

#---------------------------Api for a pdf file preview--------------------
@app.route('/api/pdf/<filename>')
def serve_pdf(filename):

    pdf_path = os.path.join('D:/Monarch_Mod/backend/generated_docs', f'{filename}.pdf')
    
    if os.path.exists(pdf_path):
        return send_file(pdf_path, mimetype='application/pdf')
    else:
        return jsonify({"error": "PDF not found"}), 404



@app.route('/Modpdf-download/<application_number>', methods=['GET'])
def downloadpdf(application_number):
    try:
        pdf_filename = f"{application_number}.pdf"
        pdf_path = os.path.join('D:/Monarch_Mod/backend/generated_docs', pdf_filename)

        if os.path.exists(pdf_path):
            return send_file(
                pdf_path,
                as_attachment=True,
                download_name=f"MOD_{application_number}.pdf",  # Correct naming
                mimetype='application/pdf'
            )
        else:
            return jsonify({"error": "PDF not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500




@app.route('/run-bat', methods=['GET'])
def run_bat_file():
    try:
        subprocess.Popen([r"D:\Monarch_Mod\backend\run_converter.bat"], shell=True)
        return jsonify({"success": True, "message": "BAT file started"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
        app.run(debug=True, host='0.0.0.0', port=5000)
    







# paragraph = docmonarch.add_paragraph()
                    
                    # # 2. Get the XML element of the paragraph
                    # p = paragraph._element
                    
                    # # 3. Create a page break element
                    # br = OxmlElement('w:br')
                    # br.set(qn('w:type'), 'page')  # Set break type to PAGE
                    
                    # # 4. Add the break to the paragraph
                    # p.append(br)
                    
                    # # 5. Insert this paragraph AFTER the first table
                    # table._element.addnext(p)
                    # # ====== END PAGE BREAK ======






#  if map_screenshots:
#                 # Add a page break
#                 docmonarch.add_paragraph().add_run()         #----.add_break(WD_BREAK.PAGE)
                
#                 # Add a title for the maps section
#                 # maps_title = docmonarch.add_paragraph("Site Location Maps")
#                 # maps_title.style = docmonarch.styles['Heading 1']
                
#                 # Process and add map screenshots
#                 for map_name, screenshot_data in map_screenshots.items():
#                     if screenshot_data and screenshot_data.startswith('data:image'):
#                         # Extract the base64 data
#                         img_data = screenshot_data.split(',')[1]
                        
#                         # Create temporary file for the image
#                         img_filename = f"temp_{map_name}.png"
                        
#                         # Save base64 data as image
#                         with open(img_filename, "wb") as img_file:
#                             img_file.write(base64.b64decode(img_data))
                        
#                         # # Add a title for each map
#                         # map_title = ""
#                         # if map_name == "map1":
#                         #     map_title = "NDA Map View"
#                         # elif map_name == "map2":
#                         #     map_title = "Lohagaon Map View"
#                         # elif map_name == "map3":
#                         #     map_title = "Toposheet Map View"
                        
#                         # Add the map title
#                         # map_para = docmonarch.add_paragraph(map_title)
#                         # map_para.style = docmonarch.styles['Heading 2']

#                         spacing_paragraph = docmonarch.add_paragraph()
#                         spacing_paragraph.add_run("\n")  # Adding a new line for extra spacing

                        
#                         # Add the map image
#                         paragraph = docmonarch.add_paragraph()
#                         run = paragraph.add_run()
#                         run.add_picture(img_filename, width=Inches(6))
                        
#                         paragraph.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER

#                         paragraph.paragraph_format.space_before = Pt(10)
#                         # Remove temporary file
#                         os.remove(img_filename)
                        
#                         # Add some space after the image
#                         docmonarch.add_paragraph()











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
from docx.shared import Pt
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
import requests
# from flask import Flask, request, jsonify, send_file
# from flask_cors import CORS
import os
# import comtypes.client
import logging
import pythoncom  
# import pypandoc
from docx2pdf import convert


app = Flask(__name__)

CORS(app) 

# Database Configuration    
DB_HOST = "iwmsgis.pmc.gov.in"
DB_NAME = "MOD"
DB_USER = "postgres"
DB_PASS = "pmc992101"

def get_db_connection():
    """Establish connection to PostgreSQL"""
    return psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASS
    )

# Login Route


@app.route('/admin_login', methods=['POST'])
def admin_login():
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
        cursor.close()
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
        siteadress = data.get("siteadress")
        gutnumber = data.get("gutnumber") 
        district = data.get("district")
        taluka = data.get("taluka")
        village = data.get("village")
        pincode = data.get("pincode") if data.get("pincode") else None
        correspondanceadress = data.get("correspondanceadress")
        # outwardnumber = data.get("outwardnumber")
        date = datetime.now()  # Store current timestamp

        if not all([name, nameoncertificate, gutnumber, district, taluka, village]):
            return jsonify({"error": "Missing required fields"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # SQL Query to Insert Data
        insert_query = """
        INSERT INTO public.userdata 
        (name, mobilenumber, nameoncertificate, gstnumber, pannumber, siteadress, gutnumber, 
         district, taluka, village, pincode, correspondanceadress,  date) 
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING outwardnumber
        """
        cursor.execute(insert_query, (name, mobilenumber, nameoncertificate, gstnumber, pannumber, 
                                      siteadress, gutnumber, district, taluka, village, pincode, 
                                      correspondanceadress,  date))

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
                   pannumber, siteadress, gutnumber, district, taluka, village, 
                   pincode, correspondanceadress, date FROM userdata WHERE outwardnumber = %s"""
        cursor.execute(query, (outwardnumber,))
        user = cursor.fetchone()

        cursor.close()
        conn.close()

        if user:
            # Define column names explicitly in the correct order
            columns = ["outwardnumber", "name", "mobilenumber", "nameoncertificate", "gstnumber", 
                       "pannumber", "siteadress", "gutnumber", "district", "taluka", "village", 
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



def map_sattelite(coords, points_with_labels,nearest_points_list, output_map="map.html"):
    """
    Create a folium map with a polygon, labeled points, and an export-to-PDF button on Google Satellite imagery.
    
    Args:
        coords (list): List of (latitude, longitude) tuples for the polygon.
        points_with_labels (list): List of tuples [(lat, lon, label), ...] for points with labels.
        output_map (str): Path to save the output HTML map.
    
    Returns:
        str: Path to the saved HTML map.
    """
   
    m = folium.Map(
        location=[coords[0][0], coords[0][1]],
        zoom_start=10,
        tiles=None  # Disable default tiles
    )
    m.add_child(MeasureControl())

    folium.TileLayer(
        tiles="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
        attr="OpenStreetMap",
        name="OpenStreetMap",
        overlay=False,
        control=True  # Allow users to toggle this layer
    ).add_to(m)
    
    # Add Google Satellite Tiles
    folium.TileLayer(
        tiles="https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}",
        attr="Google Satellite",
        name="Google Satellite",
        overlay=False,
        control=True
    ).add_to(m) 
    
    polygon = folium.Polygon(
        locations=coords,  # List of (latitude, longitude) tuples
        color="red",
        weight=3,
        fill=True,
        fill_color="cyan",
        fill_opacity=0.4,
        popup="Polygon Area"
    ).add_to(m)

    Aviation_boundary = folium.WmsTileLayer(
        url="https://iwmsgis.pmc.gov.in/geoserver/wms?",
        name="Aviation Boundaries",
        layers="MOD:Aviation_Boundary",
        fmt="image/png",
        transparent=True,
        overlay=True,
        control=True
    ).add_to(m)

    
    Aviation_zone =folium.WmsTileLayer(
        url="https://iwmsgis.pmc.gov.in/geoserver/wms?",
        name="Aviation Zone",
        layers="MOD:Aviation_data",
        fmt="image/png",
        transparent=True,
        overlay=True,
        control=True
    ).add_to(m)

   
    for point_pair in nearest_points_list:
    # Each point_pair is a tuple of two points
        point1 = point_pair[0]  
        point2 = point_pair[1] 

        # Calculate the distance between the two points using geodesic (this calculates the great-circle distance)
        line_length = geodesic(point1, point2).kilometers  # Distance in kilometers

        mid_point_lat = (point1[0] + point2[0]) / 2
        mid_point_lon = (point1[1] + point2[1]) / 2
        popup_message = f"Distance: {line_length:.2f} km"  # Format the distance to two decimal places

        # Add the PolyLine to the map with the popup showing the distance
        folium.PolyLine(
            locations=[point1, point2],  # Coordinates of the points to draw a line between
            color="yellow",  # Color for the line
            weight=1,  # Line thickness
        ).add_to(m).add_child(folium.Popup(popup_message))

        folium.Marker(
        location=[mid_point_lat, mid_point_lon],  # Midpoint of the line
        icon=folium.DivIcon(
            icon_size=(150, 36),  # Size of the label
            icon_anchor=(7, 20),  # Position of the label
            html=f'<div style="font-size: 16px; font-weight: bold; color: yellow;">{line_length:.2f} km</div>'  # Label style
        ),
    ).add_to(m)


    for lat, lon, label in points_with_labels:
        folium.CircleMarker(
            location=(lat, lon),
            radius=3,  # Small dot size
            color="blue",
            fill=True,
            fill_color="blue",
            fill_opacity=0.5,
            popup=f"{label}",  # Add label as a popup
        ).add_to(m)

        folium.Marker(
        location=[lat, lon], 
        icon=folium.DivIcon(
            icon_size=(150, 36),  # Size of the label
            icon_anchor=(7, 20),  # Position of the label
            html=f'<div style="font-size: 12px; font-weight: bold; color: yellow;">{label}</div>'  # Label style
        ),
    ).add_to(m)

    m.fit_bounds(polygon.get_bounds()) 
    # Add a custom button to export to PDF
    pdf_button = """
      <script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js" integrity="sha512-BNaRQnYJYiPSqHHDb58B0yaPfCu+Wgds8Gp/gU33kqBtgNS4tSPHuGibyoeqMV/TJlSKda6FXzoEyYGjTe+vXA==" crossorigin="anonymous" referrerpolicy="no-referrer"></script>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js"></script>
                <div style="position: fixed; 
                            bottom: 50px; left: 50px; width: 150px; height: 30px; 
                            z-index: 1000;">
                    <button onclick="exportToPDF()" style="width: 150px; height: 30px; background-color: #4CAF50; color: white; border: none; border-radius: 5px;">
                        Export to PDF
                    </button>
                </div>
            
                <script>
                function exportToPDF() {
    try {
        const { jsPDF } = window.jspdf;
        const doc = new jsPDF();

        // Select the map container dynamically
        const mapContainer = document.querySelector('.folium-map');

        const originalScrollX = window.scrollX;
        const originalScrollY = window.scrollY;

        html2canvas(mapContainer, {
            scale: 2, // Scale for high resolution
            useCORS: true, // Handle cross-origin images
            scrollX: originalScrollX, // Maintain original horizontal scroll position
            scrollY: originalScrollY, // Maintain original vertical scroll position
        }).then(function (canvas) {
            const imgData = canvas.toDataURL('image/png');
            const pdfWidth = 180; // Maximum width for PDF
            const aspectRatio = canvas.width / canvas.height;
            const imgHeight = pdfWidth / aspectRatio; // Maintain aspect ratio

            // Center the map image in the PDF
            const pageWidth = doc.internal.pageSize.getWidth();
            const centerX = (pageWidth - pdfWidth) / 2;

            // Add the image to the PDF
            doc.addImage(imgData, 'PNG', centerX, 10, pdfWidth, imgHeight);

            // Save the generated PDF
            const fileName = `map_export.pdf`;
            doc.save(fileName);
        });
    } catch (error) {
        console.error('Error generating PDF:', error);
        alert('Failed to generate PDF. Check console for details.');
    }
}


    </script>
    """
    m.get_root().html.add_child(folium.Element(pdf_button))

    folium.LayerControl().add_to(m)
    m.save(output_map)
    return output_map

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
            data = pd.read_csv(file)

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
                    distances[ref_name] = float(haversine(lat, lon, ref_coords["latitude"], ref_coords["longitude"]))

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
                    "latitude_dms": f"{lat_dms[0]}°{lat_dms[1]}'{lat_dms[2]:.4f}\"",
                    "longitude_dms": f"{lon_dms[0]}°{lon_dms[1]}'{lon_dms[2]:.4f}\"",
                    "distances_to_reference_points_km": distances,
                })

            boundary_distances, nearest_points_list = calculate_boundaryDistance(utmpoints)
            
            # Convert boundary distances to float
            boundary_distances = {
                "NDAboundaryMinDistance": float(boundary_distances["NDAboundaryMinDistance"]),
                "LohgaonBoundaryMinDistance": float(boundary_distances["LohgaonBoundaryMinDistance"])
            }

            map_sattelite(fpoints, fpointswithlabel, nearest_points_list)

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






# Set up logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def set_table_borders(table):
    tbl = table._element
    tbl_pr = tbl.find(qn("w:tblPr"))
    if tbl_pr is None:
        tbl_pr = OxmlElement("w:tblPr")
        tbl.insert(0, tbl_pr)

    tbl_borders = OxmlElement("w:tblBorders")
    for border_name in ["top", "left", "bottom", "right", "insideH", "insideV"]:
        border = OxmlElement(f"w:{border_name}")
        border.set(qn("w:val"), "single")
        border.set(qn("w:sz"), "5")
        border.set(qn("w:space"), "0")
        border.set(qn("w:color"), "000000")
        tbl_borders.append(border)
    tbl_pr.append(tbl_borders)

def set_paragraph_format(paragraph):
    paragraph_format = paragraph.paragraph_format
    paragraph_format.line_spacing = 1.5
    paragraph_format.space_after = Pt(6)
    paragraph_format.space_before = Pt(6)

@app.route('/generate-doc', methods=['POST'])
def generate_document():
    try:
        # Initialize COM for this thread
        pythoncom.CoInitialize()
        
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
            coordinates_data = data.get('fileData')

            if not outward_number or not coordinates_data:
                return jsonify({
                    "success": False,
                    "error": "Missing required fields: outwardNumber or fileData"
                }), 400

            logger.info(f"Processing outward number: {outward_number}")
            logger.info(f"Coordinates data: {coordinates_data}")

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
            template_path = "MOD 2.docx"
            if not os.path.exists(template_path):
                return jsonify({
                    "success": False,
                    "error": "Template file not found"
                }), 500

            # Create document
            try:
                docmonarch = Document(template_path)
            except Exception as e:
                logger.error(f"Error creating document: {str(e)}")
                return jsonify({
                    "success": False,
                    "error": f"Failed to create document: {str(e)}"
                }), 500

            # Update user information
            try:
                name_on_certificate = user_data["user"]["nameoncertificate"]
                corresponding_Address = user_data["user"]["correspondanceadress"]
                Survey_no = "Survey No." + user_data["user"]["gutnumber"]
                site_adress = f"Village :{user_data['user']['village']} Taluka :{user_data['user']['taluka']} District :{user_data['user']['district']}"

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
                    paragraph = docmonarch.paragraphs[8]
                    paragraph.clear()
                    run = paragraph.add_run(corresponding_Address)
                    run.font.name = 'Arial'
                    run.font.size = Pt(12)
                    run.font.bold = True
                    set_paragraph_format(paragraph)

                if len(docmonarch.paragraphs) > 15:
                    paragraph = docmonarch.paragraphs[7]
                    paragraph.clear()
                    run = paragraph.add_run(Survey_no)
                    run.font.name = 'Arial'
                    run.font.size = Pt(12)
                    run.font.bold = True

                if len(docmonarch.paragraphs) > 17:
                    paragraph = docmonarch.paragraphs[7]
                    paragraph.clear()
                    run = paragraph.add_run(site_adress)
                    run.font.name = 'Arial'
                    run.font.size = Pt(12)
                    run.font.bold = True

                # Update table with coordinates data
                if docmonarch.tables:
                    if len(docmonarch.tables) > 1:
                        for table in docmonarch.tables[1:]:
                            table._element.getparent().remove(table._element)
                    
                    table = docmonarch.tables[0]
                    row_index = 3

                    # Remove existing data rows
                    for _ in range(len(table.rows) - row_index):
                        table._element.remove(table.rows[row_index]._element)

                    serial_number = 1
                    for entry in coordinates_data:
                        new_row = table.add_row()
                        new_row.cells[0].text = str(serial_number)
        
                        # Check that all other cells are populated correctly
                        for i, cell in enumerate(new_row.cells):
                            if i == 1:
                               cell.text = f"Point No. {entry['P_name']} :- Differential GPS Observation taken on Ground IN STATIC mode"
                            elif i == 2:
                               cell.text = entry['latitude_dms']
                            elif i == 3:
                               cell.text = entry['longitude_dms']
                            elif i == 4:
                                cell.text = str(entry['Height'])
                            elif i == 5 and 'distances_to_reference_points_km' in entry:
                                cell.text = f"{entry['distances_to_reference_points_km']['NDA']:.2f} KM"
                            elif i == 6 and 'distances_to_reference_points_km' in entry:
                                cell.text = f"{entry['distances_to_reference_points_km']['loh']:.2f} KM"
                            elif i == 7 and 'boundary_distances' in entry:
                                cell.text = (
                                   f"NDA Min Distance: {entry['boundary_distances']['NDAboundaryMinDistance']:.2f} KM\n"
                                   f"Lohgaon Min Distance: {entry['boundary_distances']['LohgaonBoundaryMinDistance']:.2f} KM"
                                )

                            # Set the font and formatting for each cell
                            for para in cell.paragraphs:
                                for run in para.runs:
                                    run.font.name = "Arial"
                                    run.font.size = Pt(12)

                        serial_number += 1

                    set_table_borders(table)

                # Save document
                output_docx = 'modified_output.docx'
                output_pdf = 'modified_output.pdf'
                docmonarch.save(output_docx)
                
                # Convert to PDF using docx2pdf
                try:
                    # Convert DOCX to PDF
                    convert(output_docx, output_pdf)

                    if not os.path.exists(output_pdf):
                        raise Exception("PDF file was not created")

                    return jsonify({
                        "success": True,
                        "message": "Document generated successfully",
                        "docPath": os.path.abspath(output_docx),
                        "pdfPath": os.path.abspath(output_pdf)
                    })

                except Exception as e:
                    logger.error(f"Error converting to PDF: {str(e)}")
                    return jsonify({
                        "success": False,
                        "error": f"Error converting to PDF: {str(e)}"
                    }), 500

            except Exception as e:
                logger.error(f"Error during document generation: {str(e)}")
                return jsonify({
                    "success": False,
                    "error": f"Error during document generation: {str(e)}"
                }), 500

        finally:
            # Always uninitialize COM, even if an error occurred
            pythoncom.CoUninitialize()

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


if __name__ == '__main__':
        app.run(debug=True, host='0.0.0.0', port=5000)















# @app.route('/generate-doc', methods=['POST'])
# def generate_document():
#     pythoncom.CoInitialize()  # Initialize COM
#     try:
#         # Validate request data
#         if not request.is_json:
#             return jsonify({
#                 "success": False,
#                 "error": "Request must be JSON"
#             }), 400

#         # Get outward number and file data from request
#         data = request.json
#         if not data:
#             return jsonify({
#                 "success": False,
#                 "error": "No JSON data received"
#             }), 400

#         outward_number = data.get('outwardNumber')
#         coordinates_data = data.get('fileData')

#         if not outward_number or not coordinates_data:
#             return jsonify({
#                 "success": False,
#                 "error": "Missing required fields: outwardNumber or fileData"
#             }), 400

#         logger.info(f"Processing outward number: {outward_number}")
#         logger.info(f"Coordinates data: {coordinates_data}")

#         # Fetch user data from API
#         try:
#             user_response = requests.get(f'http://127.0.0.1:5000/get_user/{outward_number}')
#             user_response.raise_for_status()
#             user_data = user_response.json()
#         except requests.exceptions.RequestException as e:
#             logger.error(f"Error fetching user data: {str(e)}")
#             return jsonify({
#                 "success": False,
#                 "error": f"Failed to fetch user data: {str(e)}"
#             }), 500

#         # Verify template file exists
#         template_path = "MOD 2.docx"
#         if not os.path.exists(template_path):
#             return jsonify({
#                 "success": False,
#                 "error": "Template file not found"
#             }), 500

#         # Create document
#         try:
#             docmonarch = Document(template_path)
#         except Exception as e:
#             logger.error(f"Error creating document: {str(e)}")
#             return jsonify({
#                 "success": False,
#                 "error": f"Failed to create document: {str(e)}"
#             }), 500

#         # Update user information
#         try:
#             name_on_certificate = user_data["user"]["nameoncertificate"]
#             corresponding_Address = user_data["user"]["correspondanceadress"]
#             Survey_no = "Survey No." + user_data["user"]["gutnumber"]
#             site_adress = f"Village :{user_data['user']['village']} Taluka :{user_data['user']['taluka']} District :{user_data['user']['district']}"

#             # Update paragraphs
#             if len(docmonarch.paragraphs) > 6:
#                 paragraph = docmonarch.paragraphs[6]
#                 paragraph.clear()
#                 run = paragraph.add_run(name_on_certificate)
#                 run.font.name = 'Arial'
#                 run.font.size = Pt(12)
#                 run.font.bold = True
#                 set_paragraph_format(paragraph)

#             if len(docmonarch.paragraphs) > 8:
#                 paragraph = docmonarch.paragraphs[8]
#                 paragraph.clear()
#                 run = paragraph.add_run(corresponding_Address)
#                 run.font.name = 'Arial'
#                 run.font.size = Pt(12)
#                 run.font.bold = True
#                 set_paragraph_format(paragraph)

#             if len(docmonarch.paragraphs) > 15:
#                 paragraph = docmonarch.paragraphs[7]
#                 paragraph.clear()
#                 run = paragraph.add_run(Survey_no)
#                 run.font.name = 'Arial'
#                 run.font.size = Pt(12)
#                 run.font.bold = True

#             if len(docmonarch.paragraphs) > 17:
#                 paragraph = docmonarch.paragraphs[7]
#                 paragraph.clear()
#                 run = paragraph.add_run(site_adress)
#                 run.font.name = 'Arial'
#                 run.font.size = Pt(12)
#                 run.font.bold = True

#             # Update table with coordinates data
#             if docmonarch.tables:
#                 if len(docmonarch.tables) > 1:
#                     for table in docmonarch.tables[1:]:
#                         table._element.getparent().remove(table._element)
                
#                 table = docmonarch.tables[0]
#                 row_index = 3

#                 # Remove existing data rows
#                 for _ in range(len(table.rows) - row_index):
#                     table._element.remove(table.rows[row_index]._element)

                
#                 serial_number = 1
#                 for entry in coordinates_data:
#                     new_row = table.add_row()
#                     new_row.cells[0].text = str(serial_number)
    
#     # Check that all other cells are populated correctly
#                     for i, cell in enumerate(new_row.cells):
#                         if i == 1:
#                            cell.text = f"Point No. {entry['P_name']} :- Differential GPS Observation taken on Ground IN STATIC mode"
#                         elif i == 2:
#                            cell.text = entry['latitude_dms']
#                         elif i == 3:
#                            cell.text = entry['longitude_dms']
#                         elif i == 4:
#                             cell.text = str(entry['Height'])
#                         elif i == 5 and 'distances_to_reference_points_km' in entry:
#                             cell.text = f"{entry['distances_to_reference_points_km']['NDA']:.2f} KM"
#                         elif i == 6 and 'distances_to_reference_points_km' in entry:
#                             cell.text = f"{entry['distances_to_reference_points_km']['loh']:.2f} KM"
#                         elif i == 7 and 'boundary_distances' in entry:
#                             cell.text = (
#                                f"NDA Min Distance: {entry['boundary_distances']['NDAboundaryMinDistance']:.2f} KM\n"
#                                f"Lohgaon Min Distance: {entry['boundary_distances']['LohgaonBoundaryMinDistance']:.2f} KM"
#                             )

#         # Set the font and formatting for each cell
#                         for para in cell.paragraphs:
#                             for run in para.runs:
#                                 run.font.name = "Arial"
#                                 run.font.size = Pt(12)

#                     serial_number += 1

                
#                 set_table_borders(table)

#             # Save document
#             output_docx = 'modified_output.docx'
#             output_pdf = 'modified_output.pdf'
#             docmonarch.save(output_docx)
            
#             # Convert to PDF
#             word = comtypes.client.CreateObject("Word.Application")
#             word.Visible = False
            
#             doc = word.Documents.Open(os.path.abspath(output_docx))
#             doc.SaveAs(os.path.abspath(output_pdf), FileFormat=17)
#             doc.Close()
#             word.Quit()

#             return jsonify({
#                 "success": True,
#                 "message": "Document generated successfully",
#                 "docPath": os.path.abspath(output_docx)
#             })

#         except Exception as e:
#             logger.error(f"Error during document generation: {str(e)}")
#             return jsonify({
#                 "success": False,
#                 "error": f"Error during document generation: {str(e)}"
#             }), 500
#         finally:
#             pythoncom.CoUninitialize()

#     except Exception as e:
#         logger.error(f"Unexpected error: {str(e)}")
#         return jsonify({
#             "success": False,
#             "error": f"Unexpected error: {str(e)}"
#         }), 500
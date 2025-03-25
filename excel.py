
from flask import Flask, request, jsonify, render_template, send_file
import psycopg2
from datetime import datetime
from flask_cors import CORS
import pandas as pd
import json
import sys
from werkzeug.utils import secure_filename
import re


import psycopg2

# Database connection details
DB_NAME = "mod"
DB_USER = "postgres"
DB_PASSWORD = "Mojani@992101"
DB_HOST = "info.dpzoning.com"  # Change if using a remote server
DB_PORT = "5432"  


app = Flask(__name__)
CORS(app) 


ALLOWED_EXTENSIONS = {'csv'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/update_csv', methods=['POST'])
def update_csv():
    file = request.files.get('file')  
    if file and allowed_file(file.filename):
        try:
            filename = secure_filename(file.filename)
            data = pd.read_csv(file)
            pointplotCoordiantes, pointbuildingCoordiantes = [], []
            plotCoordiantes, buildingCoordiantes = [], []

            print("Columns in CSV:", data.columns)

            if data.shape[1] < 3:
                return jsonify({"error": "CSV file must contain at least 3 columns (P name, UTM x, UTM y)"}), 400

            # Loop through the rows of the CSV
            for index, row in data.iterrows():
                labelName, utmXcoordiantes, utmYcoordinates, Zcoordinates = row[0], row[1], row[2], row[3]
                pattern = r"^\s*[Pp]"

                # Check if the label name starts with "P" or "p" (with optional spaces)
                if re.match(pattern, labelName):
                    print("------------------------------------------------------")
                    pointplotCoordiantes.append((labelName, utmXcoordiantes, utmYcoordinates, Zcoordinates))
                    plotCoordiantes.append((utmXcoordiantes, utmYcoordinates, Zcoordinates))
                else:
                    pointbuildingCoordiantes.append((labelName, utmXcoordiantes, utmYcoordinates, Zcoordinates))
                    buildingCoordiantes.append((utmXcoordiantes, utmYcoordinates, Zcoordinates))

            # Ensure the polygon is closed by appending the first point to the end
            if plotCoordiantes and plotCoordiantes[0] != plotCoordiantes[-1]:
                plotCoordiantes.append(plotCoordiantes[0])

            if buildingCoordiantes and buildingCoordiantes[0] != buildingCoordiantes[-1]:
                buildingCoordiantes.append(buildingCoordiantes[0])

            # Create the polygon for plotCoordiantes
            plot_polygon_wkt = "POLYGONZ((" + ", ".join(f"{x} {y} {z}" for x, y, z in plotCoordiantes) + "))"
            
            # Create the polygon for buildingCoordiantes
            building_polygon_wkt = "POLYGONZ((" + ", ".join(f"{x} {y} {z}" for x, y, z in buildingCoordiantes) + "))"

            # Connect to the database
            conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT)
            cur = conn.cursor()

            # Insert building coordinates if available
            if buildingCoordiantes:
                for name, x, y, z in pointbuildingCoordiantes:
                    outwardnumber = '112345'  # Assuming outwardnumber is the numeric part of the name (e.g., B1 -> 1)
                    point_wkt = f"POINTZ({x} {y} {z})"
                    cur.execute("INSERT INTO points (pointname, geom, outward, typeofsite) VALUES (%s, ST_GeomFromText(%s, 32643), %s, %s);", 
                                (name, point_wkt, outwardnumber, "building"))

                # Insert the building polygon into the `mod` table
                cur.execute("INSERT INTO mod (geom, outward, typeofsite) VALUES (ST_GeomFromText(%s, 32643), %s, %s);", 
                            (building_polygon_wkt, outwardnumber, "building"))

            # Insert plot coordinates if available
            if plotCoordiantes:
                for name, x, y, z in pointplotCoordiantes:
                    outwardnumber = '112345'  # Assuming outwardnumber is the numeric part of the name (e.g., P1 -> 1)
                    point_wkt = f"POINTZ({x} {y} {z})"
                    cur.execute("INSERT INTO points (pointname, geom, outward, typeofsite) VALUES (%s, ST_GeomFromText(%s, 32643), %s, %s);", 
                                (name, point_wkt, outwardnumber, "plot"))

                # Insert the plot polygon into the `mod` table
                cur.execute("INSERT INTO mod (geom, outward, typeofsite) VALUES (ST_GeomFromText(%s, 32643), %s, %s);", 
                            (plot_polygon_wkt, outwardnumber, "plot"))

            # Commit the changes
            conn.commit()

            # Close the connection
            cur.close()
            conn.close()

            return jsonify({"message": "CSV data processed and inserted successfully!"})

        except Exception as e:
            print(f"Error occurred: {e}")
            return jsonify({"error": f"An error occurred: {str(e)}"}), 500

    else:
        return jsonify({"error": "No file or invalid file format."}), 400



if __name__ == '__main__':
        app.run(debug=True, host='0.0.0.0', port=5000)





# @app.route('/update_csv', methods=['POST'])
# def update_csv():
#     # Get outward number from the form data
#     outwardnumber = request.form.get('outwardNumber')
#     if not outwardnumber:
#         return jsonify({"error": "Outward number is required"}), 400
    
#     file = request.files.get('file')  
#     if file and allowed_file(file.filename):
#         try:
#             filename = secure_filename(file.filename)
#             data = pd.read_csv(file)
#             pointplotCoordiantes, pointbuildingCoordiantes = [], []
#             plotCoordiantes, buildingCoordiantes = [], []

#             print("Columns in CSV:", data.columns)
#             print(f"Using outward number: {outwardnumber}")

#             if data.shape[1] < 3:
#                 return jsonify({"error": "CSV file must contain at least 3 columns (P name, UTM x, UTM y)"}), 400

#             # Loop through the rows of the CSV
#             for index, row in data.iterrows():
#                 labelName, utmXcoordiantes, utmYcoordinates, Zcoordinates = row[0], row[1], row[2], row[3]
#                 pattern = r"^\s*[Pp]"

#                 # Check if the label name starts with "P" or "p" (with optional spaces)
#                 if re.match(pattern, labelName):
#                     print("------------------------------------------------------")
#                     pointplotCoordiantes.append((labelName, utmXcoordiantes, utmYcoordinates, Zcoordinates))
#                     plotCoordiantes.append((utmXcoordiantes, utmYcoordinates, Zcoordinates))
#                 else:
#                     pointbuildingCoordiantes.append((labelName, utmXcoordiantes, utmYcoordinates, Zcoordinates))
#                     buildingCoordiantes.append((utmXcoordiantes, utmYcoordinates, Zcoordinates))

#             # Ensure the polygon is closed by appending the first point to the end
#             if plotCoordiantes and plotCoordiantes[0] != plotCoordiantes[-1]:
#                 plotCoordiantes.append(plotCoordiantes[0])

#             if buildingCoordiantes and buildingCoordiantes[0] != buildingCoordiantes[-1]:
#                 buildingCoordiantes.append(buildingCoordiantes[0])

#             # Create the polygon for plotCoordiantes
#             plot_polygon_wkt = "POLYGONZ((" + ", ".join(f"{x} {y} {z}" for x, y, z in plotCoordiantes) + "))"
            
#             # Create the polygon for buildingCoordiantes
#             building_polygon_wkt = "POLYGONZ((" + ", ".join(f"{x} {y} {z}" for x, y, z in buildingCoordiantes) + "))"

#             # Connect to the database using provided credentials
#             conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST, port=DB_PORT)
#             cur = conn.cursor()

#             # Insert building coordinates if available
#             if buildingCoordiantes:
#                 for name, x, y, z in pointbuildingCoordiantes:
#                     point_wkt = f"POINTZ({x} {y} {z})"
#                     cur.execute("INSERT INTO points (pointname, geom, outward, typeofsite) VALUES (%s, ST_GeomFromText(%s, 32643), %s, %s);", 
#                                 (name, point_wkt, outwardnumber, "building"))

#                 # Insert the building polygon into the `mod` table
#                 cur.execute("INSERT INTO mod (geom, outward, typeofsite) VALUES (ST_GeomFromText(%s, 32643), %s, %s);", 
#                             (building_polygon_wkt, outwardnumber, "building"))

#             # Insert plot coordinates if available
#             if plotCoordiantes:
#                 for name, x, y, z in pointplotCoordiantes:
#                     point_wkt = f"POINTZ({x} {y} {z})"
#                     cur.execute("INSERT INTO points (pointname, geom, outward, typeofsite) VALUES (%s, ST_GeomFromText(%s, 32643), %s, %s);", 
#                                 (name, point_wkt, outwardnumber, "plot"))

#                 # Insert the plot polygon into the `mod` table
#                 cur.execute("INSERT INTO mod (geom, outward, typeofsite) VALUES (ST_GeomFromText(%s, 32643), %s, %s);", 
#                             (plot_polygon_wkt, outwardnumber, "plot"))

#             # Commit the changes
#             conn.commit()

#             # Close the connection
#             cur.close()
#             conn.close()

#             return jsonify({"message": "CSV data processed and inserted successfully!"})

#         except Exception as e:
#             print(f"Error occurred: {e}")
#             return jsonify({"error": f"An error occurred: {str(e)}"}), 500

#     else:
#         return jsonify({"error": "No file or invalid file format."}), 400

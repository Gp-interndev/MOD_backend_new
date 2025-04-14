from docx import Document

template_path = r"D:\Monarch_Mod\backend\MOD 3.docx"
docmonarch = Document(template_path)

# Ensure the document has at least two tables
if len(docmonarch.tables) > 1:
    # Assign tables before modifying or iterating
    table = docmonarch.tables[0]  # First table
    table1 = docmonarch.tables[1]  # Second table

    # Print all tables
    for table_index, table_obj in enumerate(docmonarch.tables):
        print(f"Table {table_index + 1}:\n")
        for row in table_obj.rows:
            row_text = [cell.text.strip() for cell in row.cells]
            print("\t".join(row_text))  # Print row text in a tab-separated format
        print("\n" + "=" * 50 + "\n")  # Separator between tables

    # Now you can safely use `table` and `table1` separately
    print("Table 1 and Table 2 have been assigned successfully.")

else:
    print("Document does not contain enough tables.")




#--------------------------------------old Document generation pdf code---------------------------

# def convert_to_pdf(input_docx, output_pdf):
#     """
#     Convert DOCX to PDF using `docx2pdf` on Windows and LibreOffice on Linux.
#     """
#     system = platform.system()

#     if system == "Windows":
#         try:
#             import pythoncom
#             from docx2pdf import convert
            
#             pythoncom.CoInitialize()  # Initialize COM for Windows
#             convert(input_docx, output_pdf)
#             pythoncom.CoUninitialize()  # Clean up COM
            
#             return True
#         except Exception as e:
#             logger.error(f"Error using docx2pdf on Windows: {str(e)}")
#             return False

#     else:  # Linux/macOS
#         try:
#             # Find the correct LibreOffice binary
#             libreoffice_commands = ["libreoffice", "soffice"]
#             command = next((cmd for cmd in libreoffice_commands if subprocess.run([cmd, "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False).returncode == 0), None)
            
#             if not command:
#                 logger.error("Neither LibreOffice nor soffice found. Please install LibreOffice.")
#                 return False

#             output_dir = os.path.dirname(output_pdf) or "."

#             process = subprocess.run(
#                 [command, "--headless", "--convert-to", "pdf", "--outdir", output_dir, input_docx],
#                 stdout=subprocess.PIPE,
#                 stderr=subprocess.PIPE,
#                 check=False
#             )

#             if process.returncode != 0:
#                 logger.error(f"Error converting with LibreOffice: {process.stderr.decode()}")
#                 return False

#             # Rename output file if necessary
#             input_basename = os.path.splitext(os.path.basename(input_docx))[0]
#             libreoffice_output = os.path.join(output_dir, f"{input_basename}.pdf")

#             if libreoffice_output != output_pdf:
#                 os.rename(libreoffice_output, output_pdf)

#             return True

#         except Exception as e:
#             logger.error(f"Error converting to PDF on Linux/Mac: {str(e)}")
#             return False




# @app.route('/generate_doc', methods=['POST'])
# def generate_document():
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
#         # outward_number = '1069'
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
#             user_response = requests.get(f'http://103.167.184.133:5000/get_user/{outward_number}')
#             user_response.raise_for_status()
#             user_data = user_response.json()
#         except requests.exceptions.RequestException as e:
#             logger.error(f"Error fetching user data: {str(e)}")
#             return jsonify({
#                 "success": False,
#                 "error": f"Failed to fetch user data: {str(e)}"
#             }), 500

#         # Verify template file exists
#         template_path = "MOD 3.docx"
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
#             Survey_no = f"Survey No:" + user_data["user"]["gutnumber"]
#             site_adress = f"Village :{user_data['user']['village']} Taluka :{user_data['user']['taluka']} District :{user_data['user']['district']} Pincode :{user_data['user']['pincode']}"

#             # Update date in all headers - Get current date in the desired format (DD/MM/YYYY)
#             import datetime
#             from docx.enum.text import WD_ALIGN_PARAGRAPH  # Add this import
#             current_date = datetime.datetime.now().strftime("%d/%m/%Y")
#             logger.info(f"Current Date: {current_date}")  # Log the date
            
#             # Update the date in every section's header
#             date_updated = False
#             for section in docmonarch.sections:
#                 header = section.header
                
#                 # First check paragraphs in the header
#                 for paragraph in header.paragraphs:
#                     text = paragraph.text
#                     logger.info(f"Header Paragraph Text: '{text}'")  # Log the text content
                    
#                     if "Date" in text:
#                         paragraph.clear()
#                         run = paragraph.add_run(f"Date - {current_date}")
#                         run.font.name = 'Arial'
#                         run.font.size = Pt(12)
#                         run.font.bold = True
#                         logger.info(f"Updated paragraph with date: {paragraph.text}")
#                         date_updated = True
                
#                 # Check for date in header tables
#                 for table in header.tables:
#                     for row in table.rows:
#                         for cell in row.cells:
#                             for paragraph in cell.paragraphs:
#                                 text = paragraph.text
#                                 logger.info(f"Header Table Cell Text: '{text}'")
                                
#                                 if "Date" in text:
#                                     paragraph.clear()
#                                     run = paragraph.add_run(f"Date - {current_date}")
#                                     run.font.name = 'Arial'
#                                     run.font.size = Pt(12)
#                                     run.font.bold = True
#                                     logger.info(f"Updated table cell with date: {paragraph.text}")
#                                     date_updated = True
            
#             # If no date field was found in headers, check the main document body
#             if not date_updated:
#                 logger.info("No date field found in headers, checking document body")
#                 for paragraph in docmonarch.paragraphs:
#                     if "Date" in paragraph.text:
#                         paragraph.clear()
#                         run = paragraph.add_run(f"Date - {current_date}")
#                         run.font.name = 'Arial'
#                         run.font.size = Pt(12)
#                         run.font.bold = True
#                         logger.info(f"Updated body paragraph with date: {paragraph.text}")
#                         date_updated = True
#                         break
            
#             # If still no date field found, try to add it to the header
#             if not date_updated:
#                 logger.info("No date field found, adding to first section header")
#                 if docmonarch.sections:
#                     header = docmonarch.sections[0].header
#                     paragraph = header.add_paragraph(f"Date - {current_date}")
#                     paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT

#                     paragraph_format = paragraph.paragraph_format
#                     paragraph_format.right_indent = Inches(0.5)  # Right padding
#                     # paragraph_format.line_spacing = Pt(6)  # Adjust line spacing as needed
#                     # paragraph_format.space_after = Pt(10)  # Bottom margin
#                     section = docmonarch.sections[0]
#                     section.top_margin = Inches(0.5)  # Adjust the top margin of the section


                    

#                     run = paragraph.runs[0]
#                     run.font.name = 'Arial'
#                     run.font.size = Pt(12)
#                     # run.font.bold = True
#                     logger.info(f"Added new date field to header: {paragraph.text}")

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
#                 paragraph = docmonarch.paragraphs[9]
#                 paragraph.clear()
#                 run = paragraph.add_run(corresponding_Address)
#                 run.font.name = 'Arial'
#                 run.font.size = Pt(12)
#                 run.font.bold = True
#                 set_paragraph_format(paragraph)
#                 paragraph.paragraph_format.left_indent = Inches(0.2)

#             if len(docmonarch.paragraphs) > 15:
#                 paragraph = docmonarch.paragraphs[7]  
#                 paragraph.clear()
#                 run = paragraph.add_run(Survey_no)
#                 run.font.name = 'Arial'
#                 run.font.size = Pt(12)
#                 run.font.bold = True
            
#             if len(docmonarch.paragraphs) > 15:
#                 paragraph = docmonarch.paragraphs[13]  
#                 paragraph.clear()
#                 run = paragraph.add_run(Survey_no)
#                 run.font.name = 'Arial'
#                 run.font.size = Pt(12)
#                 # run.font.bold = True

#             if len(docmonarch.paragraphs) > 17:
#                 paragraph = docmonarch.paragraphs[8]  
#                 paragraph.clear()
#                 run = paragraph.add_run(site_adress)
#                 run.font.name = 'Arial'
#                 run.font.size = Pt(12)
#                 run.font.bold = True

#             if len(docmonarch.paragraphs) > 17:
#                 paragraph = docmonarch.paragraphs[15]  
#                 paragraph.clear()
#                 run = paragraph.add_run(site_adress)
#                 run.font.name = 'Arial'
#                 run.font.size = Pt(12)
#                 # run.font.bold = True

#             # Update table with coordinates data
#             if docmonarch.tables:
#                 if len(docmonarch.tables) > 1:
#                     # Get references to both tables
#                     table = docmonarch.tables[0]  # First table (for entries starting with P/p)
#                     table1 = docmonarch.tables[1]  # Second table (for other entries)
#                     row_index = 3  # Row index where data starts

#                     # Clear existing data rows from both tables
#                     for _ in range(len(table.rows) - row_index):
#                         table._element.remove(table.rows[row_index]._element)

#                     for _ in range(len(table1.rows) - row_index):
#                         table1._element.remove(table1.rows[row_index]._element)

#                     # Initialize separate counters for each table
#                     serial_number_table = 1  # Counter for first table
#                     serial_number_table1 = 1  # Counter for second table (will start from 1)

#                     for entry in coordinates_data:
#                         # Check if point name starts with P/p
#                         if re.match(r"^\s*[Pp]", entry['P_name']):
#                             # Process for FIRST table
#                             new_row = table.add_row()
#                             prevent_row_split(new_row)

#                             for i, cell in enumerate(new_row.cells):
#                                 # Clear existing content
#                                 for paragraph in cell.paragraphs:
#                                     paragraph._element.getparent().remove(paragraph._element)
                                
#                                 # Add new paragraph with controlled formatting
#                                 paragraph = cell.add_paragraph()
#                                 paragraph_format = paragraph.paragraph_format
#                                 paragraph_format.space_before = Pt(0)
#                                 paragraph_format.space_after = Pt(0)
#                                 paragraph_format.line_spacing = 1.0

#                                 # Add content based on column index
#                                 if i == 0:
#                                     run = paragraph.add_run(str(serial_number_table))
#                                 elif i == 1:
#                                     run = paragraph.add_run(f"Point No. {entry['P_name']} :- Differential GPS Observation taken on Ground IN STATIC mode")
#                                 elif i == 2:
#                                     run = paragraph.add_run(entry['latitude_dms'])
#                                 elif i == 3:
#                                     run = paragraph.add_run(entry['longitude_dms'])
#                                 elif i == 4:
#                                     run = paragraph.add_run(str(entry['Height']))
#                                 elif i == 5 and 'distances_to_reference_points_km' in entry:
#                                     run = paragraph.add_run(f"{entry['distances_to_reference_points_km']['NDA']:.2f} KM")
#                                 elif i == 6 and 'distances_to_reference_points_km' in entry:
#                                     run = paragraph.add_run(f"{entry['distances_to_reference_points_km']['loh']:.2f} KM")
#                                 elif i == 7 and 'boundary_distances' in entry:
#                                     run = paragraph.add_run(f"NDA Min Distance: {entry['boundary_distances']['NDAboundaryMinDistance']:.2f} KM\nLohgaon Min Distance: {entry['boundary_distances']['LohgaonBoundaryMinDistance']:.2f} KM")
                                
#                                 # Formatting
#                                 run.font.name = "Arial"
#                                 run.font.size = Pt(12)

#                             serial_number_table += 1  # Increment only first table's counter

#                         else:
#                             # Process for SECOND table
#                             new_row = table1.add_row()
#                             prevent_row_split(new_row)

#                             for i, cell in enumerate(new_row.cells):
#                                 # Clear existing content
#                                 for paragraph in cell.paragraphs:
#                                     paragraph._element.getparent().remove(paragraph._element)
                                
#                                 # Add new paragraph with controlled formatting
#                                 paragraph = cell.add_paragraph()
#                                 paragraph_format = paragraph.paragraph_format
#                                 paragraph_format.space_before = Pt(0)
#                                 paragraph_format.space_after = Pt(0)
#                                 paragraph_format.line_spacing = 1.0

#                                 # Add content based on column index
#                                 if i == 0:
#                                     run = paragraph.add_run(str(serial_number_table1))  # Starts from 1
#                                 elif i == 1:
#                                     run = paragraph.add_run(f"Point No. {entry['P_name']} :- Differential GPS Observation taken on Ground IN STATIC mode")
#                                 elif i == 2:
#                                     run = paragraph.add_run(entry['latitude_dms'])
#                                 elif i == 3:
#                                     run = paragraph.add_run(entry['longitude_dms'])
#                                 elif i == 4:
#                                     run = paragraph.add_run(str(entry['Height']))
#                                 elif i == 5 and 'distances_to_reference_points_km' in entry:
#                                     run = paragraph.add_run(f"{entry['distances_to_reference_points_km']['NDA']:.2f} KM")
#                                 elif i == 6 and 'distances_to_reference_points_km' in entry:
#                                     run = paragraph.add_run(f"{entry['distances_to_reference_points_km']['loh']:.2f} KM")
#                                 elif i == 7 and 'boundary_distances' in entry:
#                                     run = paragraph.add_run(f"NDA Min Distance: {entry['boundary_distances']['NDAboundaryMinDistance']:.2f} KM\nLohgaon Min Distance: {entry['boundary_distances']['LohgaonBoundaryMinDistance']:.2f} KM")
                                
#                                 # Formatting
#                                 run.font.name = "Arial"
#                                 run.font.size = Pt(12)

#                             serial_number_table1 += 1  # Increment only second table's counter

#                         # Apply cell alignment for all new rows
#                         for cell in new_row.cells:
#                             set_cell_alignment(cell, vertical="center", horizontal="center")

#                     # Final table formatting
#                     set_table_borders(table)
#                     set_table_borders(table1)
#                     adjust_table_cell_alignments(table)
#                     adjust_table_cell_alignments(table1)

#                     paragraph = docmonarch.add_paragraph()
#                     run = paragraph.add_run()
#                     run.add_break(WD_BREAK.PAGE)

#                     # # ====== 100% WORKING PAGE BREAK ======
#                     # # 1. Create a new empty paragraph
                    

#                     paragraph_after_table1 = docmonarch.add_paragraph()
#                     p1 = paragraph_after_table1._element
#                     br1 = OxmlElement('w:br')
#                     br1.set(qn('w:type'), 'page')
#                     p1.append(br1)
#                     table._element.addnext(p1)  # Insert after first table

#                     # ====== 2. Page Break After Second Table (table1) ======
#                     paragraph_after_table2 = docmonarch.add_paragraph()
#                     p2 = paragraph_after_table2._element
#                     br2 = OxmlElement('w:br')
#                     br2.set(qn('w:type'), 'page')
#                     p2.append(br2)
#                     table1._element.addnext(p2) 

                
                

#             # Save document
#             output_docx = 'modified_output.docx'
#             output_pdf = 'modified_output.pdf'
#             docmonarch.save(output_docx)     
            
            
#             docmonarch = None  # Release the document

#             system = platform.system()
            
#             # Convert to PDF using platform-specific method
#             if convert_to_pdf(output_docx, output_pdf):
#                 if not os.path.exists(output_pdf):
#                     raise Exception("PDF file was not created")

#                 return jsonify({
#                     "success": True,
#                     "message": "Document generated successfully",
#                     "docPath": os.path.abspath(output_docx),
#                     "pdfPath": os.path.abspath(output_pdf)
#                 })
#             else:
#                 return jsonify({
#                     "success": False,
#                     "error": "Failed to convert document to PDF"
#                 }), 500

#         except Exception as e:
#             logger.error(f"Error during document generation: {str(e)}")
#             return jsonify({
#                 "success": False,
#                 "error": f"Error during document generation: {str(e)}"
#             }), 500

#     except Exception as e:
#         logger.error(f"Unexpected error: {str(e)}")
#         return jsonify({
#             "success": False,
#             "error": f"Unexpected error: {str(e)}"
#         }), 500





#-------------------------old Map generation code--------------------------


# def map_sattelite(coords, points_with_labels,nearest_points_list, output_map="static/map.html"):
#     """
#     Create a folium map with a polygon, labeled points, and an export-to-PDF button on Google Satellite imagery.
    
#     Args:
#         coords (list): List of (latitude, longitude) tuples for the polygon.
#         points_with_labels (list): List of tuples [(lat, lon, label), ...] for points with labels.
#         output_map (str): Path to save the output HTML map.
    
#     Returns:
#         str: Path to the saved HTML map.
#     """
#     swapped_coords = [(lat,lon) for lon, lat  in coords]
#     m = folium.Map(
#         # location=[coords[0][0], coords[0][1]],
#         location = swapped_coords[0],
#         zoom_start=10,
#         tiles=None  # Disable default tiles
#     )
#     m.add_child(MeasureControl())

#     folium.TileLayer(
#         tiles="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
#         attr="OpenStreetMap",
#         name="OpenStreetMap",
#         overlay=False,
#         control=True  # Allow users to toggle this layer
#     ).add_to(m)
    
#     # Add Google Satellite Tiles
#     folium.TileLayer(
#         tiles="https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}",
#         attr="Google Satellite",
#         name="Google Satellite",
#         overlay=False,
#         control=True
#     ).add_to(m) 
    
#     polygon = folium.Polygon(
#         locations=swapped_coords,  # List of (latitude, longitude) tuples
#         color="red",
#         weight=3,
#         fill=True,
#         fill_color="cyan",
#         fill_opacity=0.4,
#         popup="Polygon Area"
#     ).add_to(m)

#     Aviation_boundary = folium.WmsTileLayer(
#         url="https://iwmsgis.pmc.gov.in/geoserver/wms?",
#         name="Aviation Boundaries",
#         layers="MOD:Aviation_Boundary",
#         fmt="image/png",
#         transparent=True,
#         overlay=True,
#         control=True
#     ).add_to(m)

    
#     Aviation_zone =folium.WmsTileLayer(
#         url="https://iwmsgis.pmc.gov.in/geoserver/wms?",
#         name="Aviation Zone",
#         layers="MOD:Aviation_data",
#         fmt="image/png",
#         transparent=True,
#         overlay=True,
#         opacity = 0.5,
#         control=True
#     ).add_to(m)

   
#     for point_pair in nearest_points_list:
#     # Each point_pair is a tuple of two points
#         point1 = point_pair[0]  
#         point2 = point_pair[1] 

#         # Calculate the distance between the two points using geodesic (this calculates the great-circle distance)
#         line_length = geodesic(point1, point2).kilometers  # Distance in kilometers

#         mid_point_lat = (point1[0] + point2[0]) / 2
#         mid_point_lon = (point1[1] + point2[1]) / 2
#         popup_message = f"Distance: {line_length:.2f} km"  # Format the distance to two decimal places

#         # Add the PolyLine to the map with the popup showing the distance
#         folium.PolyLine(
#             locations=[point1, point2],  # Coordinates of the points to draw a line between
#             color="yellow",  # Color for the line
#             weight=1,  # Line thickness
#         ).add_to(m).add_child(folium.Popup(popup_message))

#         folium.Marker(
#         location=[mid_point_lat, mid_point_lon],  # Midpoint of the line
#         icon=folium.DivIcon(
#             icon_size=(150, 36),  # Size of the label
#             icon_anchor=(7, 20),  # Position of the label
#             html=f'<div style="font-size: 16px; font-weight: bold; color: yellow;">{line_length:.2f} km</div>'  # Label style
#         ),
#     ).add_to(m)


#     for lat, lon, label in points_with_labels:
#         folium.CircleMarker(
#             location=(lat, lon),
#             radius=3,  # Small dot size
#             color="blue",
#             fill=True,
#             fill_color="blue",
#             fill_opacity=0.5,
#             popup=f"{label}",  # Add label as a popup
#         ).add_to(m)

#         folium.Marker(
#         location=[lat, lon], 
#         icon=folium.DivIcon(
#             icon_size=(150, 36),  # Size of the label
#             icon_anchor=(7, 20),  # Position of the label
#             html=f'<div style="font-size: 12px; font-weight: bold; color: yellow;">{label}</div>'  # Label style
#         ),
#     ).add_to(m)

#     m.fit_bounds(polygon.get_bounds()) 
#     # Add a custom button to export to PDF
#     pdf_button = """
#       <script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js" integrity="sha512-BNaRQnYJYiPSqHHDb58B0yaPfCu+Wgds8Gp/gU33kqBtgNS4tSPHuGibyoeqMV/TJlSKda6FXzoEyYGjTe+vXA==" crossorigin="anonymous" referrerpolicy="no-referrer"></script>
#             <script src="https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js"></script>
#                 <div style="position: fixed; 
#                             bottom: 50px; left: 50px; width: 150px; height: 30px; 
#                             z-index: 1000;">
#                     <button onclick="exportToPDF()" style="width: 150px; height: 30px; background-color: #4CAF50; color: white; border: none; border-radius: 5px;">
#                         Export to PDF
#                     </button>
#                 </div>
            
#                 <script>
#                 function exportToPDF() {
#     try {
#         const { jsPDF } = window.jspdf;
#         const doc = new jsPDF();

#         // Select the map container dynamically
#         const mapContainer = document.querySelector('.folium-map');

#         const originalScrollX = window.scrollX;
#         const originalScrollY = window.scrollY;

#         html2canvas(mapContainer, {
#             scale: 2, // Scale for high resolution
#             useCORS: true, // Handle cross-origin images
#             scrollX: originalScrollX, // Maintain original horizontal scroll position
#             scrollY: originalScrollY, // Maintain original vertical scroll position
#         }).then(function (canvas) {
#             const imgData = canvas.toDataURL('image/png');
#             const pdfWidth = 180; // Maximum width for PDF
#             const aspectRatio = canvas.width / canvas.height;
#             const imgHeight = pdfWidth / aspectRatio; // Maintain aspect ratio

#             // Center the map image in the PDF
#             const pageWidth = doc.internal.pageSize.getWidth();
#             const centerX = (pageWidth - pdfWidth) / 2;

#             // Add the image to the PDF
#             doc.addImage(imgData, 'PNG', centerX, 10, pdfWidth, imgHeight);

#             // Save the generated PDF
#             const fileName = `map_export.pdf`;
#             doc.save(fileName);
#         });
#     } catch (error) {
#         console.error('Error generating PDF:', error);
#         alert('Failed to generate PDF. Check console for details.');
#     }
# }


#     </script>
#     """
#     m.get_root().html.add_child(folium.Element(pdf_button))

#     folium.LayerControl().add_to(m)
#     m.save(output_map)
#     return output_map
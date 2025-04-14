import psycopg2
def fetchData(outward_number):
   outward_number1= str(outward_number)
   try:
       # Establish the connection
       conn = psycopg2.connect(
           dbname="MOD",
           user="postgres",
           password="geopulse123",       #pmc992101
           host="103.167.184.133",  # iwmsgis.pmc.gov.in
           port="5435"   #  5432
       )
       print("Connection to PostgreSQL DB successful")
       cur = conn.cursor()
       cur.execute("SELECT name,gut,villagename,talukaname,districtname, excel_name FROM mod WHERE outward = %s", (outward_number1,))
       rows = cur.fetchall()
       print(rows)
       if rows:
           a, b, c, d, e,f = rows[0]
           #print(a,'0000000000000000')
       cur.close()
       conn.close()
       print("Connection close")
       return a, "Gut/Survey/CTS Number = {}".format(b), c, d, e,f
   except Exception as e:
       print(f"An error occurred: {e}")




print(fetchData('1105'))
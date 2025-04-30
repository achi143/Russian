import pandas as pd 
import requests
import io
import psycopg2
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv
import os

#Load environment variable
load_dotenv()

#kobo credentials
KOBO_USERNAME = os.getenv("KOBO_USERNAME")
KOBO_PASSWORD = os.getenv("KOBO_PASSWORD")
KOBO_CSV_URL = "https://kf.kobotoolbox.org/api/v2/assets/av6HrwGEGk7KJhw85Lyz4T/export-settings/es2XWjdbfb55zGtNGGcoKSW/data.csv"


# postgresql credentials

PG_HOST = os.getenv("PG_HOST")
PG_DATABASE = os.getenv("PG_DATABASE")
PG_USER = os.getenv("PG_USER")
PG_PASSWORD = os.getenv("PG_PASSWORD")
PG_PORT = os.getenv("PG_PORT")


# schema table details
schema_name = "war"
table_name = "russia_ukrain"  # please avoid special character in the table name


# Fetch data from Kobo toolbox
print("✅Fetching data from kobotoolbox....")
response = requests.get(KOBO_CSV_URL, auth=HTTPBasicAuth(KOBO_USERNAME,KOBO_PASSWORD))

if response.status_code == 200:

    print("✅Data fetched succesfully")

    csv_data = io.StringIO(response.text)
    df  = pd.read_csv(csv_data, sep=';', on_bad_lines='skip')

    # step 2 clean and transform data
    print("✅processing data...")

    df.columns = [col.strip().replace(" ", "_").replace("&", "and").replace("-", "_") for col in df.columns]

    # compute total casualties

    df["Total_soldier_casualties"] = df[["casualties","Injured","captured"]].sum(axis=1)

    #convert Date to proper format(optional)

    df["Date"] = pd.to_datetime(df["Date"], errors='coerce')

    # step 3 : upload to postgreSQL

    print("upload data to postgreSQL....")

    conn = psycopg2.connect(
        host = PG_HOST,
        database = PG_DATABASE,
        user = PG_USER,
        password = PG_PASSWORD,
        port = PG_PORT
    )

    cur = conn.cursor()

    #create schema if it doesn't exist

    cur.execute(f"create schema if not exists {schema_name};")

    # drop and recreate table (for simplicity)

    cur.execute(f"drop table if exists {schema_name}.{table_name};")
    cur.execute(f"""
            create table {schema_name}.{table_name} (
            id serial primary key,
            "start" Timestamp,
            "end" Timestamp,
            "date" DATE,
            "country" Text,
            event Text,
            oblast Text,
            casulaties INT,
            injured INT,
            captured INT,
            civilian_casualties INT,
            new_recruits INT,
            combat_intensity FLOAT,
            territory_status Text,
            area occupied Float,
            total_casualties INT
        );
    """)


    # Insert Data row by row

    insert_query = f"""
        insert into {schema_name}.{table_name}(
            "start","end","date","country",event ,oblast,casulaties,injured,captured ,
             civilian_casualties,new_recruits,combat_intensity,territory_status,
            area occupied,total_casualties .      
            
            )  values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) 

    """ 
    for _, row in df.iterrows():
       cur.execute(insert_query, (
        row.get("start"),
        row.get("end"),
        row.get("Date"),
        row.get("country"),
        row.get("event"),
        row.get("oblast"),
        row.get("casulaties", 0),
        row.get("injured", 0),
        row.get("captured", 0),
        row.get("civilian_casualties", 0),
        row.get("new_recruits", 0),
        row.get("combat_intensity", 0),
        row.get("territory_status", 0),
        row.get("area occupied", 0),  # (keep quotes if not renamed)
        row.get("total_casualtie", 0),  # (fix spelling if needed)
    ))  

    conn.commit()
    cur.close()
    conn.close()




    print("✅Data Successfully loaded into postresql!")

else:
   print(f"❌failed to tech data status code : {response.status_code}")

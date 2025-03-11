import json
import os
import sys
from datetime import date, datetime

import dotenv
import requests

dotenv.load_dotenv()
API_KEY = os.getenv("EPA_API_KEY")
# S3 bucket url base + s3Path (in get request) = the full path to the files
BUCKET_URL_BASE = "https://api.epa.gov/easey/bulk-files/"

parameters = {"api_key": API_KEY}

# change this to the date you want to start downloading files from
# all files after this date and time will be downloaded
dateToday = date.today()
month, year = (dateToday.month - 1, dateToday.year) if dateToday.month != 1 else (12, dateToday.year - 1)
prevMonth = dateToday.replace(day=1, month=month, year=year)
timeOfLastDownload = datetime.fromisoformat(str(prevMonth) + "T00:00:00.000Z"[:-1] + "+00:00")

# executing get request
response = requests.get("https://api.epa.gov/easey/camd-services/bulk-files", params=parameters, timeout=60)


if int(response.status_code) > 399:
    sys.exit("Error message: " + response.json()["error"]["message"])

# converting the content from json format to a data frame
resjson = response.content.decode("utf8").replace("'", '"')
bulkFiles = json.loads(resjson)

for bulkFile in bulkFiles:
    print(json.dumps(bulkFile))

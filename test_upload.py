import requests

url = "http://127.0.0.1:8000/api/v1/ingest/excel"

# We don't have a valid semester_id, so we'll just make one up or use a UUID.
# If the DB can't be reached, it'll fail anyway.
data = {
    "department_code": "ECSE",
    "semester_id": "00000000-0000-0000-0000-000000000000"
}

files = {
    "file": ("ECSE Summer.xlsx", open("ECSE Summer.xlsx", "rb"), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
}

try:
    response = requests.post(url, data=data, files=files)
    print(f"Status Code: {response.status_code}")
    print("Response JSON:")
    try:
        print(response.json())
    except:
        print(response.text)
except Exception as e:
    print(f"Error: {e}")

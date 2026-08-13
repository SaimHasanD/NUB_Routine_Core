import requests

url = "https://nub-routine-core.onrender.com/api/v1/ingest/excel"

data = {
    "department_code": "ECSE",
    "semester_id": "763e59f8-ad6b-436b-a409-1ab76e23b5a2"
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

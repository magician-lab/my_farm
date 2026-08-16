import requests
import time
from datetime import datetime

URL = "https://my-farm-donn.onrender.com/health"

while True:
    try:
        response = requests.get(URL, timeout=30)

        print(
            f"{datetime.now()} | "
            f"Status: {response.status_code}"
        )

    except Exception as e:
        print(
            f"{datetime.now()} | Error: {e}"
        )

    time.sleep(240)  # 2minutes
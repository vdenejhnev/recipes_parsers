import requests

class Request:
    def __init__(self, base_url):
        self.base_url = base_url

    def sendGet(self, endpoint=None, params=None):
        try:
            if endpoint is None: 
                url = f"{self.base_url}"
            else:   
                url = f"{self.base_url}/{endpoint}"
        
            response = requests.get(url, params=params)
            return response
        except requests.exceptions.RequestException as e:
            print(f"Error sending GET request: {e}")

            return None

    def sendPost(self, endpoint, data, headers=None):
        try:
            if headers is None:
                headers = {
                    "Content-Type": "application/json"
                }

            url = f"{self.base_url}{endpoint}"
            response = requests.post(url, json=data, headers=headers)
            response.raise_for_status()

            return response
        except requests.exceptions.RequestException as e:
            print(f"Error sending POST request: {e}")

            return None
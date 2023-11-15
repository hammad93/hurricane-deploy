import json
import requests
import os
import test
import time

def run_tts():
  '''
  Runs the container on the web service that generates and uploads the 
  text to speech artificial intelligence through Azure.

  https://github.com/Azure-Samples/azure-samples-python-management/blob/main/samples/containerinstance/manage_container_group.py
  '''
  test.setup() # setups up environment
  
  # Azure Service Principal Credentials
  tenant_id = os.environ['AZURE_TENANT_ID']
  client_id = os.environ['AZURE_CLIENT_ID']
  client_secret = os.environ['AZURE_CLIENT_SECRET']
  acr_secret = os.environ['AZURE_CONTAINER_REGISTRY_PWD']
  
  # Azure Resource Details
  subscription_id = '6fabfb83-efda-4669-a00e-8c928dcd4b18'
  resource_group = 'jupyter-lab_group'
  container_group_name = f'tts{int(time.time())}'
  image_id = "huraim.azurecr.io/hurricane-tts:latest"
  
  # Azure REST API Endpoint
  resource = "https://management.azure.com/"
  url = f"https://management.azure.com/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/Microsoft.ContainerInstance/containerGroups/{container_group_name}?api-version=2021-07-01"
  
  # Body of the request
  container_instance_body = {
      # Add your container instance details here
      "location": "eastus",
      "properties": {
          "containers": [
              {
                  "name": container_group_name,
                  "properties": {
                      "image": image_id,
                      "resources": {
                          "requests": {
                              "cpu": 2,
                              "memoryInGb": 8
                          }
                      }
                  }
              }
          ],
          "osType": "Linux",
          "imageRegistryCredentials": [
            {
                "server": "huraim.azurecr.io",  # Replace with your registry server
                "username": "huraim",  # Replace with your registry username
                "password": acr_secret  # Replace with your registry password
            }
        ],
        "restartPolicy": "Never"  # Set the restart policy to Never
      }
  }
  
  # Function to obtain the OAuth2 token
  def get_access_token(tenant_id, client_id, client_secret):
      url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/token"
      payload = {
          'grant_type': 'client_credentials',
          'client_id': client_id,
          'client_secret': client_secret,
          'resource': resource
      }
      response = requests.post(url, data=payload).json()
      return response['access_token']
  
  # Function to create the container instance
  def create_container_instance(url, token, body):
      headers = {
          'Authorization': f'Bearer {token}',
          'Content-Type': 'application/json'
      }
      response = requests.put(url, headers=headers, json=body)
      return response
  
  # Main process
  access_token = get_access_token(tenant_id, client_id, client_secret)
  response = create_container_instance(url, access_token, container_instance_body)
  
  # Output the result
  print(response.status_code, response.json())

def web_screenshot(url = 'http://fluids.ai:7000/', out = 'screenshot.png'):
  import time
  from selenium import webdriver
  from selenium.webdriver.chrome.options import Options
  from selenium.webdriver.chrome.service import Service
  from webdriver_manager.chrome import ChromeDriverManager
  
  # Configure Selenium options
  options = Options()
  options.add_argument('--headless')  # Run in headless mode for a headless machine
  options.add_argument('--disable-dev-shm-usage')  # Overcome limited resource problems
  options.add_argument('--disable-gpu')  # Disable GPU hardware acceleration
  options.add_argument('--no-sandbox')  # Bypass OS security model, required in some environments
  
  # Initialize the Chrome driver
  driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
  
  # Navigate to the url
  driver.get(url)
  
  # Wait for the map to load fully. Adjust time as needed based on network speed and map complexity
  time.sleep(10)  # Sleep for 10 seconds (or more if needed)
  
  # Take and save a screenshot
  driver.save_screenshot(out)
  
  # Close the browser
  driver.quit()

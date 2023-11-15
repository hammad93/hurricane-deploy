from azure.identity import DefaultAzureCredential
from azure.mgmt.containerinstance import ContainerInstanceManagementClient
from azure.mgmt.resource import ResourceManagementClient
import test
import requests
import json
import os

def run_tts():
  '''
  Runs the container on the web service that generates and uploads the 
  text to speech artificial intelligence through Azure.

  https://github.com/Azure-Samples/azure-samples-python-management/blob/main/samples/containerinstance/manage_container_group.py
  '''
  test.setup() # setups up environment
  
  # Azure details
  SUBSCRIPTION_ID = '6fabfb83-efda-4669-a00e-8c928dcd4b18'
  GROUP_NAME = 'jupyter-lab_group'
  CONTAINER_GROUP = 'huraim'
  CONTAINER_NAME = 'huraim'
  IMAGE_ID ='huraim.azurecr.io/hurricane-tts'
  
  # Authenticate with Azure
  # https://learn.microsoft.com/en-us/azure/developer/python/sdk/authentication-on-premises-apps?tabs=azure-portal
  # Create client
  # # For other authentication approaches, please see: https://pypi.org/project/azure-identity/
  resource_client = ResourceManagementClient(
      credential=DefaultAzureCredential(),
      subscription_id=SUBSCRIPTION_ID
  )
  containerinstance_client = ContainerInstanceManagementClient(
      credential=DefaultAzureCredential(),
      subscription_id=SUBSCRIPTION_ID
  )
  
  # Create resource group
  resource_client.resource_groups.create_or_update(
      GROUP_NAME,
      {"location": "eastus"}
  )
  
  # Create container group
  container_group = containerinstance_client.container_groups.begin_create_or_update(
      GROUP_NAME,
      CONTAINER_GROUP,
      {
        "location": "eastus",
        "identity": {
          "type": "SystemAssigned"
        },
        "containers": [
          {
            "name": CONTAINER_NAME,
            "command": [],
            "environment_variables": [],
            "image": IMAGE_ID,
            "ports": [
              {
                "port": "80"
              }
            ],
            "resources": {
              "requests": {
                "cpu": "4",
                "memory_in_gb": "8"
              }
            }
          }
        ],
        "os_type": "Linux",
        "restart_policy": "OnFailure"
      }
  ).result()
  print("Create container group:\n{}".format(container_group))
  
  # Get container group
  container_group = containerinstance_client.container_groups.get(
      GROUP_NAME,
      CONTAINER_GROUP
  )
  print("Get container group:\n{}".format(container_group))
  
  # Update container group
  container_group = containerinstance_client.container_groups.update(
      GROUP_NAME,
      CONTAINER_GROUP,
      {
        "tags": {
          "tag1key": "tag1Value",
          "tag2key": "tag2Value"
        }
      }
  )
  print("Update container group:\n{}".format(container_group))
  
  # Container exec
  result = containerinstance_client.containers.execute_command(
      GROUP_NAME,
      CONTAINER_GROUP,
      CONTAINER_NAME,
      {
        "command": "/bin/bash",
        "terminal_size": {
          "rows": "12",
          "cols": "12"
        }
      }
  )
  print("Container exec:\n{}".format(result))
  
  # Delete container group
  container_group = containerinstance_client.container_groups.begin_delete(
      GROUP_NAME,
      CONTAINER_GROUP
  ).result()
  print("Delete container group.\n")
  
  # Delete Group
  resource_client.resource_groups.begin_delete(
      GROUP_NAME
  ).result()
  return True
def run_tts_rest():
  # Azure Service Principal Credentials
  tenant_id = os.environ['AZURE_TENANT_ID']
  client_id = os.environ['AZURE_CLIENT_ID']
  client_secret = os.environ['AZURE_CLIENT_SECRET']
  
  # Azure Resource Details
  subscription_id = '6fabfb83-efda-4669-a00e-8c928dcd4b18'
  resource_group = 'jupyter-lab_group'
  container_group_name = 'huraim'
  
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
                      "image": "mcr.microsoft.com/azure-cli",
                      "resources": {
                          "requests": {
                              "cpu": 4,
                              "memoryInGb": 8
                          }
                      }
                  }
              }
          ],
          "osType": "Linux",
          # Add more properties as needed
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
  return True

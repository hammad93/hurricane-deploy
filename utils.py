from azure.identity import DefaultAzureCredential
from azure.mgmt.containerinstance import ContainerInstanceManagementClient
from azure.mgmt.containerinstance.models import ContainerGroup, Container, ContainerPort, Port, ResourceRequests, ResourceRequirements, OperatingSystemTypes

import test

def run_tts():
  '''
  Runs the container on the web service that generates and uploads the 
  text to speech artificial intelligence through Azure.
  '''
  test.setup() # setups up environment
  
  # Azure details
  subscription_id = '6fabfb83-efda-4669-a00e-8c928dcd4b18'
  resource_group = 'jupyter-lab_group'
  container_group_name = 'huraim'
  container_image = 'huraim.azurecr.io/huraim'
  
  # Authenticate with Azure
  # https://learn.microsoft.com/en-us/azure/developer/python/sdk/authentication-on-premises-apps?tabs=azure-portal
  credential = DefaultAzureCredential()
  client = ContainerInstanceManagementClient(credential, subscription_id)

  # Define the container instance
  container_resource_requirements = ResourceRequirements(
      requests=ResourceRequests(
          memory_in_gb=8,
          cpu=2.0
      )
  )
  
  container_instance = Container(
      name=container_group_name,
      image=container_image,
      resources=container_resource_requirements,
      ports=[ContainerPort(port=80)]
  )

  # Define the container group
  container_group = ContainerGroup(
      location='eastus',
      containers=[container_instance],
      os_type=OperatingSystemTypes.linux
  )

  # Recreate the container instance
  response = client.container_groups.begin_create_or_update(resource_group, container_group_name, container_group)
  response.result()
  
  print(f"Container instance '{container_group_name}' recreated.")

import requests
from requests.auth import HTTPBasicAuth
import test

def create_post(title, content, **kwargs):
    '''
    Create wordpress post
    '''
    test.setup()
    url = 'https://fluids.ai/wp-json/wp/v2/posts'
    
    post = {
        'title': title,
        'content': content,
        'status': kwargs.get('status', 'private')
    }
    
    # Sending POST request to create a new post
    response = requests.post(
        url,
        auth=HTTPBasicAuth('user', os.environ['WP_PASS']),
        json=post)
    
    # Checking response
    if response.status_code == 201:
        print("Post created successfully, ID:", response.json()['id'])
    else:
        print("Failed to create post:", response.content)
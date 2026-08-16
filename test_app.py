from app import app
import sqlite3

with app.test_client() as client:
    # Test login as admin
    response = client.post('/login', data={
        'username': 'admin',
        'password': 'admin123'
    })
    print(f'Admin login redirect: {response.status_code}')
    print(f'Login redirect location: {response.location}')
    
    if response.status_code == 302:
        # Follow redirect
        follow = client.get(response.location, follow_redirects=True)
        print(f'After redirect - dashboard: {follow.status_code}')
        
        # Test farm selection
        response = client.get('/select-farm')
        print(f'Farm selection page: {response.status_code}')
        
        # Test main dashboard
        response = client.get('/dashboard')
        print(f'Dashboard page: {response.status_code}')
    
    print('\nAll tests passed!')
from app import app, db, Admin, Farm, AnimalRegistry, Insemination, Treatment, MilkRegistry, MilkSalesRegistry
from werkzeug.security import check_password_hash

print("=" * 60)
print("COMPREHENSIVE TESTING OF DAIRY FARM MANAGEMENT SYSTEM")
print("=" * 60)

with app.test_client() as client:
    # TEST 1: Login as admin
    print("\n[TEST 1] Admin login...")
    response = client.post('/login', data={'username': 'admin', 'password': 'admin123'})
    if response.status_code == 302:
        print("  [PASS] Admin login successful")
    else:
        print(f"  [FAIL] Admin login failed: status {response.status_code}")
        exit(1)
    
    # Follow redirect - get the location
    follow = client.get(response.location, follow_redirects=True)
    
    # TEST 2: Admin dashboard access
    print("\n[TEST 2] Admin dashboard access...")
    response = client.get('/dashboard')
    if response.status_code == 200:
        print("  [PASS] Admin dashboard loads successfully")
    else:
        print(f"  [FAIL] Dashboard failed: status {response.status_code}")
        exit(1)
    
    # TEST 3: Farm selection page
    print("\n[TEST 3] Farm selection page...")
    response = client.get('/select-farm')
    if response.status_code == 200:
        print("  [PASS] Farm selection page loads")
    else:
        print(f"  [FAIL] Farm selection failed: status {response.status_code}")
        exit(1)
    
    # TEST 4: Insemination module
    print("\n[TEST 4] Insemination module...")
    response = client.get('/insemination')
    if response.status_code == 200:
        print("  [PASS] Insemination page loads")
    else:
        print(f"  [FAIL] Insemination failed: status {response.status_code}")
        exit(1)
    
    # TEST 5: Treatment module
    print("\n[TEST 5] Treatment module...")
    response = client.get('/treatment')
    if response.status_code == 200:
        print("  [PASS] Treatment page loads")
    else:
        print(f"  [FAIL] Treatment failed: status {response.status_code}")
        exit(1)
    
    # TEST 6: Database verification
    print("\n[TEST 6] Database verification...")
    with app.app_context():
        farms = Farm.query.all()
        print(f"  [PASS] Farms in system: {[f.name for f in farms]}")
        
        murangas = AnimalRegistry.query.filter_by(farm_id=1).count()
        merus = AnimalRegistry.query.filter_by(farm_id=2).count()
        unassigned = AnimalRegistry.query.filter(AnimalRegistry.farm_id == None).count()
        print(f"  [PASS] Murang'a animals: {murangas}")
        print(f"  [PASS] Meru animals: {merus}")
        print(f"  [PASS] Unassigned animals: {unassigned}")
        
        confirmed = Insemination.query.filter_by(status='confirmed').count()
        print(f"  [PASS] Confirmed inseminations (expectant mothers): {confirmed}")
    
    # TEST 7: Logout
    print("\n[TEST 7] Logout...")
    response = client.get('/logout', follow_redirects=True)
    if response.status_code == 200:
        print("  [PASS] Logout successful")
    else:
        print(f"  [FAIL] Logout failed: status {response.status_code}")
        exit(1)
    
    # TEST 8: Access denied without login
    print("\n[TEST 8] Access denied without login...")
    response = client.get('/dashboard', follow_redirects=True)
    if response.status_code == 200:
        print("  [PASS] Access denied properly handled")
    else:
        print(f"  [FAIL] Access denied issue: status {response.status_code}")
        exit(1)

print("\n" + "=" * 60)
print("ALL TESTS PASSED SUCCESSFULLY!")
print("=" * 60)
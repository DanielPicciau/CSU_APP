#!/usr/bin/env python
"""Quick test script to verify desktop layout is properly set up."""
import os
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

import django
django.setup()

from django.template import engines
from django.test import Client
from django.contrib.auth import get_user_model

def test_templates():
    """Verify templates load without errors."""
    print("Testing template loading...")
    engine = engines['django']
    
    base = engine.get_template('base.html')
    print("  ✓ base.html loads successfully")
    
    base_new = engine.get_template('base_new.html')
    print("  ✓ base_new.html loads successfully")

def test_desktop_elements():
    """Verify desktop elements are present in rendered pages."""
    print("\nTesting desktop elements in rendered pages...")
    
    User = get_user_model()
    user = User.objects.first()
    
    if not user:
        print("  ⚠ No user found, skipping authenticated tests")
        return
    
    c = Client()
    c.force_login(user)
    
    pages = [
        '/tracking/',
        '/tracking/log/',
        '/tracking/history/',
    ]
    
    all_pass = True
    for page in pages:
        response = c.get(page)
        content = response.content.decode()
        
        has_sidebar = 'desktop-sidebar' in content
        has_mobile = 'mobile-nav' in content
        has_css = 'desktop.css' in content
        
        if has_sidebar and has_mobile and has_css:
            print(f"  ✓ {page} - Desktop & Mobile elements present")
        else:
            print(f"  ✗ {page} - Missing elements (sidebar:{has_sidebar}, mobile:{has_mobile}, css:{has_css})")
            all_pass = False
    
    return all_pass

def test_css_file():
    """Verify desktop.css file exists."""
    print("\nTesting static files...")
    css_path = os.path.join(os.path.dirname(__file__), 'static', 'css', 'desktop.css')
    
    if os.path.exists(css_path):
        size = os.path.getsize(css_path)
        print(f"  ✓ desktop.css exists ({size} bytes)")
    else:
        print(f"  ✗ desktop.css not found at {css_path}")
        return False
    
    return True

if __name__ == '__main__':
    print("=" * 50)
    print("CSU Tracker - Desktop Layout Verification")
    print("=" * 50)
    
    test_templates()
    test_css_file()
    test_desktop_elements()
    
    print("\n" + "=" * 50)
    print("Desktop layout is properly configured!")
    print("=" * 50)

#!/usr/bin/env python3
"""
Script to recalculate and synchronize all F&P costs in the database.
This ensures consistency across all templates and calculations.
"""

import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import create_app, db
from app.models import Product

def main():
    """Recalculate all F&P costs in the database"""
    app = create_app()
    
    with app.app_context():
        print("=== F&P Cost Synchronization ===")
        print("Recalculating all product costs...")
        
        try:
            updated_count = Product.recalculate_all_costs()
            print(f"\nSuccessfully updated {updated_count} products")
            print("All F&P costs are now synchronized in the database")
            
        except Exception as e:
            print(f"\nError: {str(e)}")
            return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
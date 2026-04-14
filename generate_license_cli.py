#!/usr/bin/env python
from license_manager import LicenseManager
import sys

def main():
    print("="*60)
    print("License Generator")
    print("="*60)
    
    customer_name = input("Customer Name: ")
    email = input("Email: ")
    expiry_days = int(input("Expiry Days (default 30): ") or 30)
    max_users = int(input("Max Users (default 5): ") or 5)
    
    lm = LicenseManager()
    license_key = lm.generate_license(customer_name, email, expiry_days, max_users)
    
    print("\n" + "="*60)
    print("LICENSE GENERATED")
    print("="*60)
    print(f"License Key:\n{license_key}")
    print("="*60)
    print("\nSave this license key and provide it to the customer.")
    
if __name__ == '__main__':
    main()
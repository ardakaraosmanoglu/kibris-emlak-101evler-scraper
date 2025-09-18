#!/usr/bin/env python3
"""
Example usage of the configuration system for 101evler.com scraper

This file demonstrates how to use the configuration system to easily
switch between different regions and property types.
"""

import config

def main():
    print("=== 101evler.com Scraper Configuration Examples ===")
    print()

    # Show available property types
    print("Available Property Types:")
    for prop_type, details in config.PROPERTY_TYPES.items():
        print(f"  - {prop_type}: {details['url_path']}")
    print()

    # Show available presets
    print("Available Region Presets:")
    for preset_name, preset_config in config.REGION_PRESETS.items():
        print(f"  - {preset_name}: {preset_config['CITY']} - {preset_config['PROPERTY_TYPE']}")
    print()

    # Example 1: Manual configuration
    print("=== Example 1: Manual Configuration ===")
    config.CITY = "magusa"
    config.PROPERTY_TYPE = "satilik-daire"
    config.SALE_TYPE = "R"
    config.show_config()
    print()

    # Example 2: Using presets
    print("=== Example 2: Using Presets ===")
    config.apply_preset("girne_villa")
    config.show_config()
    print()

    # Example 3: Custom configuration for rent
    print("=== Example 3: Rental Properties ===")
    config.CITY = "lefkosa"
    config.PROPERTY_TYPE = "kiralik-daire"
    config.SALE_TYPE = "L"  # L for rent
    config.show_config()
    print()

    # Show how to get generated URLs and parameters
    print("=== Generated URLs and Parameters ===")
    print(f"Search URL: {config.get_base_search_url()}")
    print(f"API Parameters: {config.get_api_params()}")
    print(f"Listing Pattern: {config.get_listing_pattern()}")
    print()

    # Validate configuration
    print("=== Configuration Validation ===")
    is_valid = config.validate_config()
    print(f"Configuration is valid: {is_valid}")

if __name__ == "__main__":
    main()
#Enhanced version that converts all integers to floats first, then maps to RGB
#This ensures consistent float-to-RGB conversion for all numeric data

import pandas as pd
import numpy as np
import re
import math
import itertools
from PIL import Image
import os
import struct
import json
import shutil

# ========= CONFIG ==============
INPUT_CSV = "source_in2.csv"
OUTPUT_DIR = "data"
IMAGE_SIZE = 150
TYPES_FILE = "data_types.json"  
DECODED = "from_image.csv"
# ===============================

#comment out the below sections, if you require the images or the json file. 
# ===DELETE EXISTING CONTENT ====
if os.path.exists(TYPES_FILE):
    os.remove(TYPES_FILE)
if os.path.exists(OUTPUT_DIR):
    shutil.rmtree(OUTPUT_DIR)
if os.path.exists(DECODED):
    os.remove(DECODED)
#===============================


df = pd.read_csv(INPUT_CSV, header=None)

# Type detection. Converts non network address fields to floats. 
def detect_column_types(df):
    final_types = []
    
    for col_idx in range(len(df.columns)):
        column_data = df.iloc[:, col_idx].astype(str)
        has_float = False
        has_ip = False
        has_mac = False
        has_numeric = False  # Combined int/float detection
        
        for value in column_data:
            value = str(value).strip()
            if re.match(r'^(\d{1,3}\.){3}\d{1,3}$', value):
                has_ip = True
            elif re.match(r'^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$', value):
                has_mac = True
            elif re.fullmatch(r'-?\d+\.\d+', value):
                has_numeric = True
                has_float = True
            elif re.fullmatch(r'-?\d+$', value):
                has_numeric = True

        
        # Priority: IP > MAC > Numeric (Float) > String.  All integers are now treated as floats
        if has_ip:
            final_types.append("IP Address")
        elif has_mac:
            final_types.append("MAC Address")
        elif has_numeric:  # Both integers and floats become floats
            final_types.append("Float")
        else:
            final_types.append("String")
    
    return final_types

# Enhanced type detection
types_list = detect_column_types(df)
print(f"Detected types: {types_list}")

# Debug types comment out if not needed
#for i, dtype in enumerate(types_list):
#    print(f"DEBUG: Column {i} = {dtype}")
#    if dtype == "Float":
#        print(f"  Sample values: {df.iloc[:3, i].tolist()}")

#Convert Float values to RGB values. This will produce two pixels to enusre a loss-less transformation
def float_to_two_rgb_pixels(float_val):
    try:
        # float into 4 bytes
        packed_bytes = struct.pack('!f', float_val)
        r1, g1, b1 = packed_bytes[0], packed_bytes[1], packed_bytes[2]
        r2 = packed_bytes[3]  # Last byte of the float
        g2 = 0  # Padding
        b2 = 0  # Padding
        
        return (r1, g1, b1), (r2, g2, b2)
    except Exception as e:
        print(f"Error converting float {float_val}: {e}")
        return (0, 0, 0), (0, 0, 0)

# RGB helpers
def convertLineToRGB(line):
    result = []
    for value in line:
        if isinstance(value, (tuple, list)):  # already RGB
            if len(value) == 2 and isinstance(value[0], tuple):  # Two RGB tuples
                result.extend(value)
            elif len(value) == 3:  # Single RGB tuple
                result.append(value)
            else:
                result.append((0, 0, 0))  # Default for invalid format
        else:
            result.append((0, 0, 0))
    return result

# MAC splitter 
def split_mac(data, types_list):
    new_data = []
    new_types = []
    
    for row_idx, row in enumerate(data):
        new_row = []
        current_types = []
        
        for col_idx, (value, dtype) in enumerate(zip(row, types_list)):
            if dtype == "MAC Address":
                # Split MAC address
                mac = str(value).replace(":", "")
                if len(mac) >= 12:
                    chunk1 = mac[:6]   # First 6 hex characters
                    chunk2 = mac[6:12] # Second 6 hex characters
                    new_row.extend([chunk1, chunk2])
                    current_types.extend(["MAC Address", "MAC Address"])
                else:
                    # Invalid MAC, treat as string
                    new_row.append(value)
                    current_types.append("String")
            else:
                new_row.append(value)
                current_types.append(dtype)
        
        new_data.append(new_row)
        if row_idx == 0:  # Only update types based on first row
            new_types = current_types
    
    return new_data, new_types

# IP splitter -  4 octets
def split_ip(data, types_list):
    new_data = []
    new_types = []
    
    for row_idx, row in enumerate(data):
        new_row = []
        current_types = []
        
        for col_idx, (value, dtype) in enumerate(zip(row, types_list)):
            if dtype == "IP Address":
                # Validate and split IP address
                if re.match(r'^(\d{1,3}\.){3}\d{1,3}$', str(value)):
                    octets = str(value).split('.')
                    new_row.extend(octets)
                    current_types.extend(["IP Address"] * 4)  # 4 octets
                else:
                    # Invalid IP, treat as string
                    new_row.append(value)
                    current_types.append("String")
            else:
                new_row.append(value)
                current_types.append(dtype)
        
        new_data.append(new_row)
        if row_idx == 0:  # Only update types based on first row
            new_types = current_types
    
    return new_data, new_types

# Completed pipeline
print("Processing data...")
source_out = df.astype(str).values.tolist()

# Split MAC addresses and update types
source_out, updated_types = split_mac(source_out, types_list)

# Split IP addresses and update types again
source_out, final_types = split_ip(source_out, updated_types)

def save_type_information(original_types, final_types):
    type_info = {
        "original_types": original_types,
        "final_types": final_types,
        "encoding_info": {
            "description": "Data type mapping for decoding - ALL INTEGERS CONVERTED TO FLOATS",
            "float_encoding": "Each float becomes 2 RGB pixels (6 bytes total)",
            "mac_encoding": "MAC address split into 2 hex chunks",
            "ip_encoding": "IP address split into 4 octets",
            "integer_note": "All integers converted to floats before encoding",
            "string_encoding": "Hashed to integer, converted to float, then 2 RGB pixels"
        },
        "original_columns": len(original_types),
        "final_columns": len(final_types)
    }
    
    with open(TYPES_FILE, 'w') as f:
        json.dump(type_info, f, indent=2)
    
    print(f" Type information saved to '{TYPES_FILE}'")
    return type_info

# Save the type information to the json file. 
type_info = save_type_information(types_list, final_types)

# Convert to numeric values with FLOAT-FIRST approach
processed = []
for row_idx, row in enumerate(source_out):
    new_row = []
    row_types = final_types + ["String"] * (len(row) - len(final_types))
    
    for val_idx, (val, dtype) in enumerate(zip(row, row_types)):
        try:
            if dtype == "Float":
                float_val = float(val)
                # Convert float to 2 RGB pixels
                rgb_pixel1, rgb_pixel2 = float_to_two_rgb_pixels(float_val)
                new_row.extend([rgb_pixel1, rgb_pixel2])  # Add both RGB pixels
                
            elif dtype == "MAC Address":
                mac_int = int(val, 16)
                mac_float = float(mac_int)
                rgb_pixel1, rgb_pixel2 = float_to_two_rgb_pixels(mac_float)
                new_row.extend([rgb_pixel1, rgb_pixel2])

                
            elif dtype == "IP Address":
                octet_int = int(val)
                octet_float = float(octet_int)
                rgb_pixel1, rgb_pixel2 = float_to_two_rgb_pixels(octet_float)
                new_row.extend([rgb_pixel1, rgb_pixel2])
                
            else:  # String or unknown
                # Convert string to integer based on hash, then to float
                str_hash = abs(hash(str(val))) % 16777215
                str_float = float(str_hash)
                rgb_pixel1, rgb_pixel2 = float_to_two_rgb_pixels(str_float)
                new_row.extend([rgb_pixel1, rgb_pixel2])
                
        except (ValueError, TypeError) as e:
            print(f"Conversion error for value '{val}' (type {dtype}): {e}")
            # For any conversion errors, add two black pixels
            new_row.extend([(0, 0, 0), (0, 0, 0)])

    # Convert all values to RGB (should already be RGB tuples)
    rgb_row = convertLineToRGB(new_row)
    processed.append(rgb_row)
   

os.makedirs(OUTPUT_DIR, exist_ok=True)

def imageCreatorByLine(line, image_id):
 
    if not line:
        # Create a black image if no data
        array = np.zeros((IMAGE_SIZE, IMAGE_SIZE, 3), dtype=np.uint8)
    else:

        array = np.zeros((IMAGE_SIZE, IMAGE_SIZE, 3), dtype=np.uint8)
        rows_per_color = max(1, IMAGE_SIZE // len(line))
        
        # Fill the image with horizontal stripes
        current_row = 0
        for rgb_idx, rgb in enumerate(line):
            # Ensure RGB values are valid
            r, g, b = rgb
            r = max(0, min(255, int(r)))
            g = max(0, min(255, int(g)))
            b = max(0, min(255, int(b)))
            

            for row_offset in range(rows_per_color):
                if current_row + row_offset < IMAGE_SIZE:
                    array[current_row + row_offset, :] = [r, g, b]  # Fill entire row
            
            current_row += rows_per_color
            
            if current_row >= IMAGE_SIZE:
                break
        

        if current_row < IMAGE_SIZE and line:
            last_rgb = line[-1]
            r, g, b = last_rgb
            r = max(0, min(255, int(r)))
            g = max(0, min(255, int(g)))
            b = max(0, min(255, int(b)))
            
            for remaining_row in range(current_row, IMAGE_SIZE):
                array[remaining_row, :] = [r, g, b]
    
    # Create and save image
    img = Image.fromarray(array)
    img.save(os.path.join(OUTPUT_DIR, f"{image_id}.png"))

def imagesCreatorForMultiLines(all_lines):
    #"""Create images for all processed lines"""
    for i, line in enumerate(all_lines):
        imageCreatorByLine(line, i)

# Generate images
print("Creating images...")
imagesCreatorForMultiLines(processed)
#print(f" {len(processed)} images saved to '{OUTPUT_DIR}/'")

# Debug output
#print("\nDebug Information:")
#print(f"Original types: {types_list}")
#print(f"Final types: {final_types}")
#if len(source_out) > 0:
#    print(f"First row length: {len(source_out[0])}")
#     print(f"First row sample: {source_out[0][:5]}...")  # Show first 5 elements
#if len(processed) > 0:
#    print(f"First processed row RGB count: {len(processed[0])}")
#    print(f"First processed row sample: {processed[0][:3]}...")  # Show first 3 RGB tuples

#print(f"\n Type mapping saved to: {TYPES_FILE}")
#print("This file will be used by I2NeT.py for proper decoding!")

# Show the type mapping
#print(f"\n Data Type Analysis:")
#for i, dtype in enumerate(types_list):
#    print(f"  Original Column {i}: {dtype}")
    
#print(f"\n After Splitting (All converted to Float->RGB pairs):")
#for i, dtype in enumerate(final_types):
#    print(f"  Position {i}: {dtype} -> Float -> 2 RGB pixels")

#print(f"\n KEY CHANGE: ALL integers are now converted to floats and encoded as 2 RGB pixels each!")
#print(f"   This ensures consistent float-to-RGB mapping for all numeric data.")
"""
Net2i - Network Data to Image Converter
An interface for converting network data to images.
"""

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
import csv
import ipaddress
from typing import List, Tuple, Optional, Dict, Any


# Global configuration
_CONFIG = {
    'output_dir': 'data',
    'image_size': 150,
    'types_file': 'data_types.json',
    'types_file_ipv6': 'data_types_ipv6.json',
    'decoded_file': 'from_image.csv',
    'clean_existing': True
}


def set_config(output_dir: str = None, 
               image_size: int = None,
               types_file: str = None,
               types_file_ipv6: str = None,
               decoded_file: str = None,
               clean_existing: bool = None):
    """
    Set global configuration for Net2i operations.
    
    Args:
        output_dir: Directory to save generated images
        image_size: Size of output images (width x height). Make sure that your CNN algorithm is tunned to recieve images of this size.
        types_file: JSON file to store IPv4 type information. ipv4 will be processed seperately to ipv6. 
        types_file_ipv6: JSON file to store IPv6 type information
        decoded_file: Output file for decoded data
        clean_existing: Whether to clean existing files
    """
    global _CONFIG
    
    if output_dir is not None:
        _CONFIG['output_dir'] = output_dir
    if image_size is not None:
        _CONFIG['image_size'] = image_size
    if types_file is not None:
        _CONFIG['types_file'] = types_file
    if types_file_ipv6 is not None:
        _CONFIG['types_file_ipv6'] = types_file_ipv6
    if decoded_file is not None:
        _CONFIG['decoded_file'] = decoded_file
    if clean_existing is not None:
        _CONFIG['clean_existing'] = clean_existing


class _Net2iConverter:

    def __init__(self, config: dict):
        self.output_dir = config['output_dir']
        self.image_size = config['image_size']
        self.types_file = config['types_file']
        self.types_file_ipv6 = config['types_file_ipv6']
        self.decoded_file = config['decoded_file']
        self.clean_existing = config['clean_existing']
        
        # Data storage
        self.df = None
        self.original_types = []
        self.final_types = []
        self.processed_data = []
        
    def _clean_existing_files(self):
        #Remove existing output files if clean_existing is True.
        if not self.clean_existing:
            return
            
        files_to_remove = [self.types_file, self.types_file_ipv6, self.decoded_file]
        for file_path in files_to_remove:
            if os.path.exists(file_path):
                os.remove(file_path)
                
        if os.path.exists(self.output_dir):
            shutil.rmtree(self.output_dir)
            
        # Clean IPv4/IPv6 split files
        for file_path in ['ipv4_rows.csv', 'ipv6_rows.csv']:
            if os.path.exists(file_path):
                os.remove(file_path)
    
    def _is_ipv6(self, ip_string: str) -> bool:
        #Check if an IP address is IPv6.
        try:
            return isinstance(ipaddress.ip_address(ip_string.strip()), ipaddress.IPv6Address)
        except ValueError:
            return False
    
    def _is_ipv4(self, ip_string: str) -> bool:
        #Check if an IP address is IPv4.
        try:
            return isinstance(ipaddress.ip_address(ip_string.strip()), ipaddress.IPv4Address)
        except ValueError:
            return False
    
    def _detect_ip_columns(self, df: pd.DataFrame) -> List[int]:
        #Detect which columns contain IP addresses.
        ip_columns = []
        
        for col_idx in range(len(df.columns)):
            column_data = df.iloc[:, col_idx].astype(str)
            ip_count = 0
            total_count = 0
            
            for value in column_data[:min(100, len(column_data))]:  # Check first 100 rows
                value = str(value).strip()
                total_count += 1
                if self._is_ipv4(value) or self._is_ipv6(value):
                    ip_count += 1
            
            # If more than 50% of values are IPs, consider it an IP column
            if total_count > 0 and (ip_count / total_count) > 0.5:
                ip_columns.append(col_idx)
        
        return ip_columns
    
    def _split_ipv4_ipv6_data(self, csv_path: str) -> Tuple[str, str, bool, bool]:
        """
        Split CSV data into IPv4 and IPv6 files.
        
        Returns:
            Tuple of (ipv4_file, ipv6_file, has_ipv4, has_ipv6)
        """
        ipv4_output = 'ipv4_rows.csv' #these are temp csv files. 
        ipv6_output = 'ipv6_rows.csv'
        
        # First, detect IP columns
        temp_df = pd.read_csv(csv_path, header=None, nrows=100)
        ip_columns = self._detect_ip_columns(temp_df)
        
        #print(f"Detected IP columns at positions: {ip_columns}") ##uncomment for debugging
        
        has_ipv4_data = False
        has_ipv6_data = False
        
        with open(csv_path, 'r', newline='') as infile, \
             open(ipv4_output, 'w', newline='') as ipv4_file, \
             open(ipv6_output, 'w', newline='') as ipv6_file:
            
            reader = csv.reader(infile)
            ipv4_writer = csv.writer(ipv4_file)
            ipv6_writer = csv.writer(ipv6_file)
            
            for row in reader:
                if len(row) == 0:
                    continue
                    
                # Check if any IP column contains IPv6
                has_ipv6_in_row = False
                for col_idx in ip_columns:
                    if col_idx < len(row) and self._is_ipv6(row[col_idx]):
                        has_ipv6_in_row = True
                        break
                
                if has_ipv6_in_row:
                    ipv6_writer.writerow(row)
                    has_ipv6_data = True
                else:
                    ipv4_writer.writerow(row)
                    has_ipv4_data = True
        
        #print(f"Data split completed:")
        #print(f"   - IPv4 data: {'Yes' if has_ipv4_data else 'No'}")
        #print(f"   - IPv6 data: {'Yes' if has_ipv6_data else 'No'}")
        
        return ipv4_output, ipv6_output, has_ipv4_data, has_ipv6_data
    
    def _detect_column_types(self, df: pd.DataFrame, is_ipv6: bool = False) -> List[str]:
        #detect column types. This will include detecting mac addresses, ip addresses, port infor, etc
        final_types = []
        
        for col_idx in range(len(df.columns)):
            column_data = df.iloc[:, col_idx].astype(str)
            has_float = False
            has_ipv4 = False
            has_ipv6 = False
            has_mac = False
            has_numeric = False
            
            for value in column_data:
                value = str(value).strip()
                
                if self._is_ipv4(value):
                    has_ipv4 = True
                elif self._is_ipv6(value):
                    has_ipv6 = True
                elif re.match(r'^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$', value):
                    has_mac = True
                elif re.fullmatch(r'-?\d+\.\d+', value):
                    has_numeric = True
                    has_float = True
                elif re.fullmatch(r'-?\d+$', value):
                    has_numeric = True
            
            # Priority: IPv6 > IPv4 > MAC > Numeric (Float) > String
            if has_ipv6:
                final_types.append("IPv6 Address")
            elif has_ipv4:
                final_types.append("IPv4 Address")
            elif has_mac:
                final_types.append("MAC Address")
            elif has_numeric:
                final_types.append("Float")
            else:
                final_types.append("String")
        
        return final_types
    
    def _ipv6_to_rgb_pixels(self, ipv6_str: str) -> List[Tuple[int, int, int]]:

        #IPv6 is 16 bytes, we pad to 18 bytes for 6 RGB pixels. ipv6 will be expanded to the 128-bit representation 
        try:
            ip = ipaddress.IPv6Address(ipv6_str.strip())
            # Get 16 bytes from IPv6 address + pad with 2 zeros for 18 bytes total
            data = list(ip.packed) + [0, 0]
            # Convert to 6 RGB pixels (18 bytes / 3 = 6 pixels)
            rgb_values = [tuple(data[i:i + 3]) for i in range(0, 18, 3)]
            return rgb_values
        except Exception as e:
            print(f"Error converting IPv6 {ipv6_str}: {e}")
            # Return 6 black pixels as fallback
            return [(0, 0, 0)] * 6
    
    def _ipv4_to_rgb_pixels(self, ipv4_str: str) -> List[Tuple[int, int, int]]:
      
        #Convert IPv4 address to RGB pixels (using octet method).  8 RGB pixels via float conversion
        try:
            octets = ipv4_str.strip().split('.')
            rgb_pixels = []
            
            for octet in octets:
                octet_float = float(int(octet))
                rgb_pixel1, rgb_pixel2 = self._float_to_two_rgb_pixels(octet_float)
                rgb_pixels.extend([rgb_pixel1, rgb_pixel2])
            
            return rgb_pixels
        except Exception as e:
            print(f"Error converting IPv4 {ipv4_str}: {e}")
            return [(0, 0, 0)] * 8
    
    def _float_to_two_rgb_pixels(self, float_val: float) -> Tuple[Tuple[int, int, int], Tuple[int, int, int]]:
        #Convert float value to two RGB pixels for lossless transformation.
        try:
            packed_bytes = struct.pack('!f', float_val)
            r1, g1, b1 = packed_bytes[0], packed_bytes[1], packed_bytes[2]
            r2 = packed_bytes[3]
            g2 = 0
            b2 = 0
            return (r1, g1, b1), (r2, g2, b2)
        except Exception as e:
            print(f"Error converting float {float_val}: {e}")
            return (0, 0, 0), (0, 0, 0)
    
    def _convert_line_to_rgb(self, line: List[Any]) -> List[Tuple[int, int, int]]:
        #Convert a line of data to RGB tuples.
        result = []
        for value in line:
            if isinstance(value, (tuple, list)):
                if len(value) == 2 and isinstance(value[0], tuple):
                    result.extend(value)
                elif len(value) >= 3 and isinstance(value[0], int):
                    result.append(tuple(value[:3]))
                elif isinstance(value, list) and len(value) > 0 and isinstance(value[0], tuple):
                    result.extend(value)
                else:
                    result.append((0, 0, 0))
            else:
                result.append((0, 0, 0))
        return result
    
    def _split_mac(self, data: List[List], types_list: List[str]) -> Tuple[List[List], List[str]]:
        #Split MAC addresses into chunks for processing into RGB
        new_data = []
        new_types = []
        
        for row_idx, row in enumerate(data):
            new_row = []
            current_types = []
            
            for col_idx, (value, dtype) in enumerate(zip(row, types_list)):
                if dtype == "MAC Address":
                    mac = str(value).replace(":", "")
                    if len(mac) >= 12:
                        chunk1 = mac[:6]
                        chunk2 = mac[6:12]
                        new_row.extend([chunk1, chunk2])
                        current_types.extend(["MAC Address", "MAC Address"])
                    else:
                        new_row.append(value)
                        current_types.append("String")
                else:
                    new_row.append(value)
                    current_types.append(dtype)
            
            new_data.append(new_row)
            if row_idx == 0:
                new_types = current_types
        
        return new_data, new_types
    
    def _split_ip(self, data: List[List], types_list: List[str]) -> Tuple[List[List], List[str]]:
        #Split IP addresses - IPv4 into octets
        new_data = []
        new_types = []
        
        for row_idx, row in enumerate(data):
            new_row = []
            current_types = []
            
            for col_idx, (value, dtype) in enumerate(zip(row, types_list)):
                if dtype == "IPv4 Address":
                    if self._is_ipv4(str(value)):
                        octets = str(value).split('.')
                        new_row.extend(octets)
                        current_types.extend(["IPv4 Address"] * 4)
                    else:
                        new_row.append(value)
                        current_types.append("String")
                elif dtype == "IPv6 Address":
                    # IPv6 addresses are kept as single values for custom processing
                    new_row.append(value)
                    current_types.append("IPv6 Address")
                else:
                    new_row.append(value)
                    current_types.append(dtype)
            
            new_data.append(new_row)
            if row_idx == 0:
                new_types = current_types
        
        return new_data, new_types
    
    def _save_type_information(self, is_ipv6: bool = False):
        #Save type information to appropriate JSON file. This will be used again  in the I2NeT
        types_file = self.types_file_ipv6 if is_ipv6 else self.types_file
        
        type_info = {
            "ip_version": "IPv6" if is_ipv6 else "IPv4",
            "original_types": self.original_types,
            "final_types": self.final_types,
            "encoding_info": {
                "description": f"Data type mapping for decoding - {'IPv6' if is_ipv6 else 'IPv4'} version",
                "float_encoding": "Each float becomes 2 RGB pixels (6 bytes total)",
                "mac_encoding": "MAC address split into 2 hex chunks",
                "ipv4_encoding": "IPv4 address split into 4 octets, each becomes 2 RGB pixels",
                "ipv6_encoding": "IPv6 address becomes 6 RGB pixels (16 bytes + 2 padding)",
                "integer_note": "All integers converted to floats before encoding",
                "string_encoding": "Hashed to integer, converted to float, then 2 RGB pixels"
            },
            "original_columns": len(self.original_types),
            "final_columns": len(self.final_types)
        }
        
        with open(types_file, 'w') as f:
            json.dump(type_info, f, indent=2)
        
        #print(f"Type information saved to '{types_file}'")
        return type_info
    
    def _process_data(self, source_out: List[List], is_ipv6: bool = False) -> List[List[Tuple[int, int, int]]]:
       #Process data and convert to RGB pixels
        processed = []
        
        for row_idx, row in enumerate(source_out):
            new_row = []
            row_types = self.final_types + ["String"] * (len(row) - len(self.final_types))
            
            for val_idx, (val, dtype) in enumerate(zip(row, row_types)):
                try:
                    if dtype == "Float":
                        float_val = float(val)
                        rgb_pixel1, rgb_pixel2 = self._float_to_two_rgb_pixels(float_val)
                        new_row.extend([rgb_pixel1, rgb_pixel2])
                        
                    elif dtype == "MAC Address":
                        mac_int = int(val, 16)
                        mac_float = float(mac_int)
                        rgb_pixel1, rgb_pixel2 = self._float_to_two_rgb_pixels(mac_float)
                        new_row.extend([rgb_pixel1, rgb_pixel2])
                        
                    elif dtype == "IPv4 Address":
                        octet_int = int(val)
                        octet_float = float(octet_int)
                        rgb_pixel1, rgb_pixel2 = self._float_to_two_rgb_pixels(octet_float)
                        new_row.extend([rgb_pixel1, rgb_pixel2])
                        
                    elif dtype == "IPv6 Address":
                        # Convert IPv6 to 6 RGB pixels
                        ipv6_pixels = self._ipv6_to_rgb_pixels(str(val))
                        new_row.extend(ipv6_pixels)
                        
                    else:  # String or unknown
                        str_hash = abs(hash(str(val))) % 16777215
                        str_float = float(str_hash)
                        rgb_pixel1, rgb_pixel2 = self._float_to_two_rgb_pixels(str_float)
                        new_row.extend([rgb_pixel1, rgb_pixel2])
                        
                except (ValueError, TypeError) as e:
                    print(f"Conversion error for value '{val}' (type {dtype}): {e}")
                    if dtype == "IPv6 Address":
                        new_row.extend([(0, 0, 0)] * 6)  # 6 black pixels for IPv6
                    else:
                        new_row.extend([(0, 0, 0), (0, 0, 0)])  # 2 black pixels for others
            
            rgb_row = self._convert_line_to_rgb(new_row)
            processed.append(rgb_row)
        
        return processed
    
    def _create_image_from_line(self, line: List[Tuple[int, int, int]], image_id: int, prefix: str = ""):
        #Create an image from a single line of RGB data.
        if not line:
            array = np.zeros((self.image_size, self.image_size, 3), dtype=np.uint8)
        else:
            array = np.zeros((self.image_size, self.image_size, 3), dtype=np.uint8)
            rows_per_color = max(1, self.image_size // len(line))
            
            current_row = 0
            for rgb_idx, rgb in enumerate(line):
                r, g, b = rgb
                r = max(0, min(255, int(r)))
                g = max(0, min(255, int(g)))
                b = max(0, min(255, int(b)))
                
                for row_offset in range(rows_per_color):
                    if current_row + row_offset < self.image_size:
                        array[current_row + row_offset, :] = [r, g, b]
                
                current_row += rows_per_color
                
                if current_row >= self.image_size:
                    break
            
            if current_row < self.image_size and line:
                last_rgb = line[-1]
                r, g, b = last_rgb
                r = max(0, min(255, int(r)))
                g = max(0, min(255, int(g)))
                b = max(0, min(255, int(b)))
                
                for remaining_row in range(current_row, self.image_size):
                    array[remaining_row, :] = [r, g, b]
        
        filename = f"{prefix}{image_id}.png" if prefix else f"{image_id}.png"
        img = Image.fromarray(array)
        img.save(os.path.join(self.output_dir, filename))
    
    def _create_all_images(self, prefix: str = ""):
        #Create images for all processed lines. 
        os.makedirs(self.output_dir, exist_ok=True)
        
        for i, line in enumerate(self.processed_data):
            self._create_image_from_line(line, i, prefix)
        
        #print(f"{len(self.processed_data)} images saved to '{self.output_dir}/' with prefix '{prefix}'")
    
    def _process_single_dataset(self, csv_path: str, is_ipv6: bool = False, prefix: str = "") -> Dict[str, Any]:
        #Process a single dataset (IPv4 or IPv6).
        #print(f"\nProcessing {'IPv6' if is_ipv6 else 'IPv4'} dataset: {csv_path}")
        
        # Load CSV
        self.df = pd.read_csv(csv_path, header=None)
        #print(f"Loaded CSV with shape: {self.df.shape}")
        
        # Detect column types
        self.original_types = self._detect_column_types(self.df, is_ipv6)
        #print(f"Detected types: {self.original_types}")
        
        # Convert to string data
        source_out = self.df.astype(str).values.tolist()
        
        # Split MAC addresses and update types
        source_out, updated_types = self._split_mac(source_out, self.original_types)
        
        # Split IP addresses and update types
        source_out, self.final_types = self._split_ip(source_out, updated_types)
        
        # Save type information
        type_info = self._save_type_information(is_ipv6)
        
        # Process data to RGB pixels
        print("Processing data...")
        self.processed_data = self._process_data(source_out, is_ipv6)
        
        # Create images
        print("Creating images...")
        self._create_all_images(prefix)
        
        return {
            "input_file": csv_path,
            "ip_version": "IPv6" if is_ipv6 else "IPv4",
            "original_shape": self.df.shape,
            "original_types": self.original_types,
            "final_types": self.final_types,
            "num_images": len(self.processed_data),
            "type_info": type_info
        }
    
    def convert(self, csv_path: str, **kwargs) -> Dict[str, Any]:
        
        #Main function to load CSV, auto-detect IP versions, and convert to images.
        #print(f"Loading and analyzing CSV: {csv_path}")
        
        # Clean existing files
        self._clean_existing_files()
        
        # Split data into IPv4 and IPv6
        ipv4_file, ipv6_file, has_ipv4, has_ipv6 = self._split_ipv4_ipv6_data(csv_path)
        
        results = {
            "input_file": csv_path,
            "output_dir": self.output_dir,
            "image_size": self.image_size,
            "has_ipv4": has_ipv4,
            "has_ipv6": has_ipv6,
            "ipv4_results": None,
            "ipv6_results": None
        }
        
        # Process IPv4 data if present
        if has_ipv4 and os.path.exists(ipv4_file):
            ipv4_results = self._process_single_dataset(ipv4_file, is_ipv6=False, prefix="ipv4_")
            results["ipv4_results"] = ipv4_results
            #print(f" IPv4 processing completed - {ipv4_results['num_images']} images generated")
        
        # Process IPv6 data if present
        if has_ipv6 and os.path.exists(ipv6_file):
            ipv6_results = self._process_single_dataset(ipv6_file, is_ipv6=True, prefix="ipv6_")
            results["ipv6_results"] = ipv6_results
            #print(f" IPv6 processing completed - {ipv6_results['num_images']} images generated")
        
        # Summary
        total_images = 0
        if results["ipv4_results"]:
            total_images += results["ipv4_results"]["num_images"]
        if results["ipv6_results"]:
            total_images += results["ipv6_results"]["num_images"]
        
        results["total_images"] = total_images
        
        ##print(f"\n🎉 Pipeline completed successfully!")
        #print(f"   - Total images generated: {total_images}")
        #print(f"   - IPv4 data processed: {'Yes' if has_ipv4 else 'No'}")
        #print(f"   - IPv6 data processed: {'Yes' if has_ipv6 else 'No'}")
        print(f"   - Images saved to: {self.output_dir}")
        #if has_ipv4:
        #    print(f"   - IPv4 type mapping: {self.types_file}")
        #if has_ipv6:
        #    print(f"   - IPv6 type mapping: {self.types_file_ipv6}")
        
        return results


def load_csv(csv_path: str, **kwargs) -> str:

    #Load CSV file and return the path for encoding.
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV file not found: {csv_path}")
    
    print(f"CSV file loaded: {csv_path}")
    return csv_path


def encode(csv_path: str, 
           output_dir: str = None,
           image_size: int = None,
           **kwargs) -> Dict[str, Any]:
    # Create config for this conversion
    config = _CONFIG.copy()
    
    # Override with local parameters
    if output_dir is not None:
        config['output_dir'] = output_dir
    if image_size is not None:
        config['image_size'] = image_size
    
    # Create converter and run conversion
    converter = _Net2iConverter(config)
    return converter.convert(csv_path, **kwargs)


# Convenience aliases for backward compatibility
def convert_csv(csv_path: str, **kwargs) -> Dict[str, Any]:
    
    return encode(csv_path, **kwargs)


# Usage examples and help
def help():
    """Print usage examples."""
    print("""
Net2i - Network Data to Image Converter
========================================

Simple Usage:
    import Net2i
    
    # Basic conversion
    results = Net2i.encode(Net2i.load_csv('source_in2.csv'))
    
    # With custom output directory and image size
    results = Net2i.encode('source_in2.csv', output_dir='my_images', image_size=200)

Global Configuration:
    # Set global defaults
    Net2i.set_config(output_dir='data_images', image_size=150, clean_existing=True)
    
    # Then use simple calls
    results = Net2i.encode(Net2i.load_csv('source_in2.csv'))

Features:
    - Automatic IPv4/IPv6 detection and separation
    - Lossless data encoding to images
    - Support for MAC addresses, floats, integers, strings
    - Type information saved for decoding
    - Configurable output directory and image size

Results Structure:
    {
        'input_file': 'source_in2.csv',
        ''output_dir': 'data_images',
        'image_size': 150,
        'has_ipv4': True,
        'has_ipv6': False,
        'total_images': 42,
        'ipv4_results': {...},
        'ipv6_results': None
    }

Output Files:
    - Images: saved to output_dir/ with prefixes 'ipv4_' and 'ipv6_'
    - Type info: data_types.json (IPv4) and data_types_ipv6.json (IPv6)
    - Split data: ipv4_rows.csv and ipv6_rows.csv (temporary)

Supported Data Types:
    - IPv4 Address: Detected automatically, split into octets
    - IPv6 Address: Detected automatically, encoded as 6 RGB pixels
    - MAC Address: Detected by pattern, split into hex chunks
    - Float: Numeric values with decimals
    - Integer: Whole numbers (converted to float for processing)
    - String: Text data (hashed for consistent encoding)

For more information, visit: https://github.com/yourusername/Net2i
    """)


def show_config():
    """Display current global configuration."""
    print("Current Net2i Configuration:")
    print("============================")
    for key, value in _CONFIG.items():
        print(f"  {key}: {value}")


def reset_config():
    """Reset configuration to defaults."""
    global _CONFIG
    _CONFIG = {
        'output_dir': 'data',
        'image_size': 150,
        'types_file': 'data_types.json',
        'types_file_ipv6': 'data_types_ipv6.json',
        'decoded_file': 'from_image.csv',
        'clean_existing': True
    }
    print("Configuration reset to defaults")


# Main interface functions
__all__ = [
    'load_csv',
    'encode', 
    'convert_csv',
    'set_config',
    'show_config',
    'reset_config',
    'help'
]


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python Net2i.py <csv_file> [output_dir] [image_size]")
        print("Example: python Net2i.py source_in2.csv data_images 150")
        help()
        sys.exit(1)
    
    csv_file = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None
    image_size = int(sys.argv[3]) if len(sys.argv) > 3 else None
    
    print(f"Processing {csv_file}...")
    results = encode(load_csv(csv_file), output_dir=output_dir, image_size=image_size)
    
    #print("\nConversion completed successfully!")
    #print(f"Total images generated: {results['total_images']}")
    #print(f"Output directory: {results['output_dir']}")
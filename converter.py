"""
NeT2i Converter Module
Converts CSV data to images by encoding different data types as RGB pixels.
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
from typing import List, Tuple, Optional, Dict, Any


class NeT2iConverter:
    """Main converter class for CSV to image transformation."""
    
    def __init__(self, 
                 output_dir: str = "data", 
                 image_size: int = 150,
                 types_file: str = "data_types.json",
                 decoded_file: str = "from_image.csv",
                 clean_existing: bool = True):
        """
        Initialize the NeT2i converter.
        
        Args:
            output_dir: Directory to save generated images
            image_size: Size of output images (width x height)
            types_file: JSON file to store type information
            decoded_file: Output file for decoded data
            clean_existing: Whether to clean existing files
        """
        self.output_dir = output_dir
        self.image_size = image_size
        self.types_file = types_file
        self.decoded_file = decoded_file
        self.clean_existing = clean_existing
        
        # Data storage
        self.df = None
        self.original_types = []
        self.final_types = []
        self.processed_data = []
        
    def _clean_existing_files(self):
        """Remove existing output files if clean_existing is True."""
        if not self.clean_existing:
            return
            
        files_to_remove = [self.types_file, self.decoded_file]
        for file_path in files_to_remove:
            if os.path.exists(file_path):
                os.remove(file_path)
                
        if os.path.exists(self.output_dir):
            shutil.rmtree(self.output_dir)
    
    def _detect_column_types(self, df: pd.DataFrame) -> List[str]:
        """
        Detect column types in the dataframe.
        Converts non-network address fields to floats.
        
        Args:
            df: Input dataframe
            
        Returns:
            List of detected types
        """
        final_types = []
        
        for col_idx in range(len(df.columns)):
            column_data = df.iloc[:, col_idx].astype(str)
            has_float = False
            has_ip = False
            has_mac = False
            has_numeric = False
            
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
            
            # Priority: IP > MAC > Numeric (Float) > String
            # All integers are treated as floats
            if has_ip:
                final_types.append("IP Address")
            elif has_mac:
                final_types.append("MAC Address")
            elif has_numeric:
                final_types.append("Float")
            else:
                final_types.append("String")
        
        return final_types
    
    def _float_to_two_rgb_pixels(self, float_val: float) -> Tuple[Tuple[int, int, int], Tuple[int, int, int]]:
        """
        Convert float value to two RGB pixels for lossless transformation.
        
        Args:
            float_val: Float value to convert
            
        Returns:
            Tuple of two RGB pixel tuples
        """
        try:
            # Pack float into 4 bytes
            packed_bytes = struct.pack('!f', float_val)
            r1, g1, b1 = packed_bytes[0], packed_bytes[1], packed_bytes[2]
            r2 = packed_bytes[3]  # Last byte of the float
            g2 = 0  # Padding
            b2 = 0  # Padding
            
            return (r1, g1, b1), (r2, g2, b2)
        except Exception as e:
            print(f"Error converting float {float_val}: {e}")
            return (0, 0, 0), (0, 0, 0)
    
    def _convert_line_to_rgb(self, line: List[Any]) -> List[Tuple[int, int, int]]:
        """Convert a line of data to RGB tuples."""
        result = []
        for value in line:
            if isinstance(value, (tuple, list)):
                if len(value) == 2 and isinstance(value[0], tuple):
                    # Two RGB tuples
                    result.extend(value)
                elif len(value) == 3:
                    # Single RGB tuple
                    result.append(value)
                else:
                    result.append((0, 0, 0))
            else:
                result.append((0, 0, 0))
        return result
    
    def _split_mac(self, data: List[List], types_list: List[str]) -> Tuple[List[List], List[str]]:
        """Split MAC addresses into chunks."""
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
        """Split IP addresses into octets."""
        new_data = []
        new_types = []
        
        for row_idx, row in enumerate(data):
            new_row = []
            current_types = []
            
            for col_idx, (value, dtype) in enumerate(zip(row, types_list)):
                if dtype == "IP Address":
                    if re.match(r'^(\d{1,3}\.){3}\d{1,3}$', str(value)):
                        octets = str(value).split('.')
                        new_row.extend(octets)
                        current_types.extend(["IP Address"] * 4)
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
    
    def _save_type_information(self):
        """Save type information to JSON file."""
        type_info = {
            "original_types": self.original_types,
            "final_types": self.final_types,
            "encoding_info": {
                "description": "Data type mapping for decoding - ALL INTEGERS CONVERTED TO FLOATS",
                "float_encoding": "Each float becomes 2 RGB pixels (6 bytes total)",
                "mac_encoding": "MAC address split into 2 hex chunks",
                "ip_encoding": "IP address split into 4 octets",
                "integer_note": "All integers converted to floats before encoding",
                "string_encoding": "Hashed to integer, converted to float, then 2 RGB pixels"
            },
            "original_columns": len(self.original_types),
            "final_columns": len(self.final_types)
        }
        
        with open(self.types_file, 'w') as f:
            json.dump(type_info, f, indent=2)
        
        print(f"Type information saved to '{self.types_file}'")
        return type_info
    
    def _process_data(self, source_out: List[List]) -> List[List[Tuple[int, int, int]]]:
        """Process data and convert to RGB pixels."""
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
                        
                    elif dtype == "IP Address":
                        octet_int = int(val)
                        octet_float = float(octet_int)
                        rgb_pixel1, rgb_pixel2 = self._float_to_two_rgb_pixels(octet_float)
                        new_row.extend([rgb_pixel1, rgb_pixel2])
                        
                    else:  # String or unknown
                        str_hash = abs(hash(str(val))) % 16777215
                        str_float = float(str_hash)
                        rgb_pixel1, rgb_pixel2 = self._float_to_two_rgb_pixels(str_float)
                        new_row.extend([rgb_pixel1, rgb_pixel2])
                        
                except (ValueError, TypeError) as e:
                    print(f"Conversion error for value '{val}' (type {dtype}): {e}")
                    new_row.extend([(0, 0, 0), (0, 0, 0)])
            
            rgb_row = self._convert_line_to_rgb(new_row)
            processed.append(rgb_row)
        
        return processed
    
    def _create_image_from_line(self, line: List[Tuple[int, int, int]], image_id: int):
        """Create an image from a single line of RGB data."""
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
            
            # Fill remaining rows with last color
            if current_row < self.image_size and line:
                last_rgb = line[-1]
                r, g, b = last_rgb
                r = max(0, min(255, int(r)))
                g = max(0, min(255, int(g)))
                b = max(0, min(255, int(b)))
                
                for remaining_row in range(current_row, self.image_size):
                    array[remaining_row, :] = [r, g, b]
        
        img = Image.fromarray(array)
        img.save(os.path.join(self.output_dir, f"{image_id}.png"))
    
    def _create_all_images(self):
        """Create images for all processed lines."""
        os.makedirs(self.output_dir, exist_ok=True)
        
        for i, line in enumerate(self.processed_data):
            self._create_image_from_line(line, i)
        
        print(f"{len(self.processed_data)} images saved to '{self.output_dir}/'")
    
    def load_csv(self, csv_path: str, **kwargs) -> Dict[str, Any]:
        """
        Main function to load CSV and convert to images.
        
        Args:
            csv_path: Path to the input CSV file
            **kwargs: Additional arguments for pd.read_csv
            
        Returns:
            Dictionary with conversion results and metadata
        """
        print(f"Loading CSV: {csv_path}")
        
        # Clean existing files
        self._clean_existing_files()
        
        # Load CSV
        self.df = pd.read_csv(csv_path, header=None, **kwargs)
        print(f"Loaded CSV with shape: {self.df.shape}")
        
        # Detect column types
        self.original_types = self._detect_column_types(self.df)
        print(f"Detected types: {self.original_types}")
        
        # Convert to string data
        source_out = self.df.astype(str).values.tolist()
        
        # Split MAC addresses and update types
        source_out, updated_types = self._split_mac(source_out, self.original_types)
        
        # Split IP addresses and update types
        source_out, self.final_types = self._split_ip(source_out, updated_types)
        
        # Save type information
        type_info = self._save_type_information()
        
        # Process data to RGB pixels
        print("Processing data...")
        self.processed_data = self._process_data(source_out)
        
        # Create images
        print("Creating images...")
        self._create_all_images()
        
        # Return results
        results = {
            "input_file": csv_path,
            "output_dir": self.output_dir,
            "types_file": self.types_file,
            "original_shape": self.df.shape,
            "original_types": self.original_types,
            "final_types": self.final_types,
            "num_images": len(self.processed_data),
            "image_size": self.image_size,
            "type_info": type_info
        }
        
        print(f"\nConversion completed successfully!")
        print(f"- Generated {results['num_images']} images")
        print(f"- Images saved to: {self.output_dir}")
        print(f"- Type mapping saved to: {self.types_file}")
        
        return results


# Convenience functions for direct use
_default_converter = None

def load_csv(csv_path: str, 
             output_dir: str = "data",
             image_size: int = 150,
             types_file: str = "data_types.json",
             decoded_file: str = "from_image.csv",
             clean_existing: bool = True,
             **kwargs) -> Dict[str, Any]:
    """
    Convenience function to load CSV and convert to images.
    
    Args:
        csv_path: Path to the input CSV file
        output_dir: Directory to save generated images
        image_size: Size of output images (width x height)
        types_file: JSON file to store type information
        decoded_file: Output file for decoded data
        clean_existing: Whether to clean existing files
        **kwargs: Additional arguments for pd.read_csv
        
    Returns:
        Dictionary with conversion results and metadata
        
    Example:
        >>> import NeT2i.converter as converter
        >>> results = converter.load_csv('source_in2.csv')
        >>> print(f"Generated {results['num_images']} images")
    """
    global _default_converter
    
    _default_converter = NeT2iConverter(
        output_dir=output_dir,
        image_size=image_size,
        types_file=types_file,
        decoded_file=decoded_file,
        clean_existing=clean_existing
    )
    
    return _default_converter.load_csv(csv_path, **kwargs)


def get_converter() -> Optional[NeT2iConverter]:
    """Get the current default converter instance."""
    return _default_converter


# Aliases for backward compatibility
def convert_csv_to_images(csv_path: str, **kwargs) -> Dict[str, Any]:
    """Alias for load_csv function."""
    return load_csv(csv_path, **kwargs)
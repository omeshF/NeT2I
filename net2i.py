"""
NeT2i Converter Module (with IPv6 support) 
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
import ipaddress
import csv

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


class NeT2iConverter:
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
        if not self.clean_existing:
            return
        files_to_remove = [self.types_file, self.types_file_ipv6, self.decoded_file]
        for file_path in files_to_remove:
            if os.path.exists(file_path):
                os.remove(file_path)
        if os.path.exists(self.output_dir):
            shutil.rmtree(self.output_dir)
        for file_path in ['ipv4_rows.csv', 'ipv6_rows.csv']:
            if os.path.exists(file_path):
                os.remove(file_path)

    def _is_ipv6(self, ip_string: str) -> bool:
        try:
            return isinstance(ipaddress.ip_address(ip_string.strip()), ipaddress.IPv6Address)
        except ValueError:
            return False

    def _is_ipv4(self, ip_string: str) -> bool:
        try:
            return isinstance(ipaddress.ip_address(ip_string.strip()), ipaddress.IPv4Address)
        except ValueError:
            return False

    def _detect_ip_columns(self, df: pd.DataFrame) -> List[int]:
        ip_columns = []
        for col_idx in range(len(df.columns)):
            column_data = df.iloc[:, col_idx].astype(str)
            ip_count = 0
            total_count = 0
            for value in column_data[:min(100, len(column_data))]:
                value = str(value).strip()
                if value == 'nan' or value == '':
                    continue
                total_count += 1
                if self._is_ipv4(value) or self._is_ipv6(value):
                    ip_count += 1
            if total_count > 0 and (ip_count / total_count) > 0.5:
                ip_columns.append(col_idx)
        return ip_columns

    def _split_ipv4_ipv6_data(self, csv_path: str) -> Tuple[str, str, bool, bool]:
        ipv4_output = 'ipv4_rows.csv'
        ipv6_output = 'ipv6_rows.csv'
        has_ipv4_data = False
        has_ipv6_data = False

        temp_df = pd.read_csv(csv_path, header=None, nrows=100)
        ip_columns = self._detect_ip_columns(temp_df)

        with open(csv_path, 'r', newline='') as infile, \
             open(ipv4_output, 'w', newline='') as ipv4_file, \
             open(ipv6_output, 'w', newline='') as ipv6_file:

            reader = csv.reader(infile)
            ipv4_writer = csv.writer(ipv4_file)
            ipv6_writer = csv.writer(ipv6_file)

            for row in reader:
                if not row:
                    continue
                has_ipv6_in_row = any(self._is_ipv6(row[col]) for col in ip_columns if col < len(row))
                if has_ipv6_in_row:
                    ipv6_writer.writerow(row)
                    has_ipv6_data = True
                else:
                    ipv4_writer.writerow(row)
                    has_ipv4_data = True

        return ipv4_output, ipv6_output, has_ipv4_data, has_ipv6_data

    def _detect_column_types(self, df: pd.DataFrame, is_ipv6: bool = False) -> List[str]:
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
                if value == 'nan' or value == '':
                    continue
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
        try:
            ip = ipaddress.IPv6Address(ipv6_str.strip())
            data = list(ip.packed) + [0, 0]  # 16 bytes + 2 padding = 18 bytes
            return [tuple(data[i:i+3]) for i in range(0, 18, 3)]
        except Exception:
            return [(0, 0, 0)] * 6

    def _float_to_two_rgb_pixels(self, float_val: float) -> Tuple[Tuple[int, int, int], Tuple[int, int, int]]:
        try:
            packed_bytes = struct.pack('!f', float_val)
            r1, g1, b1 = packed_bytes[0], packed_bytes[1], packed_bytes[2]
            r2, g2, b2 = packed_bytes[3], 0, 0  # FIX: Define g2 and b2 properly
            return (r1, g1, b1), (r2, g2, b2)
        except Exception:
            return (0, 0, 0), (0, 0, 0)

    def _process_data(self, source_out: List[List], is_ipv6: bool = False) -> List[List[Tuple[int, int, int]]]:
        processed = []
        for row in source_out:
            new_row = []
            # FIX: Use the correct final_types for each row
            for val, dtype in zip(row, self.final_types):
                try:
                    if dtype == "IPv6 Address":
                        new_row.extend(self._ipv6_to_rgb_pixels(str(val)))
                    elif dtype == "IPv4 Address":
                        # FIX: Handle IPv4 octets properly
                        octet_val = int(val)
                        rgb_pixel1, rgb_pixel2 = self._float_to_two_rgb_pixels(float(octet_val))
                        new_row.extend([rgb_pixel1, rgb_pixel2])
                    elif dtype == "MAC Address":
                        # FIX: Handle MAC address hex chunks properly
                        mac_int = int(val, 16)
                        rgb_pixel1, rgb_pixel2 = self._float_to_two_rgb_pixels(float(mac_int))
                        new_row.extend([rgb_pixel1, rgb_pixel2])
                    elif dtype == "Float":
                        float_val = float(val)
                        rgb_pixel1, rgb_pixel2 = self._float_to_two_rgb_pixels(float_val)
                        new_row.extend([rgb_pixel1, rgb_pixel2])
                    else:  # String
                        hash_val = abs(hash(str(val))) % 16777215
                        rgb_pixel1, rgb_pixel2 = self._float_to_two_rgb_pixels(float(hash_val))
                        new_row.extend([rgb_pixel1, rgb_pixel2])
                except Exception as e:
                    print(f"Error processing {val} as {dtype}: {e}")
                    if dtype == "IPv6 Address":
                        new_row.extend([(0, 0, 0)] * 6)
                    else:
                        new_row.extend([(0, 0, 0), (0, 0, 0)])
            processed.append(new_row)
        return processed

    def _save_type_information(self, is_ipv6: bool = False):
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

    def _create_image_from_line(self, line: List[Tuple[int, int, int]], image_id: int, prefix: str = ""):
        # Create horizontal stripes like the original version
        array = np.zeros((self.image_size, self.image_size, 3), dtype=np.uint8)
        
        if len(line) == 0:
            # Create a default gray image if no data
            array = np.full((self.image_size, self.image_size, 3), 128, dtype=np.uint8)
        else:
            # Calculate how many rows each color should occupy
            rows_per_color = max(1, self.image_size // len(line))
            current_row = 0
            
            for rgb in line:
                r, g, b = map(lambda x: max(0, min(255, int(x))), rgb)
                
                # Fill the allocated rows for this color
                for _ in range(rows_per_color):
                    if current_row < self.image_size:
                        array[current_row, :] = [r, g, b]  # Fill entire row
                        current_row += 1
            
            # Fill any remaining rows with the last color
            if current_row < self.image_size and len(line) > 0:
                last_rgb = line[-1]
                r, g, b = map(lambda x: max(0, min(255, int(x))), last_rgb)
                while current_row < self.image_size:
                    array[current_row, :] = [r, g, b]
                    current_row += 1
        
        filename = f"{prefix}{image_id}.png"
        Image.fromarray(array).save(os.path.join(self.output_dir, filename))

    def _create_all_images(self, prefix: str = ""):
        os.makedirs(self.output_dir, exist_ok=True)
        for i, line in enumerate(self.processed_data):
            self._create_image_from_line(line, i, prefix)

    def _split_mac(self, data: List[List], types_list: List[str]) -> Tuple[List[List], List[str]]:
        # FIX: Handle the types_list properly - it should be a single list, not list of lists
        new_data = []
        new_types = []
        
        for row in data:
            new_row = []
            for val, dtype in zip(row, types_list):
                if dtype == "MAC Address":
                    mac = str(val).replace(":", "")
                    if len(mac) >= 12:
                        new_row.extend([mac[:6], mac[6:12]])
                        new_types.extend(["MAC Address", "MAC Address"])
                    else:
                        new_row.append(val)
                        new_types.append("String")
                else:
                    new_row.append(val)
                    new_types.append(dtype)
            new_data.append(new_row)
        
        return new_data, new_types

    def _split_ip(self, data: List[List], types_list: List[str]) -> Tuple[List[List], List[str]]:
        # FIX: Handle the types_list properly
        new_data = []
        new_types = []
        
        for row in data:
            new_row = []
            for val, dtype in zip(row, types_list):
                if dtype == "IPv4 Address":
                    octets = str(val).split('.')
                    if len(octets) == 4:
                        new_row.extend(octets)
                        new_types.extend(["IPv4 Address"] * 4)
                    else:
                        new_row.append(val)
                        new_types.append("String")
                elif dtype == "IPv6 Address":
                    new_row.append(val)
                    new_types.append("IPv6 Address")
                else:
                    new_row.append(val)
                    new_types.append(dtype)
            new_data.append(new_row)
        
        return new_data, new_types

    def _process_single_dataset(self, csv_path: str, is_ipv6: bool = False, prefix: str = "") -> Dict[str, Any]:
        self.df = pd.read_csv(csv_path, header=None)
        self.original_types = self._detect_column_types(self.df, is_ipv6)
        source_out = self.df.astype(str).values.tolist()
        
        # FIX: Handle the splitting properly
        source_out, updated_types = self._split_mac(source_out, self.original_types)
        source_out, self.final_types = self._split_ip(source_out, updated_types)
        
        self._save_type_information(is_ipv6)
        self.processed_data = self._process_data(source_out, is_ipv6)
        self._create_all_images(prefix)
        
        return {
            "input_file": csv_path,
            "ip_version": "IPv6" if is_ipv6 else "IPv4",
            "original_shape": self.df.shape,
            "original_types": self.original_types,
            "final_types": self.final_types,
            "num_images": len(self.processed_data)
        }

    def convert(self, csv_path: str, **kwargs) -> Dict[str, Any]:
        self._clean_existing_files()
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

        if has_ipv4:
            results["ipv4_results"] = self._process_single_dataset(ipv4_file, is_ipv6=False, prefix="ipv4_")

        if has_ipv6:
            results["ipv6_results"] = self._process_single_dataset(ipv6_file, is_ipv6=True, prefix="ipv6_")

        total_images = sum([
            results["ipv4_results"]["num_images"] if has_ipv4 else 0,
            results["ipv6_results"]["num_images"] if has_ipv6 else 0
        ])

        results["total_images"] = total_images
        print(f"Conversion completed successfully!\nTotal images generated: {total_images}")
        return results


def encode(csv_path: str, output_dir: str = None, image_size: int = None, **kwargs) -> Dict[str, Any]:
    config = _CONFIG.copy()
    if output_dir:
        config['output_dir'] = output_dir
    if image_size:
        config['image_size'] = image_size

    converter = NeT2iConverter(config)
    return converter.convert(csv_path, **kwargs)


def load_csv(csv_path: str, **kwargs) -> str:
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV file not found: {csv_path}")
    return csv_path


__all__ = ['encode', 'load_csv', 'set_config']
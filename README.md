# Net2i (NeT2I) - Network Data to Image Converter

A Python library for converting network traffic data (CSV format) into RGB images for machine learning applications, particularly CNNs. Net2i uses lossless encoding to preserve all data information while creating CNN-ready image datasets from network traffic logs.

> **🔄 Companion Tool**: Use [I2NeT](https://github.com/omeshF/I2NeT) to decode images back to CSV format

## 🚀 Features

- **🔍 Automatic IP Version Detection**: Separates IPv4 and IPv6 data automatically
- **💎 Lossless Data Encoding**: Converts network data to RGB pixels without information loss
- **🌐 Multiple Data Type Support**: Handles IP addresses, MAC addresses, floats, integers, and strings
- **🧠 CNN-Ready Output**: Generates images optimized for convolutional neural networks
- **📋 Type Information Preservation**: Saves encoding metadata for data reconstruction via I2NeT
- **⚙️ Configurable Parameters**: Customizable image size and output directories
- **🔀 Mixed IP Version Support**: Processes IPv4 and IPv6 data in the same dataset

## 📦 Installation

```bash
pip install pandas numpy pillow
```

**Requirements:**
- Python 3.9+
- pandas
- numpy
- Pillow (PIL)
- ipaddress (built-in)

## 🚀 Quick Start

### Basic Usage
```python
import Net2i

# Convert network traffic CSV to images
results = Net2i.encode('network_traffic.csv')
print(f"Generated {results['total_images']} images in '{results['output_dir']}'")
```

### With Custom Configuration
```python
import Net2i

# Configure for specific CNN requirements
results = Net2i.encode(
    'firewall_logs.csv',
    output_dir='cnn_training_data',
    image_size=224  # ResNet/VGG input size
)
```

### Global Configuration
```python
import Net2i

# Set global defaults
Net2i.set_config(
    output_dir='training_images',
    image_size=150,
    clean_existing=True
)

# Use configured settings
results = Net2i.encode('network_data.csv')
```

## 📊 Supported Network Data Types

| Data Type | Detection Method | Encoding Strategy | Output Pixels |
|-----------|-----------------|-------------------|---------------|
| **IPv4 Address** | Automatic pattern matching | Split into 4 octets → IEEE 754 encoding | 8 RGB pixels |
| **IPv6 Address** | Automatic pattern matching | 128-bit → 16 bytes + 2 padding | 6 RGB pixels |
| **MAC Address** | Regex: `XX:XX:XX:XX:XX:XX` | Split into 2 hex chunks → float encoding | 4 RGB pixels |
| **Float/Integer** | Numeric detection | Direct IEEE 754 encoding | 2 RGB pixels |
| **String** | Default fallback | Consistent hash → float encoding | 2 RGB pixels |

### Encoding Details
- **Two-Pixel-Per-Float Strategy**: Each float value uses exactly 2 RGB pixels (6 bytes) for lossless IEEE 754 representation
- **IP Address Decomposition**: IPv4 addresses split into octets, IPv6 addresses use full 128-bit representation
- **Hash-Based String Encoding**: Strings converted using consistent hashing for reproducible results

## 🔧 API Reference

### Core Functions

#### `encode(csv_path, **kwargs)`
Main function to convert CSV network data to images.

**Parameters:**
- `csv_path` (str): Path to input CSV file containing network traffic data
- `output_dir` (str, optional): Directory for output images (default: 'data')
- `image_size` (int, optional): Size of square output images (default: 150)

**Returns:**
```python
{
    'input_file': 'network_traffic.csv',
    'output_dir': 'data',
    'image_size': 150,
    'has_ipv4': True,
    'has_ipv6': False,
    'total_images': 1000,
    'ipv4_results': {...},
    'ipv6_results': None
}
```

#### `load_csv(csv_path)`
Load and validate network traffic CSV file.

#### `set_config(**kwargs)`
Configure global settings for all operations.

**Configuration Options:**
- `output_dir`: Output directory for generated images
- `image_size`: Image dimensions (width × height) - tune for your CNN architecture
- `types_file`: JSON file for IPv4 type information ('data_types.json')
- `types_file_ipv6`: JSON file for IPv6 type information ('data_types_ipv6.json')
- `clean_existing`: Clean existing files before processing (default: True)

### Utility Functions
- `show_config()`: Display current configuration
- `reset_config()`: Reset to default settings
- `help()`: Show detailed usage examples

## 📁 Output Structure

### Generated Files
```
output_dir/
├── ipv4_0.png              # IPv4 traffic images
├── ipv4_1.png
├── ipv4_2.png
├── ...
├── ipv6_0.png              # IPv6 traffic images (if present)
├── ipv6_1.png
├── ...
data_types.json             # IPv4 encoding metadata (for I2NeT)
data_types_ipv6.json        # IPv6 encoding metadata (for I2NeT)
ipv4_rows.csv              # Temporary IPv4 data split
ipv6_rows.csv              # Temporary IPv6 data split
```

### Type Information Files
The `data_types.json` and `data_types_ipv6.json` files contain crucial metadata for decoding with I2NeT:

```json
{
  "ip_version": "IPv4",
  "original_types": ["IPv4 Address", "Float", "String"],
  "final_types": ["IPv4 Address", "IPv4 Address", "IPv4 Address", "IPv4 Address", "Float", "String"],
  "encoding_info": {
    "description": "Data type mapping for decoding - IPv4 version",
    "float_encoding": "Each float becomes 2 RGB pixels (6 bytes total)",
    "ipv4_encoding": "IPv4 address split into 4 octets, each becomes 2 RGB pixels"
  },
  "original_columns": 3,
  "final_columns": 6
}
```



## 🧠 Machine Learning Integration

### TensorFlow/Keras Pipeline
```python
import Net2i
import tensorflow as tf
from tensorflow.keras.preprocessing.image import ImageDataGenerator

# Step 1: Convert network data to images
Net2i.set_config(image_size=224, output_dir='training_data')
results = Net2i.encode('network_traffic.csv')

# Step 2: Create data generators
datagen = ImageDataGenerator(
    rescale=1./255,
    validation_split=0.2,
    rotation_range=10,  # Slight augmentation for network data
    width_shift_range=0.1,
    height_shift_range=0.1
)

train_generator = datagen.flow_from_directory(
    'training_data',
    target_size=(224, 224),
    batch_size=32,
    class_mode='categorical',
    subset='training'
)

validation_generator = datagen.flow_from_directory(
    'training_data',
    target_size=(224, 224),
    batch_size=32,
    class_mode='categorical',
    subset='validation'
)
```

### PyTorch Integration
```python
import Net2i
import torch
from torchvision import transforms, datasets
from torch.utils.data import DataLoader

# Convert network data
Net2i.encode('network_logs.csv', image_size=224)

# Define transforms for network traffic images
transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

# Create dataset and dataloader
dataset = datasets.ImageFolder('data', transform=transform)
dataloader = DataLoader(dataset, batch_size=32, shuffle=True, num_workers=4)
```

## 📋 Input Data Format

### CSV Structure
- **No headers required**: Data processed by column position
- **Mixed data types supported**: Automatic type detection
- **Standard network formats**: IP addresses, MAC addresses, ports, timestamps

### Example Network Traffic CSV
```csv
12,2001:0db8:85a3:0000:0000:8a2e:0370:7334,52:54:00:34:65:b2,f70c:b55a:6503:e872:154e:a4b7:feee:1d56,199,61375,17,90,40,1,1,1,700,800,900,2400,1,5200,1
11,192.168.248.159,52:54:00:34:65:b2,192.168.248.10,443,61374,17,90,40,1.2,1.785,10.54,700.55,800,900,2400,1,5200,1
12,192.168.248.159,52:54:00:34:65:b2,192.168.248.10,199,61375,17,90,40,1,1,1,700,800,900,2400,1,5200,1
```

### Supported Network Data Sources
- **Firewall logs**
- **IDS/IPS alerts** 
- **Network flow records**
- **Packet capture summaries**
- **5G-MEC traffic data**
- **IoT device communications**

## 🔄 Integration with I2NeT

Net2i creates images that can be decoded back to CSV format using [I2NeT](https://github.com/omeshF/I2NeT):

```python
import Net2i
# Step 1: Encode network data to images
results = Net2i.encode('original_traffic.csv')

# Step 2: After CNN processing, decode back with I2NeT
import I2NeT.decoder as decoder
decoded_results = decoder.load_data('data', 'reconstructed_traffic.csv')
```

This enables:
- **🔍 Verification**: Check data integrity before CNN training
- **🐛 Debugging**: Map CNN predictions back to original features  
- **🎯 Analysis**: Reconstruct specific samples for detailed examination

## 🛠️ Technical Implementation

### Image Generation Process
1. **Data Loading**: Parse CSV and detect column data types
2. **IP Version Separation**: Automatically split IPv4 and IPv6 data
3. **Type-Specific Processing**: 
   - MAC addresses → hex chunks
   - IP addresses → octets (IPv4) or 128-bit representation (IPv6)
   - Strings → consistent hash values
4. **IEEE 754 Encoding**: Convert all values to float representation
5. **RGB Pixel Mapping**: Map each float to 2 RGB pixels (6 bytes)
6. **Image Assembly**: Create square images with consistent pixel organization

### Performance Characteristics
- **Memory Efficient**: Processes data in streaming fashion
- **Scalable**: Handles datasets with thousands of network records
- **Fast Processing**: Optimized for typical network log sizes
- **Lossless**: Perfect reconstruction possible with I2NeT

## 🎯 Image Size Recommendations

| CNN Architecture | Recommended Size | Use Case |
|------------------|------------------|----------|
| **150×150** | Default | Lightweight models, fast training |
| **224×224** | ResNet, VGG | Standard deep learning architectures |
| **299×299** | Inception | Advanced feature extraction |
| **Custom** | Your model | Match your specific CNN input requirements |

## 🚨 Troubleshooting

### Common Issues

**"No IP addresses detected"**
```python
# Verify your CSV contains valid IP addresses
import pandas as pd
df = pd.read_csv('your_file.csv', header=None)
print(df.head())  # Check first few rows
```

**Images appear corrupted**
```python
# Check if CSV data is clean
Net2i.set_config(clean_existing=True)  # Clean old files
results = Net2i.encode('your_file.csv')
```

**Memory issues with large network logs**
```python
# Reduce image size for large datasets
Net2i.set_config(image_size=128)
# Process in smaller batches if needed
```

### Best Practices

1. **Data Validation**: Ensure CSV contains actual network traffic data
2. **Clean Data**: Remove headers and ensure consistent column structure
3. **Size Selection**: Match image size to your CNN architecture
4. **Storage Planning**: Large network datasets create many image files
5. **Type Files**: Keep `data_types.json` files for I2NeT decoding

## 🖥️ Command Line Usage

```bash
# Basic network data conversion
python Net2i.py network_traffic.csv

# Custom output directory and image size
python Net2i.py firewall_logs.csv cnn_images 224

# Show help and examples
python Net2i.py
```

## 📚 Citation

If you use Net2i in your research on network security or machine learning, please cite:

```bibtex
@inproceedings{fernando2023new,
  title={New algorithms for the detection of malicious traffic in 5g-mec},
  author={Fernando, Omesh A and Xiao, Hannan and Spring, Joseph},
  booktitle={2023 IEEE Wireless Communications and Networking Conference (WCNC)},
  pages={1--6},
  year={2023},
  organization={IEEE}
}
```

## 👥 Author

- **Omesh Fernando** 

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🔗 Related Projects

- **[I2NeT](https://github.com/omeshF/I2NeT)**: Decode Net2i images back to CSV format
- **IEEE WCNC 2023 Paper**: "New algorithms for the detection of malicious traffic in 5G-MEC"

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/network-enhancement`)
3. Add tests for network data processing
4. Commit changes (`git commit -am 'Add new network feature'`)
5. Push to branch (`git push origin feature/network-enhancement`)
6. Create Pull Request

## 💬 Support

- **🐛 Issues**: Report bugs on GitHub Issues
- **📖 Documentation**: Use `Net2i.help()` for detailed examples
- **🔄 Decoding**: Use [I2NeT](https://github.com/omeshF/I2NeT) for image-to-CSV conversion

---

**🔄 Remember**: Images generated by Net2i are specifically designed for decoding with I2NeT. This ensures perfect reconstruction of your original network traffic data for analysis and verification.